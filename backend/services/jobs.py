"""Async job runner with in-memory store and optional Redis mirroring for progress and ETA."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
import os
import json

from flask import current_app

from backend.services import (
    create_openai_client,
    build_vision_messages,
    download_and_process_image,
    call_model_with_retries,
    create_batches_from_sections,
    merge_csv_texts,
    validate_strict_csv,
    coerce_to_strict_csv,
    parse_prd_sections,
    make_key,
    cache_get,
    cache_set,
    kb_create_doc_from_sections,
    uploads_get_prd,
    uploads_get_testcases,
)
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


_JOBS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()
_ENHANCE_MAX_SECONDS = 240  # hard timeout guard for enhance jobs (UI shouldn't wait forever)

# Optional Redis for cross-process persistence
_redis = None
try:
    from redis import Redis

    _redis_url = os.environ.get("REDIS_URL")
    if _redis_url:
        _redis = Redis.from_url(_redis_url, decode_responses=True)
        try:
            _redis.ping()
        except Exception:
            _redis = None
except Exception:
    _redis = None


def _redis_set(job_id: str) -> None:
    if _redis is None:
        return
    try:
        with _LOCK:
            data = _JOBS.get(job_id)
        if data is not None:
            _redis.set(f"jobs:{job_id}", json.dumps(data, ensure_ascii=False), ex=60 * 60 * 24)
    except Exception:
        pass


def _update(job_id: str, **kwargs: Any) -> None:
    with _LOCK:
        _JOBS[job_id].update(kwargs)
    _redis_set(job_id)


def start_generate_job(payload: Dict[str, Any]) -> str:
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "type": "generate",
            "status": "pending",
            "progress": {"current": 0, "total": 0},
            "eta_seconds": None,
            "error": None,
            "result": None,
            "meta": None,
            "started_at": None,
        }
    _redis_set(job_id)
    t = threading.Thread(target=_run_job, args=(job_id, payload), daemon=True)
    t.start()
    return job_id


def get_job(job_id: str) -> Dict[str, Any] | None:
    # Prefer Redis if available
    if _redis is not None:
        try:
            raw = _redis.get(f"jobs:{job_id}")
            if raw:
                job = json.loads(raw)
                # Watchdog for enhance
                if job.get("type") == "enhance" and job.get("status") == "running":
                    st = job.get("started_at")
                    if st and (time.time() - float(st)) > _ENHANCE_MAX_SECONDS:
                        job["status"] = "error"
                        job["error"] = f"任务超时（>{_ENHANCE_MAX_SECONDS}s），已取消。请检查网络与模型配置后重试。"
                        # mirror back change
                        try:
                            _redis.set(f"jobs:{job_id}", json.dumps(job, ensure_ascii=False), ex=60 * 60 * 24)
                        except Exception:
                            pass
                return job
        except Exception:
            pass
    with _LOCK:
        job = _JOBS.get(job_id)
    # Watchdog: auto-timeout enhance jobs to avoid endless spinners in UI
    if job and job.get("type") == "enhance" and job.get("status") == "running":
        st = job.get("started_at")
        if st and (time.time() - float(st)) > _ENHANCE_MAX_SECONDS:
            job["status"] = "error"
            job["error"] = f"任务超时（>{_ENHANCE_MAX_SECONDS}s），已取消。请检查网络与模型配置后重试。"
            _redis_set(job_id)
    return job


def _run_job(job_id: str, data: Dict[str, Any]) -> None:
    _update(job_id, status="running", started_at=time.time())
    start_ts = time.time()
    try:
        new_prd_content = data.get("new_prd")
        old_prd_content = data.get("old_prd")
        # Resolve uploaded PRD ids if provided
        new_prd_id = data.get("new_prd_id")
        old_prd_id = data.get("old_prd_id")
        if new_prd_id and not new_prd_content:
            ref = uploads_get_prd(new_prd_id)
            if not ref:
                raise RuntimeError("指定的新PRD文件不存在")
            new_prd_content = ref.get("content")
        if old_prd_id and not old_prd_content:
            ref2 = uploads_get_prd(old_prd_id)
            if not ref2:
                raise RuntimeError("指定的旧PRD文件不存在")
            old_prd_content = ref2.get("content")
        user_config: dict = data.get("config") or {}

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

        # Cache lookup before heavy work
        cache_key = make_key({
            "old_prd": old_prd_content or "",
            "new_prd": new_prd_content or "",
            "config": user_config,
        })
        cached = cache_get(cache_key)
        if cached:
            _update(job_id, status="done", result=cached["result"], meta=cached.get("meta"), eta_seconds=0)
            return

        user_client = create_openai_client(user_api_key, user_base_url)
        prompt_template_full, prompt_template_diff = current_app.config["PROMPT_TEMPLATES"]

        # Incremental (text) mode always single batch
        if old_prd_content and old_prd_content.strip():
            final_prompt = prompt_template_diff.format(
                old_prd_content=old_prd_content,
                new_prd_content=new_prd_content,
            )
            messages = [
                {"role": "system", "content": "你是一名顶级的、经验丰富的软件测试保证（SQA）工程师。请始终使用简体中文输出。"},
                {"role": "user", "content": final_prompt},
            ]
            completion = user_client.chat.completions.create(
                model=user_text_model,
                messages=messages,
                max_tokens=4096,
            )
            ai_response = completion.choices[0].message.content
            _update(job_id, progress={"current": 1, "total": 1}, eta_seconds=0)
            meta = {"mode": "incremental", "model_used": user_text_model, "use_vision": False}
            cache_set(cache_key, {"result": ai_response, "meta": meta})
            _update(job_id, status="done", result=ai_response, meta=meta)
            return

        # Text-only fallback (no images or disabled vision)
        if user_disable_vision:
            final_prompt = prompt_template_full.format(prd_content=new_prd_content)
            messages = [
                {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                {"role": "user", "content": final_prompt},
            ]
            completion = user_client.chat.completions.create(
                model=user_text_model,
                messages=messages,
                max_tokens=4096,
            )
            ai_response = completion.choices[0].message.content
            _update(job_id, progress={"current": 1, "total": 1}, eta_seconds=0)
            meta = {"mode": "full-text-fallback", "model_used": user_text_model, "use_vision": False}
            cache_set(cache_key, {"result": ai_response, "meta": meta})
            _update(job_id, status="done", result=ai_response, meta=meta)
            return

        if not user_vision_model:
            raise RuntimeError("缺少视觉模型名称")

        sections = parse_prd_sections(new_prd_content)
        total_images = sum(len(s["images"]) for s in sections)
        if total_images == 0:
            final_prompt = prompt_template_full.format(prd_content=new_prd_content)
            messages = [
                {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                {"role": "user", "content": final_prompt},
            ]
            completion = user_client.chat.completions.create(
                model=user_text_model,
                messages=messages,
                max_tokens=4096,
            )
            ai_response = completion.choices[0].message.content
            _update(job_id, progress={"current": 1, "total": 1}, eta_seconds=0)
            meta = {"mode": "full-no-images", "model_used": user_text_model, "use_vision": False}
            cache_set(cache_key, {"result": ai_response, "meta": meta})
            _update(job_id, status="done", result=ai_response, meta=meta)
            return

        batches = create_batches_from_sections(sections, user_max_images_per_batch, user_max_section_chars)
        total_batches = len(batches)
        _update(job_id, progress={"current": 0, "total": total_batches})

        use_deepseek = bool(user_base_url) and "deepseek" in str(user_base_url).lower()

        def run_one(i_b):
            i, b = i_b
            t0 = time.time()
            msgs = build_vision_messages(
                b,
                prompt_template_full,
                i,
                total_batches,
                use_deepseek=use_deepseek,
                image_max_size=user_image_max_size,
                image_quality=user_image_quality,
                image_download_concurrency=int(user_image_dl_conc),
            )
            try:
                resp = call_model_with_retries(user_client, user_vision_model, msgs)
            except Exception:
                # degrade to text only
                combined_text = "\n\n".join([f"## {s['title']}\n{s['text']}" for s in b["sections"]])
                final_prompt2 = prompt_template_full.format(prd_content=combined_text)
                completion = user_client.chat.completions.create(
                    model=user_text_model,
                    messages=[
                        {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                        {"role": "user", "content": final_prompt2},
                    ],
                    max_tokens=4096,
                )
                resp = completion.choices[0].message.content
            dt = time.time() - t0
            # update progress and ETA
            with _LOCK:
                cur = _JOBS[job_id]["progress"]["current"] + 1
                _JOBS[job_id]["progress"]["current"] = cur
                done = cur
                remain = total_batches - done
                # naive ETA based on per-batch average so far
                elapsed = time.time() - start_ts
                avg = elapsed / max(1, done)
                _JOBS[job_id]["eta_seconds"] = int(avg * remain)
            return i, resp

        # run batches in parallel
        if total_batches > 1 and int(user_batch_infer_conc) > 1:
            with ThreadPoolExecutor(max_workers=int(user_batch_infer_conc)) as ex:
                futs = [ex.submit(run_one, (i, b)) for i, b in enumerate(batches)]
                results = {}
                for fut in as_completed(futs):
                    i, r = fut.result()
                    results[i] = r
            responses = [results.get(i, "") for i in range(total_batches)]
        else:
            responses: List[str] = []
            for i, b in enumerate(batches):
                _, r = run_one((i, b))
                responses.append(r)

        final_response = merge_csv_texts(responses)
        ok, reason = validate_strict_csv(final_response)
        if not ok:
            repaired = coerce_to_strict_csv(final_response)
            ok2, reason2 = validate_strict_csv(repaired)
            if not ok2:
                raise RuntimeError(f"AI 输出不是规范 CSV：{reason2}")
            final_response = repaired

        meta = {
            "mode": "full-vision-multimodal",
            "model_used": user_vision_model,
            "use_vision": True,
            "total_batches": total_batches,
            "total_images": total_images,
            "total_sections": len(sections),
        }

        cache_set(cache_key, {"result": final_response, "meta": meta})
        _update(job_id, status="done", result=final_response, meta=meta, eta_seconds=0)
    except Exception as exc:  # noqa: BLE001
        _update(job_id, status="error", error=str(exc))

def start_enhance_job(payload: Dict[str, Any]) -> str:
    """Start an async enhance job with simple progress and CSV repair."""
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "type": "enhance",
            "status": "pending",
            "progress": {"current": 0, "total": 1},
            "eta_seconds": None,
            "error": None,
            "result": None,
            "meta": None,
            "started_at": None,
        }
    _redis_set(job_id)

    def _runner():
        _update(job_id, status="running", started_at=time.time())
        try:
            test_cases = payload.get("test_cases", "") or ""
            # Resolve uploaded testcases id
            ref_id = (payload or {}).get("test_cases_id")
            if ref_id and not test_cases:
                ref = uploads_get_testcases(ref_id)
                if not ref:
                    raise RuntimeError("指定的测试用例文件不存在")
                test_cases = ref.get("content", "") or ""
            user_config: dict = payload.get("config") or {}

            cache_key = make_key({
                "enhance_of": test_cases,
                "config": user_config,
            })
            cached = cache_get(cache_key)
            if cached:
                _update(job_id, status="done", result=cached["result"], meta=cached.get("meta"), eta_seconds=0, progress={"current": 1, "total": 1})
                return

            user_api_key = user_config.get("api_key")
            user_base_url = user_config.get("base_url")
            user_text_model = user_config.get("text_model")

            if not test_cases.strip():
                raise RuntimeError("测试用例内容不能为空")
            if not user_api_key or not user_text_model:
                raise RuntimeError("缺少必要配置：请在模型配置中填写 API Key 和 文本模型名称。")

            client = create_openai_client(user_api_key, user_base_url)
            enhance_prompt = f"""你是一位专业的测试工程师。请分析以下测试用例，并进行完善和补充：

