from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.services.chroma_rag_service import (
    get_knowledge_base_status,
    ingest_knowledge_documents,
    query_knowledge_base,
)


router = APIRouter()


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


@router.get("/status", response_model=RagStatusResponse)
def get_rag_status(
    knowledge_base_id: str = Query(default="default", max_length=64),
) -> RagStatusResponse:
    raw = get_knowledge_base_status(knowledge_base_id=knowledge_base_id)
    return RagStatusResponse(**raw)


@router.post("/ingest", response_model=RagIngestResponse)
def post_rag_ingest(payload: RagIngestRequest) -> RagIngestResponse:
    docs = [x.model_dump(exclude_none=True) for x in payload.documents]
    try:
        raw = ingest_knowledge_documents(
            knowledge_base_id=payload.knowledge_base_id,
            documents=docs,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    return RagIngestResponse(**raw)


@router.post("/query", response_model=RagQueryResponse)
def post_rag_query(payload: RagQueryRequest) -> RagQueryResponse:
    try:
        raw = query_knowledge_base(
            knowledge_base_id=payload.knowledge_base_id,
            query_text=payload.query,
            top_k=payload.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc
    return RagQueryResponse(**raw)
