"""Result cache for generation outputs.

Uses Redis when REDIS_URL is set; falls back to in-memory otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Dict, Optional


_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()

_redis = None
_redis_enabled_err = None
try:
    from redis import Redis

    _redis_url = os.environ.get("REDIS_URL")
    if _redis_url:
        _redis = Redis.from_url(_redis_url, decode_responses=True)
        # Simple ping to verify
        try:
            _redis.ping()
        except Exception as exc:  # noqa: BLE001
            _redis = None
            _redis_enabled_err = str(exc)
except Exception as exc:  # noqa: BLE001
    _redis = None
    _redis_enabled_err = str(exc)


def make_key(payload: Dict[str, Any]) -> str:
    # Only include fields that affect output
    key_src = repr({
        "old_prd": payload.get("old_prd", ""),
        "new_prd": payload.get("new_prd", ""),
        "config": {
            k: payload.get("config", {}).get(k)
            for k in sorted((payload.get("config", {}) or {}).keys())
        },
    })
    return hashlib.sha256(key_src.encode("utf-8")).hexdigest()


def get(key: str) -> Optional[Dict[str, Any]]:
    if _redis is not None:
        try:
            val = _redis.get(f"cache:{key}")
            return json.loads(val) if val else None
        except Exception:
            pass
    with _LOCK:
        return _CACHE.get(key)


def set(key: str, value: Dict[str, Any]) -> None:
    if _redis is not None:
        try:
            _redis.set(f"cache:{key}", json.dumps(value, ensure_ascii=False), ex=60 * 60 * 24)
            return
        except Exception:
            pass
    with _LOCK:
        _CACHE[key] = value


__all__ = ["make_key", "get", "set"]
