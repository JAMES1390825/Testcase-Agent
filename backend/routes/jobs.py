"""Async job endpoints for generation progress & ETA."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services import make_key, cache_get, cache_set
from backend.services.jobs import start_generate_job, start_enhance_job, get_job


bp = Blueprint("jobs", __name__, url_prefix="/api")


@bp.route("/generate_async", methods=["POST"])
def generate_async():
    data = request.get_json() or {}
    # Cache lookup
    cache_key = make_key({
        "old_prd": data.get("old_prd", ""),
        "new_prd": data.get("new_prd", ""),
        "config": data.get("config") or {},
    })
    cached = cache_get(cache_key)
    if cached:
        return jsonify({"job_id": None, "cached": True, "result": cached["result"], "meta": cached.get("meta")})

    job_id = start_generate_job(data)
    return jsonify({"job_id": job_id, "cached": False})


@bp.route("/enhance_async", methods=["POST"])
def enhance_async():
    data = request.get_json() or {}
    cache_key = make_key({
        "enhance_of": data.get("test_cases", ""),
        "config": data.get("config") or {},
    })
    cached = cache_get(cache_key)
    if cached:
        return jsonify({"job_id": None, "cached": True, "result": cached["result"], "meta": cached.get("meta")})
    job_id = start_enhance_job(data)
    return jsonify({"job_id": job_id, "cached": False})


@bp.route("/job_status/<job_id>", methods=["GET"])
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)
