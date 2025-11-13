"""Knowledge base storage helpers.

Defaults to filesystem JSON under data/kb/<doc_id>/doc.json.
When DATABASE_URL is configured, uses PostgreSQL via SQLAlchemy instead.
Supports embedding vectorization when EMBEDDING_API_KEY is set.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import BASE_DIR
from . import db as db_mod
from . import embeddings as emb_mod


DATA_DIR = BASE_DIR / "data" / "kb"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _doc_dir(doc_id: str) -> Path:
    d = DATA_DIR / doc_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_doc(doc: Dict[str, Any]) -> None:
    # Only used in filesystem mode
    doc_id = doc["doc_id"]
    dd = _doc_dir(doc_id)
    with (dd / "doc.json").open("w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def load_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    # Prefer DB when available
    if db_mod.is_enabled():
        return db_mod.load_doc(doc_id)
    p = _doc_dir(doc_id) / "doc.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_docs() -> List[Dict[str, Any]]:
    if db_mod.is_enabled():
        return db_mod.list_docs()
    res: List[Dict[str, Any]] = []
    for child in DATA_DIR.iterdir():
        if not child.is_dir():
            continue
        doc_path = child / "doc.json"
        if doc_path.exists():
            try:
                with doc_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                res.append({
                    "doc_id": meta.get("doc_id"),
                    "name": meta.get("name"),
                    "created_at": meta.get("created_at"),
                    "sections": len(meta.get("sections", [])),
                    "total_images": sum(len(s.get("images", [])) for s in meta.get("sections", [])),
                })
            except Exception:
                continue
    return sorted(res, key=lambda x: x.get("created_at", 0), reverse=True)


def create_doc_from_sections(name: str, sections: List[Dict[str, Any]]) -> str:
    doc_id = uuid.uuid4().hex
    created_at = int(time.time())
    
    # Generate embeddings for each section if embedding is enabled
    if emb_mod.is_enabled():
        for sec in sections:
            combined = f"{sec.get('title', '')} {sec.get('text', '')}"
            try:
                sec["embedding"] = emb_mod.embed_text(combined)
            except Exception as exc:
                print(f"Failed to embed section: {exc}")
                sec["embedding"] = None
    
    if db_mod.is_enabled():
        db_mod.create_doc_from_sections(name or f"doc-{doc_id[:6]}", created_at, sections, doc_id)
        return doc_id
    payload = {
        "doc_id": doc_id,
        "name": name or f"doc-{doc_id[:6]}",
        "created_at": created_at,
        # sections: [{title, text, images: [data_url or url], embedding}]
        "sections": sections,
    }
    save_doc(payload)
    return doc_id


def search_similar_sections(query: str, top_k: int = 5, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for similar sections in knowledge base using semantic similarity.
    
    Args:
        query: Query text to search for
        top_k: Number of top results to return
        doc_id: Optional document ID to limit search scope
    
    Returns:
        List of sections with similarity scores, sorted by relevance
    """
    if not emb_mod.is_enabled():
        return []
    
    try:
        query_embedding = emb_mod.embed_text(query)
    except Exception as exc:
        print(f"Failed to embed query: {exc}")
        return []
    
    results: List[Tuple[float, Dict[str, Any]]] = []
    
    if db_mod.is_enabled():
        # Search in database
        if doc_id:
            doc = db_mod.load_doc(doc_id)
            if not doc:
                return []
            docs_to_search = [doc]
        else:
            # Search all docs
            all_docs = db_mod.list_docs()
            docs_to_search = [db_mod.load_doc(d["doc_id"]) for d in all_docs if db_mod.load_doc(d["doc_id"])]
        
        for doc in docs_to_search:
            if not doc:
                continue
            for sec in doc.get("sections", []):
                if sec.get("embedding"):
                    sim = emb_mod.cosine_similarity(query_embedding, sec["embedding"])
                    results.append((sim, {
                        "doc_id": doc["doc_id"],
                        "doc_name": doc.get("name"),
                        "title": sec.get("title"),
                        "text": sec.get("text"),
                        "images": sec.get("images", []),
                        "similarity": sim,
                    }))
    else:
        # Search in filesystem JSON
        if doc_id:
            doc = load_doc(doc_id)
            if not doc:
                return []
            docs_to_search = [doc]
        else:
            docs_to_search = []
            for child in DATA_DIR.iterdir():
                if child.is_dir():
                    d = load_doc(child.name)
                    if d:
                        docs_to_search.append(d)
        
        for doc in docs_to_search:
            for sec in doc.get("sections", []):
                if sec.get("embedding"):
                    sim = emb_mod.cosine_similarity(query_embedding, sec["embedding"])
                    results.append((sim, {
                        "doc_id": doc["doc_id"],
                        "doc_name": doc.get("name"),
                        "title": sec.get("title"),
                        "text": sec.get("text"),
                        "images": sec.get("images", []),
                        "similarity": sim,
                    }))
    
    # Sort by similarity descending and return top_k
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:top_k]]


__all__ = [
    "save_doc",
    "load_doc",
    "list_docs",
    "create_doc_from_sections",
    "search_similar_sections",
]
