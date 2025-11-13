"""File upload and retrieval endpoints for test cases and PRDs.

Supports multipart/form-data (preferred) and JSON payloads as fallback.
"""

from __future__ import annotations

import time
from typing import Optional

from flask import Blueprint, jsonify, request

from backend.services import (
    uploads_save_testcases,
    uploads_list_testcases,
    uploads_get_testcases,
    uploads_save_prd,
    uploads_list_prds,
    uploads_get_prd,
)

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


# Helpers to read file or content

def _read_text_from_request() -> tuple[Optional[str], Optional[str]]:
    # Returns (filename, text)
    if "file" in request.files:
        f = request.files["file"]
        if f and f.filename:
            text = f.read().decode("utf-8", errors="ignore")
            return f.filename, text
    data = request.get_json(silent=True) or {}
    if "content" in data:
        return data.get("name") or "unnamed.txt", str(data.get("content"))
    return None, None


@bp.route("/testcases", methods=["POST"])  # upload
def upload_testcases():
    fname, text = _read_text_from_request()
    if not text:
        return jsonify({"error": "未收到任何文件或文本内容"}), 400
    content_type = None
    if fname and "." in fname:
        content_type = fname.rsplit(".", 1)[-1].lower()
    item_id = uploads_save_testcases(name=fname or "testcases.csv", content=text, content_type=content_type)
    return jsonify({"id": item_id, "name": fname, "created_at": int(time.time())})


@bp.route("/testcases", methods=["GET"])  # list
def list_testcases():
    return jsonify({"items": uploads_list_testcases()})


@bp.route("/testcases/<item_id>", methods=["GET"])  # get
def get_testcases(item_id: str):
    it = uploads_get_testcases(item_id)
    if not it:
        return jsonify({"error": "未找到该测试用例文件"}), 404
    return jsonify(it)


@bp.route("/prds", methods=["POST"])  # upload PRD
def upload_prd():
    fname, text = _read_text_from_request()
    if not text:
        return jsonify({"error": "未收到任何文件或文本内容"}), 400
    file_type = None
    if fname and "." in fname:
        file_type = fname.rsplit(".", 1)[-1].lower()
    item_id = uploads_save_prd(name=fname or "prd.md", content=text, file_type=file_type)
    return jsonify({"id": item_id, "name": fname, "created_at": int(time.time())})


@bp.route("/prds", methods=["GET"])  # list
def list_prds():
    return jsonify({"items": uploads_list_prds()})


@bp.route("/prds/<item_id>", methods=["GET"])  # get
def get_prd(item_id: str):
    it = uploads_get_prd(item_id)
    if not it:
        return jsonify({"error": "未找到该PRD文件"}), 404
    return jsonify(it)
