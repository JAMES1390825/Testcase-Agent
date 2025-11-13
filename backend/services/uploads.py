"""Uploads storage facade for test cases and PRDs.

Prefers PostgreSQL via db.py when DATABASE_URL is configured; otherwise
falls back to filesystem JSON under data/uploads/{testcases,prds}/<id>.json.
Supports embedding vectorization when EMBEDDING_API_KEY is set.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import BASE_DIR
from . import db as db_mod
from . import embeddings as emb_mod

ROOT = BASE_DIR / "data" / "uploads"
TESTCASES_DIR = ROOT / "testcases"
PRDS_DIR = ROOT / "prds"
TESTCASES_DIR.mkdir(parents=True, exist_ok=True)
PRDS_DIR.mkdir(parents=True, exist_ok=True)


# ---- Test cases ----

def save_testcases(name: str, content: str, content_type: Optional[str] = None) -> str:
    # Generate embedding if enabled
    embedding = None
    if emb_mod.is_enabled():
        try:
            embedding = emb_mod.embed_text(content[:8000])  # Truncate for embedding API limits
        except Exception as exc:
            print(f"Failed to embed testcases: {exc}")
    
    if db_mod.is_enabled():
        return db_mod.save_uploaded_testcases(
            name=name,
            created_at=int(time.time()),
            content=content,
            content_type=content_type,
            embedding=embedding,
        )
    item_id = uuid.uuid4().hex
    payload = {
        "id": item_id,
        "name": name,
        "created_at": int(time.time()),
        "content_type": content_type,
        "content": content,
        "embedding": embedding,
    }
    with (TESTCASES_DIR / f"{item_id}.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return item_id


def list_testcases() -> List[Dict[str, Any]]:
    if db_mod.is_enabled():
        return db_mod.list_uploaded_testcases()
    res: List[Dict[str, Any]] = []
    for p in TESTCASES_DIR.glob("*.json"):
        try:
            with p.open("r", encoding="utf-8") as f:
                d = json.load(f)
            res.append({"id": d.get("id"), "name": d.get("name"), "created_at": d.get("created_at"), "content_type": d.get("content_type")})
        except Exception:
            continue
    res.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return res


def get_testcases(item_id: str) -> Optional[Dict[str, Any]]:
    if db_mod.is_enabled():
        return db_mod.get_uploaded_testcases(item_id)
    p = TESTCASES_DIR / f"{item_id}.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---- PRDs ----

def save_prd(name: str, content: str, file_type: Optional[str] = None) -> str:
    # Generate embedding if enabled
    embedding = None
    if emb_mod.is_enabled():
        try:
            embedding = emb_mod.embed_text(content[:8000])  # Truncate for embedding API limits
        except Exception as exc:
            print(f"Failed to embed PRD: {exc}")
    
    if db_mod.is_enabled():
        return db_mod.save_uploaded_prd(
            name=name,
            created_at=int(time.time()),
            content=content,
            file_type=file_type,
            embedding=embedding,
        )
    item_id = uuid.uuid4().hex
    payload = {
        "id": item_id,
        "name": name,
        "created_at": int(time.time()),
        "file_type": file_type,
        "content": content,
        "embedding": embedding,
    }
    with (PRDS_DIR / f"{item_id}.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return item_id


def list_prds() -> List[Dict[str, Any]]:
    if db_mod.is_enabled():
        return db_mod.list_uploaded_prds()
    res: List[Dict[str, Any]] = []
    for p in PRDS_DIR.glob("*.json"):
        try:
            with p.open("r", encoding="utf-8") as f:
                d = json.load(f)
            res.append({"id": d.get("id"), "name": d.get("name"), "created_at": d.get("created_at"), "file_type": d.get("file_type")})
        except Exception:
            continue
    res.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return res


def get_prd(item_id: str) -> Optional[Dict[str, Any]]:
    if db_mod.is_enabled():
        return db_mod.get_uploaded_prd(item_id)
    p = PRDS_DIR / f"{item_id}.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


__all__ = [
    "save_testcases",
    "list_testcases",
    "get_testcases",
    "save_prd",
    "list_prds",
    "get_prd",
]