【现有测试用例（原文）】
{test_cases}

【完善目标】
1. 用户场景补充：添加更多正向流程、边界条件
2. 异常场景补充：错误处理、异常输入、网络异常等
3. 测试步骤完善：步骤清晰、可执行
4. 预期结果优化：明确具体、可验证
5. 覆盖度提升：识别遗漏并补充

【输出格式（严格）】
- 仅输出 CSV 文本，不要输出 Markdown、代码块或其它说明。
- 第一行必须是表头，列为：用例ID,模块,子模块,测试项,前置条件,操作步骤,预期结果,用例类型
- 新增的测试用例在“用例ID”列以“[新增] ”前缀标注，例如：[新增] TC-登录-密码错误-0007
- 使用英文逗号分隔；如单元格内含逗号或换行，请用双引号包裹，并将内部双引号转义为两个双引号。

请直接输出完善后的完整 CSV 内容。"""

            result_text = call_model_with_retries(
                client,
                user_text_model,
                [
                    {"role": "system", "content": "你是一位经验丰富的测试工程师，擅长设计全面的测试用例。"},
                    {"role": "user", "content": enhance_prompt},
                ],
                max_tokens=4096,
                timeout=180,
                extra_kwargs={"temperature": 0.7},
            )
            _update(job_id, progress={"current": 1, "total": 1}, eta_seconds=0)

            ok, _ = validate_strict_csv(result_text)
            if not ok:
                repaired = coerce_to_strict_csv(result_text)
                ok2, _ = validate_strict_csv(repaired)
                if ok2:
                    result_text = repaired

            meta = {"mode": "enhance", "model_used": user_text_model, "use_vision": False}
            cache_set(cache_key, {"result": result_text, "meta": meta})
            _update(job_id, status="done", result=result_text, meta=meta, eta_seconds=0)
        except Exception as exc:  # noqa: BLE001
            _update(job_id, status="error", error=str(exc))

    threading.Thread(target=_runner, daemon=True).start()
    return job_id


def start_kb_ingest_job(payload: Dict[str, Any]) -> str:
    """Ingest a PRD into the local KB with preprocessed images (data URLs)."""
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "type": "kb_ingest",
            "status": "pending",
            "progress": {"current": 0, "total": 0},
            "eta_seconds": None,
            "error": None,
            "result": None,
            "meta": None,
            "started_at": None,
        }
    _redis_set(job_id)

    def _runner():
        _update(job_id, status="running", started_at=time.time())
        try:
            name = payload.get("name") or "未命名文档"
            prd_content = payload.get("prd_content") or ""
            if not prd_content.strip():
                raise RuntimeError("PRD 内容不能为空")

            sections = parse_prd_sections(prd_content)
            total_sections = len(sections)
            _update(job_id, progress={"current": 0, "total": total_sections})

            # Preprocess images into data URLs to avoid re-downloading later
            for i, s in enumerate(sections):
                imgs = s.get("images", []) or []
                processed: List[str] = []
                for url in imgs:
                    if isinstance(url, str) and url.startswith("data:image"):
                        processed.append(url)
                    else:
                        data_url = download_and_process_image(url)
                        if data_url:
                            processed.append(data_url)
                s["images"] = processed
                _update(job_id, progress={"current": i + 1, "total": total_sections})

            doc_id = kb_create_doc_from_sections(name, sections)
            stats = {
                "sections": total_sections,
                "total_images": sum(len(s.get("images", [])) for s in sections),
            }
            _update(job_id, status="done", result=doc_id, meta=stats, eta_seconds=0)
        except Exception as exc:  # noqa: BLE001
            _update(job_id, status="error", error=str(exc))

    threading.Thread(target=_runner, daemon=True).start()
    return job_id


__all__ = ["start_generate_job", "get_job", "start_enhance_job", "start_kb_ingest_job"]
