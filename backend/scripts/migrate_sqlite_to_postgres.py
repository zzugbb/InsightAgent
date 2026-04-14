from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate InsightAgent data from SQLite to PostgreSQL.",
    )
    parser.add_argument(
        "--sqlite-path",
        required=True,
        help="Path to source sqlite.db",
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Target PostgreSQL URL, e.g. postgresql://user:pass@host:5432/db",
    )
    return parser.parse_args()


def _read_sqlite_rows(sqlite_path: Path, table: str, columns: list[str]) -> list[dict]:
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            f"SELECT {', '.join(columns)} FROM {table}"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _ensure_postgres_schema(pg_connection) -> None:
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY,
            mode TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            base_url TEXT,
            api_key TEXT
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            base_url TEXT,
            api_key_enc TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            session_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            trace_json TEXT,
            usage_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
        """
    )
    pg_connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            session_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        )
        """
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON tasks(session_id)"
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)"
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)"
    )
    pg_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_task_id ON messages(task_id)"
    )


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"sqlite source not found: {sqlite_path}")

    users = _read_sqlite_rows(
        sqlite_path,
        "users",
        [
            "id",
            "email",
            "display_name",
            "password_salt",
            "password_hash",
            "created_at",
            "updated_at",
        ],
    )
    user_settings = _read_sqlite_rows(
        sqlite_path,
        "user_settings",
        [
            "user_id",
            "mode",
            "provider",
            "model",
            "base_url",
            "api_key_enc",
            "created_at",
            "updated_at",
        ],
    )
    sessions = _read_sqlite_rows(
        sqlite_path,
        "sessions",
        ["id", "user_id", "title", "created_at", "updated_at"],
    )
    tasks = _read_sqlite_rows(
        sqlite_path,
        "tasks",
        [
            "id",
            "user_id",
            "session_id",
            "prompt",
            "status",
            "trace_json",
            "usage_json",
            "created_at",
            "updated_at",
        ],
    )
    messages = _read_sqlite_rows(
        sqlite_path,
        "messages",
        [
            "id",
            "user_id",
            "session_id",
            "task_id",
            "role",
            "content",
            "created_at",
        ],
    )

    try:
        import psycopg
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "psycopg is required. Please install backend requirements first."
        ) from exc

    with psycopg.connect(args.database_url) as pg_connection:
        _ensure_postgres_schema(pg_connection)

        for row in users:
            pg_connection.execute(
                """
                INSERT INTO users(
                    id, email, display_name, password_salt, password_hash, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    display_name = EXCLUDED.display_name,
                    password_salt = EXCLUDED.password_salt,
                    password_hash = EXCLUDED.password_hash,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    row["id"],
                    row["email"],
                    row["display_name"],
                    row["password_salt"],
                    row["password_hash"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        for row in user_settings:
            pg_connection.execute(
                """
                INSERT INTO user_settings(
                    user_id, mode, provider, model, base_url, api_key_enc, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    provider = EXCLUDED.provider,
                    model = EXCLUDED.model,
                    base_url = EXCLUDED.base_url,
                    api_key_enc = EXCLUDED.api_key_enc,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    row["user_id"],
                    row["mode"],
                    row["provider"],
                    row["model"],
                    row["base_url"],
                    row["api_key_enc"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        for row in sessions:
            pg_connection.execute(
                """
                INSERT INTO sessions(id, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    title = EXCLUDED.title,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    row["id"],
                    row["user_id"],
                    row["title"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        for row in tasks:
            pg_connection.execute(
                """
                INSERT INTO tasks(
                    id, user_id, session_id, prompt, status, trace_json, usage_json, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    session_id = EXCLUDED.session_id,
                    prompt = EXCLUDED.prompt,
                    status = EXCLUDED.status,
                    trace_json = EXCLUDED.trace_json,
                    usage_json = EXCLUDED.usage_json,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    row["id"],
                    row["user_id"],
                    row["session_id"],
                    row["prompt"],
                    row["status"],
                    row["trace_json"],
                    row["usage_json"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        for row in messages:
            pg_connection.execute(
                """
                INSERT INTO messages(
                    id, user_id, session_id, task_id, role, content, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    session_id = EXCLUDED.session_id,
                    task_id = EXCLUDED.task_id,
                    role = EXCLUDED.role,
                    content = EXCLUDED.content
                """,
                (
                    row["id"],
                    row["user_id"],
                    row["session_id"],
                    row["task_id"],
                    row["role"],
                    row["content"],
                    row["created_at"],
                ),
            )

        pg_connection.commit()

    print("SQLite -> PostgreSQL migration completed.")
    print(f"users={len(users)}")
    print(f"user_settings={len(user_settings)}")
    print(f"sessions={len(sessions)}")
    print(f"tasks={len(tasks)}")
    print(f"messages={len(messages)}")


if __name__ == "__main__":
    main()
