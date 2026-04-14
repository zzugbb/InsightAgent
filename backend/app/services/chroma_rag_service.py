"""RAG knowledge-base collections on Chroma: ingest, query, and status."""

from __future__ import annotations

import hashlib
import re
from uuid import uuid4

import chromadb

from app.config import get_settings


def _http_client() -> chromadb.HttpClient:
    settings = get_settings()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )
    client.heartbeat()
    return client


def normalize_knowledge_base_id(value: str | None) -> str:
    raw = (value or "default").strip().lower()
    if not raw:
        return "default"
    normalized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    if not normalized:
        return "default"
    return normalized[:48]


def _normalize_user_scope(user_id: str) -> str:
    raw = user_id.strip().lower()
    if not raw:
        return "anon"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def rag_collection_name(user_id: str, knowledge_base_id: str) -> str:
    return f"kb_{_normalize_user_scope(user_id)}_{normalize_knowledge_base_id(knowledge_base_id)}"


def _chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    src = text.strip()
    if not src:
        return []
    if len(src) <= chunk_size:
        return [src]

    chunks: list[str] = []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    while start < len(src):
        end = min(len(src), start + chunk_size)
        chunk = src[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(src):
            break
        start += step
    return chunks


def _normalize_metadata(metadata: dict[str, str] | None) -> dict[str, object]:
    if not metadata:
        return {}
    normalized: dict[str, object] = {}
    for key, value in metadata.items():
        k = str(key).strip()
        if not k:
            continue
        normalized[k[:128]] = str(value)[:2000]
    return normalized


def ingest_knowledge_documents(
    *,
    user_id: str,
    knowledge_base_id: str,
    documents: list[dict[str, object]],
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, object]:
    if not documents:
        raise ValueError("documents is empty")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    kb_id = normalize_knowledge_base_id(knowledge_base_id)
    collection_name = rag_collection_name(user_id, kb_id)

    client = _http_client()
    collection = client.get_or_create_collection(name=collection_name)

    ids: list[str] = []
    chunks: list[str] = []
    metadatas: list[dict[str, object]] = []

    ingested_docs = 0
    for doc in documents:
        text = str(doc.get("text", "") or "").strip()
        if not text:
            continue
        source = str(doc.get("source", "") or "manual").strip() or "manual"
        doc_id = str(doc.get("document_id", "") or "").strip() or str(uuid4())
        extra_meta = _normalize_metadata(
            doc.get("metadata") if isinstance(doc.get("metadata"), dict) else None,
        )
        doc_chunks = _chunk_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        if not doc_chunks:
            continue

        ingested_docs += 1
        total = len(doc_chunks)
        for index, chunk in enumerate(doc_chunks, start=1):
            chunk_id = str(uuid4())
            ids.append(chunk_id)
            chunks.append(chunk)
            metadatas.append(
                {
                    "knowledge_base_id": kb_id,
                    "source": source[:240],
                    "document_id": doc_id,
                    "chunk_index": index,
                    "chunk_total": total,
                    **extra_meta,
                }
            )

    if not ids:
        raise ValueError("no valid documents to ingest")

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "knowledge_base_id": kb_id,
        "collection": collection_name,
        "documents_ingested": ingested_docs,
        "chunks_added": len(ids),
        "document_count": int(collection.count()),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }


def query_knowledge_base(
    *,
    user_id: str,
    knowledge_base_id: str,
    query_text: str,
    top_k: int,
) -> dict[str, object]:
    q = query_text.strip()
    if not q:
        raise ValueError("query text is empty")

    kb_id = normalize_knowledge_base_id(knowledge_base_id)
    collection_name = rag_collection_name(user_id, kb_id)
    client = _http_client()

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        return {
            "knowledge_base_id": kb_id,
            "collection": collection_name,
            "hits": [],
            "hit_count": 0,
        }

    count = int(collection.count())
    if count <= 0:
        return {
            "knowledge_base_id": kb_id,
            "collection": collection_name,
            "hits": [],
            "hit_count": 0,
        }

    limit = max(1, min(int(top_k), count, 20))
    raw = collection.query(query_texts=[q], n_results=limit)

    ids = raw.get("ids") or [[]]
    docs = raw.get("documents") or [[]]
    dists = raw.get("distances") or [[]]
    metas = raw.get("metadatas") or [[]]

    hits: list[dict[str, object]] = []
    row_ids = ids[0] if ids else []
    row_docs = docs[0] if docs else []
    row_dists = dists[0] if dists else []
    row_metas = metas[0] if metas else []

    for index, content in enumerate(row_docs):
        doc_id = row_ids[index] if index < len(row_ids) else str(index)
        distance = row_dists[index] if index < len(row_dists) else None
        metadata = row_metas[index] if index < len(row_metas) else {}
        if not isinstance(metadata, dict):
            metadata = {}

        hits.append(
            {
                "id": str(doc_id),
                "content": str(content or ""),
                "distance": float(distance) if isinstance(distance, (int, float)) else None,
                "metadata": {str(k): v for k, v in metadata.items()},
            }
        )

    return {
        "knowledge_base_id": kb_id,
        "collection": collection_name,
        "hits": hits,
        "hit_count": len(hits),
    }


def get_knowledge_base_status(*, user_id: str, knowledge_base_id: str) -> dict[str, object]:
    kb_id = normalize_knowledge_base_id(knowledge_base_id)
    collection_name = rag_collection_name(user_id, kb_id)
    settings = get_settings()
    base: dict[str, object] = {
        "knowledge_base_id": kb_id,
        "collection": collection_name,
        "chroma_url": settings.chroma_http_url,
        "chroma_reachable": False,
        "collection_exists": False,
        "document_count": 0,
        "error": None,
    }

    try:
        client = _http_client()
        base["chroma_reachable"] = True
    except Exception as exc:  # noqa: BLE001
        base["error"] = (str(exc).strip() or type(exc).__name__)[:300]
        return base

    try:
        collection = client.get_collection(name=collection_name)
        base["collection_exists"] = True
        base["document_count"] = int(collection.count())
    except Exception:
        base["collection_exists"] = False
        base["document_count"] = 0

    return base
