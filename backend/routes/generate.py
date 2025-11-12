"""/api/generate endpoint blueprint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.config import (
	DISABLE_VISION_DEFAULT,
	IMAGE_MAX_SIZE_DEFAULT,
	IMAGE_QUALITY_DEFAULT,
	MAX_IMAGES_PER_BATCH_DEFAULT,
	MAX_SECTION_CHARS_DEFAULT,
	BATCH_INFERENCE_CONCURRENCY_DEFAULT,
	IMAGE_DOWNLOAD_CONCURRENCY_DEFAULT,
)
from backend.services import (
	build_vision_messages,
	call_model_with_retries,
	create_batches_from_sections,
	create_openai_client,
	make_key,
	cache_get,
	cache_set,
	merge_csv_texts,
	validate_strict_csv,
	coerce_to_strict_csv,
	parse_prd_sections,
)
from concurrent.futures import ThreadPoolExecutor, as_completed


bp = Blueprint("generate", __name__, url_prefix="/api")


@bp.route("/generate", methods=["POST"])
def generate_test_cases():
	data = request.get_json() or {}

	new_prd_content: str | None = data.get("new_prd")
	old_prd_content: str | None = data.get("old_prd")
	user_config: dict = data.get("config") or {}

	if not new_prd_content:
		return jsonify({"error": "新版PRD内容不能为空"}), 400

	user_api_key = user_config.get("api_key")
	user_base_url = user_config.get("base_url")
	user_text_model = user_config.get("text_model")
	user_vision_model = user_config.get("vision_model")
	user_disable_vision = user_config.get("disable_vision", DISABLE_VISION_DEFAULT)
	user_max_images_per_batch = user_config.get("max_images_per_batch") or MAX_IMAGES_PER_BATCH_DEFAULT
	user_image_max_size = user_config.get("image_max_size") or IMAGE_MAX_SIZE_DEFAULT
	user_image_quality = user_config.get("image_quality") or IMAGE_QUALITY_DEFAULT
	user_max_section_chars = user_config.get("max_section_chars") or MAX_SECTION_CHARS_DEFAULT
	user_batch_infer_conc = user_config.get("batch_inference_concurrency") or BATCH_INFERENCE_CONCURRENCY_DEFAULT
	user_image_dl_conc = user_config.get("image_download_concurrency") or IMAGE_DOWNLOAD_CONCURRENCY_DEFAULT

	if not user_api_key or not user_text_model:
		return jsonify({"error": "缺少必要配置：请在模型配置中填写 API Key 和 文本模型名称。"}), 400

	try:
		user_client = create_openai_client(user_api_key, user_base_url)
	except Exception as exc:  # noqa: BLE001
		return jsonify({"error": f"配置 AI 客户端失败: {exc}"}), 400

	prompt_template_full, prompt_template_diff = current_app.config["PROMPT_TEMPLATES"]

	# Cache check (sync endpoint also benefits)
	cache_key = make_key({
		"old_prd": old_prd_content or "",
		"new_prd": new_prd_content or "",
		"config": user_config,
	})
	cached = cache_get(cache_key)
	if cached:
		return jsonify({"test_cases": cached["result"], "meta": cached.get("meta", {})})

	if old_prd_content and old_prd_content.strip():
		final_prompt = prompt_template_diff.format(
			old_prd_content=old_prd_content,
			new_prd_content=new_prd_content,
		)
		messages = [
			{
				"role": "system",
				"content": "你是一名顶级的、经验丰富的软件测试保证（SQA）工程师。请始终使用简体中文输出。",
			},
			{"role": "user", "content": final_prompt},
		]

		completion = user_client.chat.completions.create(
			model=user_text_model,
			messages=messages,
			max_tokens=4096,
		)
		ai_response = completion.choices[0].message.content

		meta = {
			"mode": "incremental",
			"model_used": user_text_model,
			"use_vision": False,
		}

		cache_set(cache_key, {"result": ai_response, "meta": meta})
		return jsonify({"test_cases": ai_response, "meta": meta})

	if user_disable_vision:
		final_prompt = prompt_template_full.format(prd_content=new_prd_content)
		messages = [
			{
				"role": "system",
				"content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。",
			},
			{"role": "user", "content": final_prompt},
		]
		completion = user_client.chat.completions.create(
			model=user_text_model,
			messages=messages,
			max_tokens=4096,
		)
		ai_response = completion.choices[0].message.content
		# 宽松模式：不再拦截；若能修复则返回修复后的内容
		ok, _ = validate_strict_csv(ai_response)
		if not ok:
			repaired = coerce_to_strict_csv(ai_response)
			ok2, _ = validate_strict_csv(repaired)
			if ok2:
				ai_response = repaired

		meta = {
			"mode": "full-text-fallback",
			"model_used": user_text_model,
			"use_vision": False,
		}

		cache_set(cache_key, {"result": ai_response, "meta": meta})
		return jsonify({"test_cases": ai_response, "meta": meta})

	if not user_vision_model:
		return jsonify({"error": "缺少视觉模型名称：请在模型配置中填写视觉模型或勾选禁用图片识别。"}), 400

	sections = parse_prd_sections(new_prd_content)
	total_images = sum(len(section["images"]) for section in sections)

	if total_images == 0:
		final_prompt = prompt_template_full.format(prd_content=new_prd_content)
		messages = [
			{
				"role": "system",
				"content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。",
			},
			{"role": "user", "content": final_prompt},
		]
		completion = user_client.chat.completions.create(
			model=user_text_model,
			messages=messages,
			max_tokens=4096,
		)
		ai_response = completion.choices[0].message.content
		ok, _ = validate_strict_csv(ai_response)
		if not ok:
			repaired = coerce_to_strict_csv(ai_response)
			ok2, _ = validate_strict_csv(repaired)
			if ok2:
				ai_response = repaired

		meta = {
			"mode": "full-no-images",
			"model_used": user_text_model,
			"use_vision": False,
		}

		cache_set(cache_key, {"result": ai_response, "meta": meta})
		return jsonify({"test_cases": ai_response, "meta": meta})

	batches = create_batches_from_sections(
		sections,
		user_max_images_per_batch,
		user_max_section_chars,
	)

	use_deepseek = bool(user_base_url) and "deepseek" in str(user_base_url).lower()

	# Function to process a single batch end-to-end
	def run_one(idx_batch_tuple):
		idx, batch = idx_batch_tuple
		print(
			f"处理第 {idx + 1}/{len(batches)} 批（{batch['total_images']} 张图片，{batch['total_chars']} 字符）..."
		)
		msgs = build_vision_messages(
			batch,
			prompt_template_full,
			idx,
			len(batches),
			use_deepseek=use_deepseek,
			image_max_size=user_image_max_size,
			image_quality=user_image_quality,
			image_download_concurrency=int(user_image_dl_conc),
		)
		try:
			return idx, call_model_with_retries(user_client, user_vision_model, msgs)
		except Exception as exc:  # noqa: BLE001
			print(f"第 {idx + 1} 批失败: {exc}")
			# Degrade: fallback to text-only generation for this batch
			combined_text = "\n\n".join(
				[f"## {s['title']}\n{s['text']}" for s in batch["sections"]]
			)
			final_prompt = prompt_template_full.format(prd_content=combined_text)
			try:
				completion = user_client.chat.completions.create(
					model=user_text_model,
					messages=[
						{
							"role": "system",
							"content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。",
						},
						{"role": "user", "content": final_prompt},
					],
					max_tokens=4096,
				)
				return idx, completion.choices[0].message.content
			except Exception as exc2:  # noqa: BLE001
				print(f"第 {idx + 1} 批文本降级也失败: {exc2}")
				return idx, ""

	# Parallel over batches with bounded workers
	if len(batches) > 1 and int(user_batch_infer_conc) > 1:
		with ThreadPoolExecutor(max_workers=int(user_batch_infer_conc)) as ex:
			futures = [ex.submit(run_one, (i, b)) for i, b in enumerate(batches)]
			results = {}
			for fut in as_completed(futures):
				idx, resp = fut.result()
				results[idx] = resp
		responses = [results.get(i, "") for i in range(len(batches))]
	else:
		responses: list[str] = []
		for idx, batch in enumerate(batches):
			_, resp = run_one((idx, batch))
			responses.append(resp)

	final_response = merge_csv_texts(responses)
	ok, _ = validate_strict_csv(final_response)
	if not ok:
		repaired = coerce_to_strict_csv(final_response)
		ok2, _ = validate_strict_csv(repaired)
		if ok2:
			final_response = repaired

	meta = {
		"mode": "full-vision-multimodal",
		"model_used": user_vision_model,
		"use_vision": True,
		"total_batches": len(batches),
		"total_images": total_images,
		"total_sections": len(sections),
	}

	cache_set(cache_key, {"result": final_response, "meta": meta})
	return jsonify({"test_cases": final_response, "meta": meta})
