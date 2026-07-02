from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_current_user
from app.services.audit_service import safe_record_audit_event
from app.services.chroma_rag_service import (
    SHARED_RAG_SCOPE_USER_ID,
    clear_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base_status,
    ingest_knowledge_documents,
    is_shared_knowledge_base_id,
    list_knowledge_bases_with_shared,
    query_knowledge_base,
)


router = APIRouter()


def _coerce_payload_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dict(dumped)
    return {}


def _coerce_payload_block_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        row = _coerce_payload_mapping(item)
        if row:
            rows.append(row)
    return rows


def _is_admin_user(current_user: dict) -> bool:
    return str(current_user.get("role") or "").strip().lower() == "admin"


def _resolve_rag_owner_user_id(
    *,
    current_user: dict,
    knowledge_base_id: str,
    mutate: bool,
) -> str:
    if not is_shared_knowledge_base_id(knowledge_base_id):
        return str(current_user["id"])
    if mutate and not _is_admin_user(current_user):
        raise HTTPException(
            status_code=403,
            detail="shared knowledge base is admin-only for write operations",
        )
    return SHARED_RAG_SCOPE_USER_ID


class RagDocumentInput(BaseModel):
    text: str = Field(min_length=1, max_length=64_000)
    source: str | None = Field(default=None, max_length=240)
    document_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, str] | None = Field(
        default=None,
        description="可选；字符串键值 metadata",
    )


class RagIngestRequest(BaseModel):
    knowledge_base_id: str = Field(default="default", max_length=64)
    documents: list[RagDocumentInput] = Field(min_length=1, max_length=100)
    chunk_size: int = Field(default=500, ge=120, le=2000)
    chunk_overlap: int = Field(default=80, ge=0, le=400)

    @field_validator("knowledge_base_id")
    @classmethod
    def _validate_kb_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return "default"
        return normalized


class RagIngestResponse(BaseModel):
    knowledge_base_id: str
    collection: str
    documents_ingested: int
    chunks_added: int
    document_count: int
    chunk_size: int
    chunk_overlap: int


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    knowledge_base_id: str = Field(default="default", max_length=64)
    top_k: int = Field(default=4, ge=1, le=20)


class RagHit(BaseModel):
    id: str
    content: str
    distance: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagQueryResponse(BaseModel):
    knowledge_base_id: str
    collection: str
    hits: list[RagHit]
    hit_count: int


class RagStatusResponse(BaseModel):
    knowledge_base_id: str
    collection: str
    chroma_url: str
    chroma_reachable: bool
    collection_exists: bool
    document_count: int
    error: str | None = None


class RagKnowledgeBaseSummary(BaseModel):
    knowledge_base_id: str
    collection: str
    document_count: int


class RagKnowledgeBaseListResponse(BaseModel):
    knowledge_bases: list[RagKnowledgeBaseSummary]
    knowledge_base_count: int
    chroma_url: str
    chroma_reachable: bool
    error: str | None = None


class RagKnowledgeBaseMutateResponse(BaseModel):
    knowledge_base_id: str
    collection: str
    existed: bool
    deleted_chunks: int
    document_count: int | None = None


