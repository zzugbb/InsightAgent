"""RAG knowledge-base collections on Chroma: ingest, query, and status."""

from __future__ import annotations

import hashlib
import re
from uuid import uuid4

import chromadb

from app.config import get_settings

SHARED_RAG_SCOPE_USER_ID = "__shared__"
SHARED_RAG_KB_PREFIX = "shared-"
_RAG_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|access[_-]?token|authorization|bearer|token|secret|password)",
    re.IGNORECASE,
)
_RAG_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_RAG_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(^|[?&#;\s])(?:api[_-]?key|access[_-]?token|token|secret|password)=[^&#;\s]+"
)
_RAG_DOCUMENT_VERSION_RE = re.compile(r"^sha256:[a-f0-9]{16,64}$")
_RAG_CONTENT_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_RAG_RESERVED_METADATA_KEY_TOKENS = {
    "knowledgebaseid",
    "source",
    "documentid",
    "documentversion",
    "contenthash",
    "chunkindex",
    "chunktotal",
}
_RAG_RESERVED_METADATA_CANONICAL_KEYS = {
    "knowledgebaseid": "knowledge_base_id",
    "source": "source",
    "documentid": "document_id",
    "documentversion": "document_version",
    "contenthash": "content_hash",
    "chunkindex": "chunk_index",
    "chunktotal": "chunk_total",
}


def _http_client() -> chromadb.HttpClient:
    settings = get_settings()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )
    client.heartbeat()
    return client


def _sanitize_rag_identifier_text(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    safe = _RAG_BEARER_TOKEN_RE.sub("[redacted]", raw)
    return _RAG_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        safe,
    )


def sanitize_rag_error_message(value: object, *, limit: int = 400) -> str:
    safe = _sanitize_rag_metadata_text(value, limit=limit)
    return safe or type(value).__name__


def normalize_knowledge_base_id(value: str | None) -> str:
    raw = (_sanitize_rag_identifier_text(value) or "default").strip().lower()
    if not raw:
        return "default"
    normalized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    if not normalized:
        return "default"
    return normalized[:48]


def is_shared_knowledge_base_id(value: str | None) -> bool:
    kb_id = normalize_knowledge_base_id(value)
    return kb_id.startswith(SHARED_RAG_KB_PREFIX)


def _normalize_user_scope(user_id: str) -> str:
    raw = user_id.strip().lower()
    if not raw:
        return "anon"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def rag_collection_name(user_id: str, knowledge_base_id: str) -> str:
    return f"kb_{_normalize_user_scope(user_id)}_{normalize_knowledge_base_id(knowledge_base_id)}"


def _rag_collection_prefix(user_id: str) -> str:
    return f"kb_{_normalize_user_scope(user_id)}_"


def _resolve_collection_name(entry: object) -> str | None:
    if isinstance(entry, str):
        resolved = entry.strip()
        return resolved or None
    if isinstance(entry, dict):
        raw = entry.get("name")
        if isinstance(raw, str):
            resolved = raw.strip()
            return resolved or None
        return None
    raw = getattr(entry, "name", None)
    if isinstance(raw, str):
        resolved = raw.strip()
        return resolved or None
    return None


def _coerce_metadata_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return {str(k): v for k, v in dumped.items()}
    return {}


def _coerce_query_payload_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _coerce_document_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _coerce_payload_block_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, (list, tuple)):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        row = _coerce_document_mapping(item)
        if row:
            rows.append(row)
    return rows


def _coerce_metadata_block_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, (list, tuple)):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        rows.append(_normalize_metadata(item))
    return [row for row in rows if row]


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


def _rag_metadata_key_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _is_reserved_rag_metadata_key(value: object) -> bool:
    return _rag_metadata_key_token(value) in _RAG_RESERVED_METADATA_KEY_TOKENS


def _normalize_metadata(
    metadata: object,
    *,
    allow_reserved: bool = True,
) -> dict[str, object]:
    metadata_dict = _coerce_metadata_mapping(metadata)
    if not metadata_dict:
        return {}
    normalized: dict[str, object] = {}
    for key, value in metadata_dict.items():
        key_token = _rag_metadata_key_token(key)
        if not allow_reserved and key_token in _RAG_RESERVED_METADATA_KEY_TOKENS:
            continue
        k = _sanitize_rag_metadata_key(key)
        if not k:
            continue
        safe_key_token = _rag_metadata_key_token(k)
        if not allow_reserved and safe_key_token in _RAG_RESERVED_METADATA_KEY_TOKENS:
            continue
        safe_value = _sanitize_rag_metadata_text(value, limit=2000)
        if safe_key_token == "documentversion" and not _RAG_DOCUMENT_VERSION_RE.fullmatch(
            safe_value
        ):
            continue
        if safe_key_token == "contenthash" and not _RAG_CONTENT_HASH_RE.fullmatch(
            safe_value
        ):
            continue
        normalized[_RAG_RESERVED_METADATA_CANONICAL_KEYS.get(safe_key_token, k)] = (
            safe_value
        )
    return normalized


