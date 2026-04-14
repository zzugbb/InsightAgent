from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit

from app.config import get_settings


class CursorAdapter:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return int(getattr(self._cursor, "rowcount", 0))

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return self._cursor.fetchall()


class DbConnectionAdapter:
    def __init__(self, connection: Any):
        self._connection = connection

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> CursorAdapter:
        adapted_query = _adapt_qmark_to_format(query)
        cursor = self._connection.execute(adapted_query, params)
        return CursorAdapter(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def _adapt_qmark_to_format(query: str) -> str:
    # 项目内 SQL 统一使用 qmark(?)，在 PostgreSQL 执行前转换为 psycopg 的 %s。
    return query.replace("?", "%s")


def get_database_locator() -> str:
    settings = get_settings()
    return _safe_database_locator(settings.database_url.strip())


def _safe_database_locator(database_url: str) -> str:
    if not database_url:
        return "<missing INSIGHT_AGENT_DATABASE_URL>"
    try:
        parsed = urlsplit(database_url)
    except Exception:  # noqa: BLE001
        return "<configured postgres url>"
    if parsed.scheme not in {"postgres", "postgresql"}:
        return "<configured database url>"

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password is not None:
            auth = f"{auth}:***"
    elif parsed.password is not None:
        auth = "***"

    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    if auth:
        host = f"{auth}@{host}"

    return urlunsplit(
        (
            parsed.scheme,
            host,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


@contextmanager
def get_db_connection() -> Iterator[DbConnectionAdapter]:
    settings = get_settings()
    database_url = settings.database_url.strip()
    if not database_url:
        raise RuntimeError("INSIGHT_AGENT_DATABASE_URL is required")
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "psycopg is required. Please install dependencies from requirements.txt."
        ) from exc

    raw_connection = psycopg.connect(database_url, row_factory=dict_row)
    connection = DbConnectionAdapter(raw_connection)
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> str:
    initialize_postgres_database()
    return get_database_locator()


def initialize_postgres_database() -> None:
    with get_db_connection() as connection:
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
                id INTEGER PRIMARY KEY,
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
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL UNIQUE,
                user_agent TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used_at TEXT,
                revoked_at TEXT,
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
                usage_json TEXT,
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
        _ensure_postgres_column(connection, "tasks", "usage_json", "TEXT")
        _ensure_postgres_column(connection, "sessions", "user_id", "TEXT")
        _ensure_postgres_column(connection, "tasks", "user_id", "TEXT")
        _ensure_postgres_column(connection, "messages", "user_id", "TEXT")
        _ensure_common_indexes(connection)
        connection.commit()


def _ensure_common_indexes(connection: DbConnectionAdapter) -> None:
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
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id
        ON auth_sessions(user_id)
        """
    )


def _ensure_postgres_column(
    connection: DbConnectionAdapter,
    table_name: str,
    column_name: str,
    column_type_sql: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ?
          AND column_name = ?
        LIMIT 1
        """,
        (table_name, column_name),
    ).fetchone()
    if row is not None:
        return
    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}"
    )
