"""Additive schema for durable RAG import jobs."""


def initialize_ingest_schema(connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS rag_ingest_jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            owner_user_id TEXT NOT NULL,
            knowledge_base_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT,
            document_total INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN
                ('queued', 'running', 'completed', 'failed', 'cancelled')),
            result_json TEXT,
            error_code TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            UNIQUE(user_id, idempotency_key)
        )
    """)
    # Also upgrade existing installations without replacing their job history.
    connection.execute("ALTER TABLE rag_ingest_jobs ADD COLUMN IF NOT EXISTS progress_json TEXT")
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_ingest_jobs_queue
        ON rag_ingest_jobs(created_at, id) WHERE status = 'queued'
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_ingest_jobs_user_kb
        ON rag_ingest_jobs(user_id, knowledge_base_id, created_at DESC)
    """)