def _sanitize_rag_metadata_text(value: object, *, limit: int) -> str:
    raw = str(value).strip()
    if not raw:
        return ""
    safe = _RAG_BEARER_TOKEN_RE.sub("[redacted]", raw)
    safe = _RAG_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        safe,
    )
    return safe[:limit]


def _sanitize_rag_metadata_key(value: object) -> str:
    raw = str(value).strip()
    if not raw:
        return ""
    if _RAG_SENSITIVE_KEY_RE.search(raw):
        return "[redacted]"
    return raw[:128]


def _rag_document_content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _rag_document_version(
    *,
    knowledge_base_id: str,
    source: str,
    document_id: str,
    content_hash: str,
) -> str:
    seed = "\x1f".join([knowledge_base_id, source, document_id, content_hash])
    return f"sha256:{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _collection_document_version_summaries(
    collection: object,
    *,
    document_count: int,
) -> list[dict[str, object]]:
    if document_count <= 0:
        return []
    getter = getattr(collection, "get", None)
    if not callable(getter):
        return []
    try:
        raw = _coerce_query_payload_mapping(
            getter(include=["metadatas"], limit=min(document_count, 5000))
        )
    except TypeError:
        try:
            raw = _coerce_query_payload_mapping(getter(include=["metadatas"]))
        except Exception:
            return []
    except Exception:
        return []

    rows = _coerce_metadata_block_list(raw.get("metadatas"))
    grouped: dict[str, dict[str, object]] = {}
    for metadata in rows:
        document_version = str(metadata.get("document_version") or "").strip()
        content_hash = str(metadata.get("content_hash") or "").strip()
        if not _RAG_DOCUMENT_VERSION_RE.fullmatch(document_version):
            continue
        if not _RAG_CONTENT_HASH_RE.fullmatch(content_hash):
            continue
        key = f"{document_version}\x1f{content_hash}"
        source = str(metadata.get("source") or "").strip()
        document_id = str(metadata.get("document_id") or "").strip()
        if key not in grouped:
            grouped[key] = {
                "document_version": document_version,
                "content_hash": content_hash,
                "source": source,
                "document_id": document_id,
                "chunk_count": 0,
            }
        grouped[key]["chunk_count"] = int(grouped[key]["chunk_count"]) + 1

    summaries = list(grouped.values())
    summaries.sort(
        key=lambda item: (
            str(item.get("source") or ""),
            str(item.get("document_id") or ""),
            str(item.get("document_version") or ""),
        )
    )
    return summaries


