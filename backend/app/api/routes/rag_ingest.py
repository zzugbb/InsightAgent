"""Asynchronous RAG ingestion; the existing synchronous API remains compatible."""

from typing import Literal, NoReturn
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.api.deps import get_current_user
from app.api.routes.rag import RagIngestRequest, RagIngestResponse, _resolve_rag_owner_user_id
from app.services.rag_ingest_jobs import (
    IngestJobError, cancel_ingest_job, create_ingest_job, get_ingest_job, list_ingest_jobs,
)

router = APIRouter()


class RagIngestJobRequest(RagIngestRequest):
    idempotency_key: UUID = Field(default_factory=uuid4)

    @model_validator(mode="after")
    def validate_import(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if any(not document.text.strip() for document in self.documents):
            raise ValueError("documents must contain nonblank text")
        if sum(len(document.text) for document in self.documents) > 512_000:
            raise ValueError("total document text exceeds 512000 characters")
        return self


class RagIngestJobResponse(BaseModel):
    id: str
    knowledge_base_id: str
    document_total: int
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    result: RagIngestResponse | None = None
    error_code: Literal["invalid_input", "chroma_unavailable", "interrupted", "permission_revoked"] | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class RagIngestJobListResponse(BaseModel):
    items: list[RagIngestJobResponse]


def _translate_error(exc: IngestJobError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post("/ingest-jobs", response_model=RagIngestJobResponse, status_code=202)
def post_ingest_job(payload: RagIngestJobRequest,
                    current_user: dict = Depends(get_current_user)) -> RagIngestJobResponse:
    owner = _resolve_rag_owner_user_id(
        current_user=current_user, knowledge_base_id=payload.knowledge_base_id, mutate=True,
    )
    try:
        job = create_ingest_job(
            user_id=str(current_user["id"]), owner_user_id=owner,
            payload=payload.model_dump(exclude={"idempotency_key"}, exclude_none=True),
            idempotency_key=str(payload.idempotency_key),
        )
    except IngestJobError as exc:
        _translate_error(exc)
    return RagIngestJobResponse(**job)


@router.get("/ingest-jobs", response_model=RagIngestJobListResponse)
def get_ingest_jobs(knowledge_base_id: str | None = Query(default=None, max_length=64),
                    limit: int = Query(default=20, ge=1, le=100),
                    current_user: dict = Depends(get_current_user)) -> RagIngestJobListResponse:
    return RagIngestJobListResponse(items=list_ingest_jobs(
        user_id=str(current_user["id"]), knowledge_base_id=knowledge_base_id, limit=limit,
    ))


@router.get("/ingest-jobs/{job_id}", response_model=RagIngestJobResponse)
def get_ingest_job_detail(job_id: UUID,
                          current_user: dict = Depends(get_current_user)) -> RagIngestJobResponse:
    try:
        job = get_ingest_job(user_id=str(current_user["id"]), job_id=str(job_id))
    except IngestJobError as exc:
        _translate_error(exc)
    return RagIngestJobResponse(**job)


@router.post("/ingest-jobs/{job_id}/cancel", response_model=RagIngestJobResponse)
def post_cancel_ingest_job(job_id: UUID,
                           current_user: dict = Depends(get_current_user)) -> RagIngestJobResponse:
    try:
        job = cancel_ingest_job(user_id=str(current_user["id"]), job_id=str(job_id))
    except IngestJobError as exc:
        _translate_error(exc)
    return RagIngestJobResponse(**job)
