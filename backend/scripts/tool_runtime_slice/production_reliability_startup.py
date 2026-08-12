from __future__ import annotations


class ProductionReliabilityStartupMixin:
    def test_production_reliability_config_exposes_task_execution_owner_id(
        self,
    ) -> None:
        config_module = __import__("app.config", fromlist=["Settings"])

        field = config_module.Settings.model_fields["task_execution_owner_id"]

        self.assertEqual(field.alias, "TASK_EXECUTION_OWNER_ID")

    def test_production_reliability_database_ensures_execution_owner_columns(
        self,
    ) -> None:
        db_module = __import__("app.db", fromlist=["initialize_postgres_database"])
        original_get_db_connection = db_module.get_db_connection
        original_ensure_column = db_module._ensure_postgres_column
        original_ensure_indexes = db_module._ensure_common_indexes
        calls: list[tuple[str, str, str]] = []

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return None

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            db_module.get_db_connection = lambda: FakeContextManager()
            db_module._ensure_postgres_column = (
                lambda connection, table, column, definition: calls.append(
                    (table, column, definition)
                )
            )
            db_module._ensure_common_indexes = lambda connection: None

            db_module.initialize_postgres_database()
        finally:
            db_module.get_db_connection = original_get_db_connection
            db_module._ensure_postgres_column = original_ensure_column
            db_module._ensure_common_indexes = original_ensure_indexes

        self.assertIn(("tasks", "execution_owner_id", "TEXT"), calls)
        self.assertIn(("tasks", "execution_heartbeat_at", "TEXT"), calls)

    def test_production_reliability_migration_schema_includes_execution_owner_columns(
        self,
    ) -> None:
        migration_module = __import__(
            "scripts.migrate_sqlite_to_postgres",
            fromlist=["_ensure_postgres_schema"],
        )
        queries: list[str] = []

        class FakePostgresConnection:
            def execute(self, query: str, _params=()):
                queries.append(query)
                return None

        migration_module._ensure_postgres_schema(FakePostgresConnection())

        task_schema = next(
            query for query in queries if "CREATE TABLE IF NOT EXISTS tasks" in query
        )
        self.assertIn("execution_owner_id TEXT", task_schema)
        self.assertIn("execution_heartbeat_at TEXT", task_schema)

    def test_production_reliability_marks_task_running_with_execution_owner(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["mark_task_running_started"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = " ".join(query.split())
                captured["params"] = tuple(params)
                return None

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            persistence_module.get_db_connection = lambda: FakeContextManager()

            persistence_module.mark_task_running_started(
                task_id="task-owner",
                user_id="user-owner",
                execution_owner_id="instance-a",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("status = ?", rendered_query)
        self.assertIn("execution_owner_id = ?", rendered_query)
        self.assertIn("execution_heartbeat_at = ?", rendered_query)
        self.assertEqual(rendered_params[0], "running")
        self.assertEqual(rendered_params[2], "instance-a")
        self.assertEqual(rendered_params[-2:], ("task-owner", "user-owner"))

    def test_production_reliability_complete_task_clears_execution_owner(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["complete_task"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = " ".join(query.split())
                captured["params"] = tuple(params)
                return None

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            persistence_module.get_db_connection = lambda: FakeContextManager()

            persistence_module.complete_task(
                "task-complete-owner",
                [],
                "user-owner",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("execution_owner_id = NULL", rendered_query)
        self.assertIn("execution_heartbeat_at = NULL", rendered_query)
        self.assertEqual(rendered_params[-2:], ("task-complete-owner", "user-owner"))

    def test_production_reliability_marks_orphaned_running_tasks_failed_on_startup(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["recover_orphaned_running_tasks_on_startup"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        executed: list[tuple[str, tuple[object, ...]]] = []

        class FakeCursor:
            rowcount = 3

        class FakeConnection:
            def execute(self, query: str, params=()):
                executed.append((" ".join(query.split()), tuple(params)))
                return FakeCursor()

            def commit(self) -> None:
                executed.append(("COMMIT", ()))

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            persistence_module.get_db_connection = lambda: FakeContextManager()

            recovered_count = persistence_module.recover_orphaned_running_tasks_on_startup(
                execution_owner_id="instance-a"
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(recovered_count, 3)
        self.assertEqual(executed[-1], ("COMMIT", ()))
        update_query, update_params = executed[0]
        self.assertIn("UPDATE tasks", update_query)
        self.assertIn("SET status = ?", update_query)
        self.assertIn("execution_owner_id = NULL", update_query)
        self.assertIn("execution_heartbeat_at = NULL", update_query)
        self.assertIn("WHERE LOWER(status) = ?", update_query)
        self.assertEqual(update_params[0], "failed")
        self.assertIn("execution_owner_id = ?", update_query)
        self.assertEqual(update_params[-2:], ("running", "instance-a"))

    def test_production_reliability_lifespan_recovers_running_tasks_after_db_init(
        self,
    ) -> None:
        asyncio_module = __import__("asyncio")
        main_module = __import__("app.main", fromlist=["lifespan"])
        calls: list[str] = []
        original_initialize_database = main_module.initialize_database
        original_recovery = getattr(
            main_module,
            "recover_orphaned_running_tasks_on_startup",
            None,
        )

        async def run_lifespan_once() -> None:
            async with main_module.lifespan(None):
                calls.append("inside")

        try:
            main_module.initialize_database = lambda: calls.append("init") or "db"
            main_module.recover_orphaned_running_tasks_on_startup = (  # type: ignore[attr-defined]
                lambda **_kwargs: calls.append("recover") or 2
            )

            asyncio_module.run(run_lifespan_once())
        finally:
            main_module.initialize_database = original_initialize_database
            if original_recovery is None:
                if hasattr(main_module, "recover_orphaned_running_tasks_on_startup"):
                    delattr(main_module, "recover_orphaned_running_tasks_on_startup")
            else:
                main_module.recover_orphaned_running_tasks_on_startup = (  # type: ignore[attr-defined]
                    original_recovery
                )

        self.assertEqual(calls, ["init", "recover", "inside"])