@router.get("/status", response_model=RagStatusResponse)
def get_rag_status(
    knowledge_base_id: str = Query(default="default", max_length=64),
    current_user: dict = Depends(get_current_user),
) -> RagStatusResponse:
    owner_user_id = _resolve_rag_owner_user_id(
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
        mutate=False,
    )
    raw = _coerce_payload_mapping(
        get_knowledge_base_status(
            user_id=owner_user_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    return RagStatusResponse(**raw)


@router.get("/knowledge-bases", response_model=RagKnowledgeBaseListResponse)
def get_rag_knowledge_bases(
    current_user: dict = Depends(get_current_user),
) -> RagKnowledgeBaseListResponse:
    raw = _coerce_payload_mapping(
        list_knowledge_bases_with_shared(
            user_id=str(current_user["id"]),
            include_shared=True,
        )
    )
    raw["knowledge_bases"] = _coerce_payload_block_list(raw.get("knowledge_bases"))
    return RagKnowledgeBaseListResponse(**raw)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/clear",
    response_model=RagKnowledgeBaseMutateResponse,
)
def post_rag_clear_knowledge_base(
    knowledge_base_id: str,
    current_user: dict = Depends(get_current_user),
) -> RagKnowledgeBaseMutateResponse:
    user_id = str(current_user["id"])
    owner_user_id = _resolve_rag_owner_user_id(
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
        mutate=True,
    )
    try:
        raw = _coerce_payload_mapping(
            clear_knowledge_base(
                user_id=owner_user_id,
                knowledge_base_id=knowledge_base_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    safe_record_audit_event(
        user_id=user_id,
        event_type="rag_kb_clear",
        detail={
            "knowledge_base_id": raw.get("knowledge_base_id"),
            "collection": raw.get("collection"),
            "deleted_chunks": raw.get("deleted_chunks"),
            "existed": raw.get("existed"),
            "scope": "shared" if owner_user_id == SHARED_RAG_SCOPE_USER_ID else "private",
        },
    )
    return RagKnowledgeBaseMutateResponse(**raw)


@router.delete(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=RagKnowledgeBaseMutateResponse,
)
def delete_rag_knowledge_base(
    knowledge_base_id: str,
    current_user: dict = Depends(get_current_user),
) -> RagKnowledgeBaseMutateResponse:
    user_id = str(current_user["id"])
    owner_user_id = _resolve_rag_owner_user_id(
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
        mutate=True,
    )
    try:
        raw = _coerce_payload_mapping(
            delete_knowledge_base(
                user_id=owner_user_id,
                knowledge_base_id=knowledge_base_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    safe_record_audit_event(
        user_id=user_id,
        event_type="rag_kb_delete",
        detail={
            "knowledge_base_id": raw.get("knowledge_base_id"),
            "collection": raw.get("collection"),
            "deleted_chunks": raw.get("deleted_chunks"),
            "existed": raw.get("existed"),
            "scope": "shared" if owner_user_id == SHARED_RAG_SCOPE_USER_ID else "private",
        },
    )
    return RagKnowledgeBaseMutateResponse(**raw)


@router.post("/ingest", response_model=RagIngestResponse)
def post_rag_ingest(
    payload: RagIngestRequest,
    current_user: dict = Depends(get_current_user),
) -> RagIngestResponse:
    user_id = str(current_user["id"])
    owner_user_id = _resolve_rag_owner_user_id(
        current_user=current_user,
        knowledge_base_id=payload.knowledge_base_id,
        mutate=True,
    )
    docs = [x.model_dump(exclude_none=True) for x in payload.documents]
    try:
        raw = _coerce_payload_mapping(
            ingest_knowledge_documents(
                user_id=owner_user_id,
                knowledge_base_id=payload.knowledge_base_id,
                documents=docs,
                chunk_size=payload.chunk_size,
                chunk_overlap=payload.chunk_overlap,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    safe_record_audit_event(
        user_id=user_id,
        event_type="rag_ingest",
        detail={
            "knowledge_base_id": raw.get("knowledge_base_id"),
            "collection": raw.get("collection"),
            "documents_ingested": raw.get("documents_ingested"),
            "chunks_added": raw.get("chunks_added"),
            "document_count": raw.get("document_count"),
            "chunk_size": payload.chunk_size,
            "chunk_overlap": payload.chunk_overlap,
            "scope": "shared" if owner_user_id == SHARED_RAG_SCOPE_USER_ID else "private",
        },
    )
    return RagIngestResponse(**raw)


@router.post("/query", response_model=RagQueryResponse)
def post_rag_query(
    payload: RagQueryRequest,
    current_user: dict = Depends(get_current_user),
) -> RagQueryResponse:
    owner_user_id = _resolve_rag_owner_user_id(
        current_user=current_user,
        knowledge_base_id=payload.knowledge_base_id,
        mutate=False,
    )
    try:
        raw = _coerce_payload_mapping(
            query_knowledge_base(
                user_id=owner_user_id,
                knowledge_base_id=payload.knowledge_base_id,
                query_text=payload.query,
                top_k=payload.top_k,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    raw["hits"] = _coerce_payload_block_list(raw.get("hits"))
    return RagQueryResponse(**raw)
