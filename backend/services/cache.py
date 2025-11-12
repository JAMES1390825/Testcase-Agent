"""Simple in-memory result cache for generation outputs."""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Dict, Optional


_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


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
    with _LOCK:
        return _CACHE.get(key)


def set(key: str, value: Dict[str, Any]) -> None:
    with _LOCK:
        _CACHE[key] = value


__all__ = ["make_key", "get", "set"]
