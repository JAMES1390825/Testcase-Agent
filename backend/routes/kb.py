"""Knowledge base endpoints: ingest and generate from KB."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services import (
    kb_list_docs,
    kb_load_doc,
    kb_search_similar_sections,
    create_openai_client,
    build_vision_messages,
    call_model_with_retries,
    merge_csv_texts,
    validate_strict_csv,
    coerce_to_strict_csv,
)
from backend.services.jobs import start_kb_ingest_job
from backend.config import (
    DISABLE_VISION_DEFAULT,
    IMAGE_MAX_SIZE_DEFAULT,
    IMAGE_QUALITY_DEFAULT,
    MAX_IMAGES_PER_BATCH_DEFAULT,
    MAX_SECTION_CHARS_DEFAULT,
    BATCH_INFERENCE_CONCURRENCY_DEFAULT,
    IMAGE_DOWNLOAD_CONCURRENCY_DEFAULT,
)
from concurrent.futures import ThreadPoolExecutor, as_completed


bp = Blueprint("kb", __name__, url_prefix="/api/kb")


@bp.route("/docs", methods=["GET"])
def docs_list():
    return jsonify({"docs": kb_list_docs()})


@bp.route("/ingest_async", methods=["POST"])
def ingest_async():
    data = request.get_json() or {}
    # name + prd_content required (for MVP)
    if not (data.get("prd_content") and str(data.get("prd_content")).strip()):
        return jsonify({"error": "PRD 内容不能为空"}), 400
    job_id = start_kb_ingest_job({
        "name": data.get("name") or "未命名文档",
        "prd_content": data.get("prd_content"),
    })
    return jsonify({"job_id": job_id})


@bp.route("/generate_from_kb", methods=["POST"])
def generate_from_kb():
    data = request.get_json() or {}
    doc_id = data.get("doc_id")
    user_config: dict = data.get("config") or {}

    if not doc_id:
        return jsonify({"error": "缺少 doc_id"}), 400
    kb_doc = kb_load_doc(doc_id)
    if not kb_doc:
        return jsonify({"error": "知识库文档不存在或未入库完成"}), 404

    sections = kb_doc.get("sections") or []

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
        return jsonify({"error": "缺少必要配置：请填写 API Key 和 文本模型名称。"}), 400

    try:
        user_client = create_openai_client(user_api_key, user_base_url)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"配置 AI 客户端失败: {exc}"}), 400

    # If vision disabled or no images at all, run text-only
    total_images = sum(len(s.get("images", [])) for s in sections)
    from backend.services.parsing import create_batches_from_sections
    prompt_full, _ = (None, None)
    from flask import current_app
    prompt_full, _ = current_app.config["PROMPT_TEMPLATES"]

    if user_disable_vision or total_images == 0 or not user_vision_model:
        combined_text = "\n\n".join([f"## {s['title']}\n{s['text']}" for s in sections])
        final_prompt = prompt_full.format(prd_content=combined_text)
        completion = user_client.chat.completions.create(
            model=user_text_model,
            messages=[
                {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                {"role": "user", "content": final_prompt},
            ],
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
            "mode": "kb-text",
            "model_used": user_text_model,
            "use_vision": False,
            "doc_id": doc_id,
            "total_images": total_images,
            "total_sections": len(sections),
        }
        return jsonify({"test_cases": ai_response, "meta": meta})

    # Vision path using preprocessed data URLs
    from backend.services.parsing import create_batches_from_sections
    batches = create_batches_from_sections(sections, user_max_images_per_batch, user_max_section_chars)
    total_batches = len(batches)

    def run_one(i_b):
        i, b = i_b
        msgs = build_vision_messages(
            b,
            prompt_full,
            i,
            total_batches,
            use_deepseek=(bool(user_base_url) and "deepseek" in str(user_base_url).lower()),
            image_max_size=user_image_max_size,
            image_quality=user_image_quality,
            image_download_concurrency=int(user_image_dl_conc),
        )
        try:
            return i, call_model_with_retries(user_client, user_vision_model, msgs)
        except Exception:
            # Degrade to text-only for this batch
            combined_text = "\n\n".join([f"## {s['title']}\n{s['text']}" for s in b["sections"]])
            final_prompt = prompt_full.format(prd_content=combined_text)
            completion = user_client.chat.completions.create(
                model=user_text_model,
                messages=[
                    {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                    {"role": "user", "content": final_prompt},
                ],
                max_tokens=4096,
            )
            return i, completion.choices[0].message.content

    if total_batches > 1 and int(user_batch_infer_conc) > 1:
        with ThreadPoolExecutor(max_workers=int(user_batch_infer_conc)) as ex:
            futs = [ex.submit(run_one, (i, b)) for i, b in enumerate(batches)]
            results = {}
            for fut in as_completed(futs):
                i, r = fut.result()
                results[i] = r
        responses = [results.get(i, "") for i in range(total_batches)]
    else:
        responses = []
        for i, b in enumerate(batches):
            _, r = run_one((i, b))
            responses.append(r)

    final_response = merge_csv_texts(responses)
    ok, _ = validate_strict_csv(final_response)
    if not ok:
        repaired = coerce_to_strict_csv(final_response)
        ok2, _ = validate_strict_csv(repaired)
        if ok2:
            final_response = repaired

    meta = {
        "mode": "kb-vision",
        "model_used": user_vision_model,
        "use_vision": True,
        "doc_id": doc_id,
        "total_batches": total_batches,
        "total_images": total_images,
        "total_sections": len(sections),
    }
    return jsonify({"test_cases": final_response, "meta": meta})


@bp.route("/search", methods=["POST"])
def search_kb():
    """Search for similar sections in knowledge base using semantic similarity."""
    data = request.get_json() or {}
    query = data.get("query")
    top_k = data.get("top_k", 5)
    doc_id = data.get("doc_id")  # Optional: limit search to specific doc
    
    if not query or not str(query).strip():
        return jsonify({"error": "查询内容不能为空"}), 400
    
    try:
        results = kb_search_similar_sections(query, top_k=top_k, doc_id=doc_id)
        return jsonify({"results": results})
    except Exception as exc:
        return jsonify({"error": f"搜索失败: {exc}"}), 500

