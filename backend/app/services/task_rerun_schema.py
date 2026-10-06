"""Additive lineage and idempotency storage; original tasks stay unchanged."""


def initialize_task_rerun_schema(connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS task_reruns (
            task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            parent_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
            idempotency_key TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, idempotency_key)
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_reruns_parent
        ON task_reruns(user_id, parent_task_id, created_at DESC, task_id)
    """)
