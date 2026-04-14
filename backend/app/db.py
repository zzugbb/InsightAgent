import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


def get_sqlite_path() -> Path:
    settings = get_settings()
    return Path(settings.sqlite_path)


def ensure_sqlite_ready() -> Path:
    sqlite_path = get_sqlite_path()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_path.touch(exist_ok=True)
    return sqlite_path


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    sqlite_path = ensure_sqlite_ready()
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> Path:
    sqlite_path = ensure_sqlite_ready()
    with get_db_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO app_meta(key, value)
            VALUES ('schema_version', 'w1-bootstrap')
            ON CONFLICT(key) DO NOTHING
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                base_url TEXT,
                api_key TEXT
            )
            """
        )
        connection.execute(
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
        connection.execute(
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
        connection.execute(
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                session_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                trace_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
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
        _ensure_tasks_usage_json_column(connection)
        _ensure_sessions_user_id_column(connection)
        _ensure_tasks_user_id_column(connection)
        _ensure_messages_user_id_column(connection)
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_session_id
            ON tasks(session_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
            ON sessions(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id
            ON tasks(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user_id
            ON messages(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_task_id
            ON messages(task_id)
            """
        )
        connection.commit()
    return sqlite_path


def _ensure_tasks_usage_json_column(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(tasks)").fetchall()
    names = {str(r["name"]) for r in rows}
    if "usage_json" not in names:
        connection.execute("ALTER TABLE tasks ADD COLUMN usage_json TEXT")


def _ensure_sessions_user_id_column(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(sessions)").fetchall()
    names = {str(r["name"]) for r in rows}
    if "user_id" not in names:
        connection.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")


def _ensure_tasks_user_id_column(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(tasks)").fetchall()
    names = {str(r["name"]) for r in rows}
    if "user_id" not in names:
        connection.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT")


def _ensure_messages_user_id_column(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(messages)").fetchall()
    names = {str(r["name"]) for r in rows}
    if "user_id" not in names:
        connection.execute("ALTER TABLE messages ADD COLUMN user_id TEXT")