def _apply_document_version_summary(
    row: dict[str, object],
    collection: object,
    *,
    document_count: int,
) -> None:
    document_versions = _collection_document_version_summaries(
        collection,
        document_count=document_count,
    )
    row["unique_document_count"] = len(document_versions)
    row["document_versions"] = document_versions


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
    for raw_doc in documents:
        doc = _coerce_document_mapping(raw_doc)
        text = str(doc.get("text", "") or "").strip()
        if not text:
            continue
        source = (
            _sanitize_rag_metadata_text(doc.get("source", "") or "manual", limit=240)
            or "manual"
        )
        doc_id = (
            _sanitize_rag_metadata_text(doc.get("document_id", "") or "", limit=128)
            or str(uuid4())
        )
        content_hash = _rag_document_content_hash(text)
        document_version = _rag_document_version(
            knowledge_base_id=kb_id,
            source=source,
            document_id=doc_id,
            content_hash=content_hash,
        )
        extra_meta = _normalize_metadata(doc.get("metadata"), allow_reserved=False)
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
                    "source": source,
                    "document_id": doc_id,
                    "document_version": document_version,
                    "content_hash": content_hash,
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
    raw = _coerce_query_payload_mapping(
        collection.query(query_texts=[q], n_results=limit)
    )

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

        hits.append(
            {
                "id": str(doc_id),
                "content": str(content or ""),
                "distance": float(distance) if isinstance(distance, (int, float)) else None,
                "metadata": _normalize_metadata(metadata),
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
        "unique_document_count": 0,
        "document_versions": [],
        "error": None,
    }

    try:
        client = _http_client()
        base["chroma_reachable"] = True
    except Exception as exc:  # noqa: BLE001
        base["error"] = sanitize_rag_error_message(exc, limit=300)
        return base

    try:
        collection = client.get_collection(name=collection_name)
        base["collection_exists"] = True
        document_count = int(collection.count())
        base["document_count"] = document_count
        _apply_document_version_summary(
            base,
            collection,
            document_count=document_count,
        )
    except Exception:
        base["collection_exists"] = False
        base["document_count"] = 0
        base["unique_document_count"] = 0
        base["document_versions"] = []

    return base


def list_knowledge_bases(*, user_id: str) -> dict[str, object]:
    settings = get_settings()
    result: dict[str, object] = {
        "knowledge_bases": [],
        "knowledge_base_count": 0,
        "chroma_url": settings.chroma_http_url,
        "chroma_reachable": False,
        "error": None,
    }
    try:
        client = _http_client()
        result["chroma_reachable"] = True
    except Exception as exc:  # noqa: BLE001
        result["error"] = sanitize_rag_error_message(exc, limit=300)
        return result

    prefix = _rag_collection_prefix(user_id)
    try:
        collections = client.list_collections()
    except Exception as exc:  # noqa: BLE001
        result["error"] = sanitize_rag_error_message(exc, limit=300)
        return result

    rows: list[dict[str, object]] = []
    for entry in collections:
        collection_name = _resolve_collection_name(entry)
        if not collection_name or not collection_name.startswith(prefix):
            continue
        kb_id = collection_name[len(prefix) :].strip()
        if not kb_id:
            continue
        if user_id != SHARED_RAG_SCOPE_USER_ID and is_shared_knowledge_base_id(kb_id):
            continue
        row: dict[str, object] = {
            "knowledge_base_id": kb_id,
            "collection": collection_name,
            "document_count": 0,
            "unique_document_count": 0,
            "document_versions": [],
        }
        try:
            collection = client.get_collection(name=collection_name)
            document_count = int(collection.count())
            row["document_count"] = document_count
            _apply_document_version_summary(
                row,
                collection,
                document_count=document_count,
            )
        except Exception:
            pass
        rows.append(row)

    rows.sort(key=lambda item: str(item["knowledge_base_id"]))
    result["knowledge_bases"] = rows
    result["knowledge_base_count"] = len(rows)
    return result


def list_knowledge_bases_with_shared(
    *,
    user_id: str,
    include_shared: bool,
) -> dict[str, object]:
    result = _coerce_document_mapping(list_knowledge_bases(user_id=user_id))
    if not include_shared:
        result["knowledge_bases"] = _coerce_payload_block_list(
            result.get("knowledge_bases")
        )
        result["knowledge_base_count"] = len(result["knowledge_bases"])
        return result
    if user_id == SHARED_RAG_SCOPE_USER_ID:
        result["knowledge_bases"] = _coerce_payload_block_list(
            result.get("knowledge_bases")
        )
        result["knowledge_base_count"] = len(result["knowledge_bases"])
        return result
    shared = _coerce_document_mapping(
        list_knowledge_bases(user_id=SHARED_RAG_SCOPE_USER_ID)
    )
    own_rows = _coerce_payload_block_list(result.get("knowledge_bases"))
    shared_rows = _coerce_payload_block_list(shared.get("knowledge_bases"))
    merged = own_rows + shared_rows
    merged.sort(key=lambda item: str(item.get("knowledge_base_id") or ""))
    result["knowledge_bases"] = merged
    result["knowledge_base_count"] = len(merged)
    if not result.get("error") and shared.get("error"):
        result["error"] = shared.get("error")
    if shared.get("chroma_reachable") is False:
        result["chroma_reachable"] = False
    return result


def clear_knowledge_base(*, user_id: str, knowledge_base_id: str) -> dict[str, object]:
    kb_id = normalize_knowledge_base_id(knowledge_base_id)
    collection_name = rag_collection_name(user_id, kb_id)

    client = _http_client()
    existed = False
    deleted_chunks = 0
    try:
        collection = client.get_collection(name=collection_name)
        existed = True
        deleted_chunks = int(collection.count())
    except Exception:
        existed = False
        deleted_chunks = 0

    if existed:
        client.delete_collection(name=collection_name)
        client.get_or_create_collection(name=collection_name)

    return {
        "knowledge_base_id": kb_id,
        "collection": collection_name,
        "existed": existed,
        "deleted_chunks": deleted_chunks,
        "document_count": 0,
    }


def delete_knowledge_base(*, user_id: str, knowledge_base_id: str) -> dict[str, object]:
    kb_id = normalize_knowledge_base_id(knowledge_base_id)
    collection_name = rag_collection_name(user_id, kb_id)

    client = _http_client()
    existed = False
    deleted_chunks = 0
    try:
        collection = client.get_collection(name=collection_name)
        existed = True
        deleted_chunks = int(collection.count())
    except Exception:
        existed = False
        deleted_chunks = 0

    if existed:
        client.delete_collection(name=collection_name)

    return {
        "knowledge_base_id": kb_id,
        "collection": collection_name,
        "existed": existed,
        "deleted_chunks": deleted_chunks,
    }
