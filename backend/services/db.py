"""PostgreSQL database integration using SQLAlchemy.

If DATABASE_URL is provided, the KB storage will use Postgres instead of
filesystem JSON. Falls back gracefully when not configured.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Integer, String, Text, ForeignKey, create_engine, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session


_ENGINE = None
_Session: Optional[sessionmaker] = None


class Base(DeclarativeBase):
    pass


class KbDoc(Base):
    __tablename__ = "kb_docs"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    sections: Mapped[List["KbSection"]] = relationship("KbSection", back_populates="doc", cascade="all, delete-orphan")


class KbSection(Base):
    __tablename__ = "kb_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("kb_docs.doc_id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    # Store embedding vector as JSON array (pgvector requires extension; fallback to JSON for simplicity)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    doc: Mapped[KbDoc] = relationship("KbDoc", back_populates="sections")


# Upload buckets
class UploadedTestCases(Base):
    __tablename__ = "uploaded_testcases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=True)  # e.g., csv, txt, md
    # Store embedding for test case content
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)


class UploadedPrd(Base):
    __tablename__ = "uploaded_prds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=True)  # e.g., md, csv, txt
    # Store embedding for PRD content
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)


def init_db(echo: bool = False) -> None:
    """Initialize SQLAlchemy engine and create tables if DATABASE_URL is set."""
    global _ENGINE, _Session
    url = os.environ.get("DATABASE_URL")
    if not url:
        return
    # Example URL: postgresql+psycopg://user:pass@host:5432/dbname
    _ENGINE = create_engine(url, echo=echo, pool_pre_ping=True)
    _Session = sessionmaker(bind=_ENGINE, expire_on_commit=False)
    Base.metadata.create_all(_ENGINE)


def is_enabled() -> bool:
    return _ENGINE is not None and _Session is not None


def create_doc_from_sections(name: str, created_at: int, sections: List[Dict[str, Any]], doc_id: str) -> str:
    """Persist a KB doc and its sections into Postgres."""
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        doc = KbDoc(doc_id=doc_id, name=name, created_at=created_at)
        s.add(doc)
        for i, sec in enumerate(sections):
            s.add(
                KbSection(
                    doc_id=doc_id,
                    idx=i,
                    title=sec.get("title") or "",
                    text=sec.get("text") or "",
                    images=list(sec.get("images") or []),
                    embedding=sec.get("embedding"),  # Store embedding vector
                )
            )
        s.commit()
    return doc_id


def list_docs() -> List[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        # Count sections and images per doc
        # images is JSON array; use SQLAlchemy func.json_array_length if available; fallback in Python aggregation
        docs = s.execute(select(KbDoc)).scalars().all()
        res: List[Dict[str, Any]] = []
        for d in docs:
            # aggregate in Python for simplicity
            secs = s.execute(select(KbSection).where(KbSection.doc_id == d.doc_id).order_by(KbSection.idx.asc())).scalars().all()
            total_images = sum(len(sec.images or []) for sec in secs)
            res.append({
                "doc_id": d.doc_id,
                "name": d.name,
                "created_at": d.created_at,
                "sections": len(secs),
                "total_images": total_images,
            })
        # Sort by created_at desc
        res.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return res


def load_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        doc = s.get(KbDoc, doc_id)
        if not doc:
            return None
        secs = s.execute(select(KbSection).where(KbSection.doc_id == doc_id).order_by(KbSection.idx.asc())).scalars().all()
        sections = [
            {
                "title": sec.title,
                "text": sec.text,
                "images": list(sec.images or []),
                "embedding": sec.embedding,  # Include embedding in loaded doc
            }
            for sec in secs
        ]
        return {
            "doc_id": doc.doc_id,
            "name": doc.name,
            "created_at": doc.created_at,
            "sections": sections,
        }


# ---------- Uploads: Test cases ----------
def save_uploaded_testcases(name: str, created_at: int, content: str, content_type: Optional[str], embedding: Optional[List[float]] = None, *, id: Optional[str] = None) -> str:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    import uuid
    uid = id or uuid.uuid4().hex
    with _Session() as s:
        s.add(UploadedTestCases(
            id=uid,
            name=name,
            created_at=created_at,
            content=content,
            content_type=content_type or None,
            embedding=embedding,
        ))
        s.commit()
    return uid


def list_uploaded_testcases() -> List[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        items = s.execute(select(UploadedTestCases)).scalars().all()
        res = [
            {"id": it.id, "name": it.name, "created_at": it.created_at, "content_type": it.content_type}
            for it in items
        ]
        res.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return res


def get_uploaded_testcases(item_id: str) -> Optional[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        it = s.get(UploadedTestCases, item_id)
        if not it:
            return None
        return {"id": it.id, "name": it.name, "created_at": it.created_at, "content_type": it.content_type, "content": it.content}


# ---------- Uploads: PRDs ----------
def save_uploaded_prd(name: str, created_at: int, content: str, file_type: Optional[str], embedding: Optional[List[float]] = None, *, id: Optional[str] = None) -> str:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    import uuid
    uid = id or uuid.uuid4().hex
    with _Session() as s:
        s.add(UploadedPrd(
            id=uid,
            name=name,
            created_at=created_at,
            content=content,
            file_type=file_type or None,
            embedding=embedding,
        ))
        s.commit()
    return uid


def list_uploaded_prds() -> List[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        items = s.execute(select(UploadedPrd)).scalars().all()
        res = [
            {"id": it.id, "name": it.name, "created_at": it.created_at, "file_type": it.file_type}
            for it in items
        ]
        res.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return res


def get_uploaded_prd(item_id: str) -> Optional[Dict[str, Any]]:
    if not is_enabled():
        raise RuntimeError("DATABASE_URL not configured")
    assert _Session is not None
    with _Session() as s:
        it = s.get(UploadedPrd, item_id)
        if not it:
            return None
        return {"id": it.id, "name": it.name, "created_at": it.created_at, "file_type": it.file_type, "content": it.content}

