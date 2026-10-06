"""Durable import queue. Public views never include document text or metadata."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.db import get_db_connection
from app.services.audit_service import safe_record_audit_event
from app.services.chroma_rag_service import normalize_knowledge_base_id

MAX_ACTIVE_JOBS_PER_USER = 3
MAX_PAYLOAD_BYTES = 1_000_000
PUBLIC_COLUMNS = (
    "id, knowledge_base_id, document_total, status, result_json, error_code, "
    "created_at, started_at, finished_at"
)


class IngestJobError(Exception):
    def __init__(self, status_code: int, code: str):
        super().__init__(code)
        self.status_code = status_code
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def advisory_key(scope: str) -> int:
    return int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], "big", signed=True)


def public_job(row: dict) -> dict:
    return {
        "id": row["id"],
        "knowledge_base_id": normalize_knowledge_base_id(row["knowledge_base_id"]),
        "document_total": row["document_total"],
        "status": row["status"],
        "result": json.loads(row["result_json"]) if row.get("result_json") else None,
        "error_code": row.get("error_code"),
        "created_at": row["created_at"],
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
    }


def create_ingest_job(*, user_id: str, owner_user_id: str, payload: dict,
                      idempotency_key: str) -> dict:
    payload = {**payload, "knowledge_base_id": normalize_knowledge_base_id(payload["knowledge_base_id"])}
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(serialized.encode()) > MAX_PAYLOAD_BYTES:
        raise IngestJobError(413, "ingest_payload_too_large")
    payload_hash = hashlib.sha256(serialized.encode()).hexdigest()
    with get_db_connection() as connection:
        # Serialize quota and idempotency checks across API instances for this user.
        connection.execute("SELECT pg_advisory_xact_lock(?)", (advisory_key(f"rag-submit:{user_id}"),))
        existing = connection.execute(
            f"SELECT {PUBLIC_COLUMNS}, payload_hash FROM rag_ingest_jobs WHERE user_id = ? AND idempotency_key = ?",
            (user_id, idempotency_key),
        ).fetchone()
        if existing:
            if existing["payload_hash"] != payload_hash:
                raise IngestJobError(409, "ingest_idempotency_conflict")
            return public_job(existing)
        active = connection.execute(
            "SELECT COUNT(*) AS total FROM rag_ingest_jobs WHERE user_id = ? AND status IN ('queued', 'running')",
            (user_id,),
        ).fetchone()
        if active["total"] >= MAX_ACTIVE_JOBS_PER_USER:
            raise IngestJobError(429, "ingest_queue_full")
        row = connection.execute(
            f"""INSERT INTO rag_ingest_jobs
                (id, user_id, owner_user_id, knowledge_base_id, idempotency_key,
                 payload_hash, payload_json, document_total, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?) RETURNING {PUBLIC_COLUMNS}""",
            (str(uuid4()), user_id, owner_user_id, payload["knowledge_base_id"],
             idempotency_key, payload_hash, serialized, len(payload["documents"]), utc_now()),
        ).fetchone()
        connection.commit()
    safe_record_audit_event(user_id=user_id, event_type="rag_ingest_job_created",
                            detail={"job_id": row["id"], "knowledge_base_id": payload["knowledge_base_id"]})
    return public_job(row)


def list_ingest_jobs(*, user_id: str, knowledge_base_id: str | None, limit: int) -> list[dict]:
    query = f"SELECT {PUBLIC_COLUMNS} FROM rag_ingest_jobs WHERE user_id = ?"
    params: list = [user_id]
    if knowledge_base_id is not None:
        query += " AND knowledge_base_id = ?"
        params.append(normalize_knowledge_base_id(knowledge_base_id))
    query += " ORDER BY CASE WHEN status IN ('queued', 'running') THEN 0 ELSE 1 END, created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [public_job(row) for row in rows]


def get_ingest_job(*, user_id: str, job_id: str) -> dict:
    with get_db_connection() as connection:
        row = connection.execute(
            f"SELECT {PUBLIC_COLUMNS} FROM rag_ingest_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
    if not row:
        raise IngestJobError(404, "ingest_job_not_found")
    return public_job(row)


def cancel_ingest_job(*, user_id: str, job_id: str) -> dict:
    with get_db_connection() as connection:
        row = connection.execute(
            f"SELECT {PUBLIC_COLUMNS} FROM rag_ingest_jobs WHERE id = ? AND user_id = ? FOR UPDATE",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise IngestJobError(404, "ingest_job_not_found")
        if row["status"] == "cancelled":
            return public_job(row)
        if row["status"] != "queued":
            raise IngestJobError(409, "ingest_job_not_queued")
        row = connection.execute(
            f"""UPDATE rag_ingest_jobs SET status = 'cancelled', payload_json = NULL,
                finished_at = ? WHERE id = ? RETURNING {PUBLIC_COLUMNS}""",
            (utc_now(), job_id),
        ).fetchone()
        connection.commit()
    safe_record_audit_event(user_id=user_id, event_type="rag_ingest_job_cancelled",
                            detail={"job_id": job_id, "knowledge_base_id": row["knowledge_base_id"]})
    return public_job(row)
