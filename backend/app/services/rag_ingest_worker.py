"""RAG import worker with per-job session locks and restart recovery."""

from __future__ import annotations

import json
import argparse
import os
import threading
import time
from collections.abc import Callable

from app.db import get_db_connection
from app.services.audit_service import safe_record_audit_event
from app.services.chroma_rag_service import (
    SHARED_RAG_SCOPE_USER_ID, ingest_knowledge_documents, rag_collection_name,
)
from app.services.rag_ingest_jobs import advisory_key, utc_now


def recover_interrupted_jobs() -> int:
    recovered = 0
    with get_db_connection() as connection:
        rows = connection.execute("SELECT id FROM rag_ingest_jobs WHERE status = 'running'").fetchall()
        for row in rows:
            key = advisory_key(f"rag-job:{row['id']}")
            acquired = connection.execute("SELECT pg_try_advisory_lock(?) AS acquired", (key,)).fetchone()
            if not acquired["acquired"]:
                continue
            try:
                cursor = connection.execute(
                    """UPDATE rag_ingest_jobs SET status = 'failed', error_code = 'interrupted',
                       payload_json = NULL, finished_at = ? WHERE id = ? AND status = 'running'""",
                    (utc_now(), row["id"]),
                )
                connection.commit()
                recovered += cursor.rowcount
            finally:
                connection.execute("SELECT pg_advisory_unlock(?)", (key,))
    return recovered


def process_next_job(*, on_started: Callable[[], None] | None = None) -> bool:
    with get_db_connection() as connection:
        row = connection.execute(
            """SELECT * FROM rag_ingest_jobs WHERE status = 'queued'
               ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED""",
        ).fetchone()
        if not row:
            return False
        key = advisory_key(f"rag-job:{row['id']}")
        acquired = connection.execute("SELECT pg_try_advisory_lock(?) AS acquired", (key,)).fetchone()
        if not acquired["acquired"]:
            return False
        try:
            connection.execute(
                "UPDATE rag_ingest_jobs SET status = 'running', started_at = ? WHERE id = ?",
                (utc_now(), row["id"]),
            )
            connection.commit()
            if on_started:
                on_started()
            error_code = None
            result = None
            try:
                user = connection.execute("SELECT role FROM users WHERE id = ?", (row["user_id"],)).fetchone()
                # Don't retain an idle transaction during external I/O.
                connection.commit()
                if not user or (row["owner_user_id"] == SHARED_RAG_SCOPE_USER_ID
                                and str(user["role"]).lower() != "admin"):
                    error_code = "permission_revoked"
                else:
                    payload = json.loads(row["payload_json"])
                    raw = ingest_knowledge_documents(user_id=row["owner_user_id"], **payload)
                    result = {
                        "knowledge_base_id": row["knowledge_base_id"],
                        "collection": rag_collection_name(row["owner_user_id"], row["knowledge_base_id"]),
                        **{field: int(raw[field]) for field in (
                            "documents_ingested", "chunks_added", "document_count", "chunk_size", "chunk_overlap",
                        )},
                    }
            except ValueError:
                error_code = "invalid_input"
            except Exception:  # noqa: BLE001
                error_code = "chroma_unavailable"
            connection.execute(
                """UPDATE rag_ingest_jobs SET status = ?, result_json = ?, error_code = ?,
                   payload_json = NULL, finished_at = ? WHERE id = ? AND status = 'running'""",
                ("failed" if error_code else "completed", json.dumps(result) if result else None,
                 error_code, utc_now(), row["id"]),
            )
            connection.commit()
            safe_record_audit_event(
                user_id=row["user_id"], event_type="rag_ingest_job_finished",
                detail={"job_id": row["id"], "knowledge_base_id": row["knowledge_base_id"],
                        "status": "failed" if error_code else "completed", "error_code": error_code,
                        "scope": "shared" if row["owner_user_id"] == SHARED_RAG_SCOPE_USER_ID else "private"},
            )
            return True
        finally:
            connection.execute("SELECT pg_advisory_unlock(?)", (key,))


def main() -> int:
    try:
        recover_interrupted_jobs()
        process_next_job()
    except Exception:  # noqa: BLE001
        # Never print documents, connection strings or upstream exception bodies.
        return 1
    return 0


def _watch_parent(parent_pid: int) -> None:
    while True:
        if os.getppid() != parent_pid:
            # Exit even during unresponsive external I/O; session locks are released.
            os._exit(1)
        time.sleep(0.5)


def run_loop(*, parent_pid: int | None = None) -> None:
    if parent_pid is not None:
        threading.Thread(target=_watch_parent, args=(parent_pid,), daemon=True).start()
    def heartbeat() -> None:
        # Fixed heartbeat only: no job identifiers or document content on stdout.
        print("tick", flush=True)
    while True:
        try:
            recover_interrupted_jobs()
            processed = process_next_job(on_started=heartbeat)
        except Exception:  # noqa: BLE001
            processed = False
        heartbeat()
        if not processed:
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args()
    if args.loop:
        run_loop(parent_pid=args.parent_pid)
    else:
        raise SystemExit(main())
