"""Health endpoint blueprint."""

from __future__ import annotations

from flask import Blueprint, jsonify


bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
	return jsonify({"status": "ok"})
