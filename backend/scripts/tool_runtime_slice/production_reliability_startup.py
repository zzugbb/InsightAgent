from __future__ import annotations

from .context import (
    SimpleNamespace,
    StaticToolRegistryProvider,
    StoredSettings,
    chat_execution_module,
)


class ProductionReliabilityStartupMixin:
    def test_production_reliability_config_exposes_task_execution_owner_id(
        self,
    ) -> None:
        config_module = __import__("app.config", fromlist=["Settings"])

        field = config_module.Settings.model_fields["task_execution_owner_id"]

        self.assertEqual(field.alias, "TASK_EXECUTION_OWNER_ID")
        self.assertEqual(
            config_module.Settings.model_fields["task_execution_stale_after_sec"].alias,
            "TASK_EXECUTION_STALE_AFTER_SEC",
        )
        self.assertEqual(
            config_module.Settings.model_fields[
                "task_execution_heartbeat_interval_sec"
            ].alias,
            "TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC",
        )

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

    def test_production_reliability_touches_running_task_heartbeat_for_owner(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["touch_task_execution_heartbeat"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        captured: dict[str, object] = {}

        class FakeCursor:
            rowcount = 1

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = " ".join(query.split())
                captured["params"] = tuple(params)
                return FakeCursor()

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            persistence_module.get_db_connection = lambda: FakeContextManager()

            updated_count = persistence_module.touch_task_execution_heartbeat(
                task_id="task-heartbeat",
                user_id="user-heartbeat",
                execution_owner_id="instance-a",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertEqual(updated_count, 1)
        self.assertIn("execution_heartbeat_at = ?", rendered_query)
        self.assertIn("LOWER(status) = ?", rendered_query)
        self.assertIn("execution_owner_id = ?", rendered_query)
        self.assertEqual(rendered_params[-4:], ("task-heartbeat", "user-heartbeat", "running", "instance-a"))

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

    def test_production_reliability_startup_recovers_stale_other_owner_tasks(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["recover_orphaned_running_tasks_on_startup"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        original_now_iso = persistence_module._now_iso
        executed: list[tuple[str, tuple[object, ...]]] = []

        class FakeCursor:
            rowcount = 2

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
            persistence_module._now_iso = lambda: "2026-08-12T12:00:00"

            recovered_count = persistence_module.recover_orphaned_running_tasks_on_startup(
                execution_owner_id="instance-a",
                execution_stale_after_sec=30,
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection
            persistence_module._now_iso = original_now_iso

        self.assertEqual(recovered_count, 2)
        update_query, update_params = executed[0]
        self.assertIn("execution_heartbeat_at < ?", update_query)
        self.assertIn("execution_heartbeat_at IS NULL", update_query)
        self.assertIn("2026-08-12T11:59:30", update_params)

    def test_production_reliability_startup_omits_stale_clause_when_disabled(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["recover_orphaned_running_tasks_on_startup"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        executed: list[tuple[str, tuple[object, ...]]] = []

        class FakeCursor:
            rowcount = 1

        class FakeConnection:
            def execute(self, query: str, params=()):
                executed.append((" ".join(query.split()), tuple(params)))
                return FakeCursor()

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return None

        try:
            persistence_module.get_db_connection = lambda: FakeContextManager()

            persistence_module.recover_orphaned_running_tasks_on_startup(
                execution_owner_id="instance-a",
                execution_stale_after_sec=0,
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        update_query, _update_params = executed[0]
        self.assertNotIn("execution_heartbeat_at < ?", update_query)

    def test_production_reliability_stream_refreshes_execution_heartbeat(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="default",
            tool_registry_provider_source="default",
        )
        heartbeat_updates: list[tuple[str, str, str]] = []

        class FakeProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                yield "a"
                yield "b"

            def get_last_usage(self):
                return None

        class FakeSlot:
            def release(self) -> None:
                return None

        original_get_settings = chat_execution_module.get_settings
        original_get_stored_settings = chat_execution_module.get_stored_settings
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_get_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_mark_running = chat_execution_module.mark_task_running_started
        original_touch_heartbeat = chat_execution_module.touch_task_execution_heartbeat
        original_update_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_trace = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_memory = chat_execution_module.try_append_task_memory
        original_safe_audit = chat_execution_module.safe_record_audit_event
        original_monotonic = chat_execution_module.monotonic

        def fake_build_tool_plan_artifacts(*args, **kwargs):
            del args, kwargs
            return SimpleNamespace(
                tool_plan=[],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=(),
                allowed_tool_labels=(),
            )

        monotonic_values = iter(index * 0.3 for index in range(40))

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-a",
                task_execution_heartbeat_interval_sec=0.5,
            )
            chat_execution_module.get_stored_settings = lambda user_id: runtime_settings
            chat_execution_module.get_llm_provider = lambda user_id: FakeProvider()
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: FakeSlot()
            )
            chat_execution_module.release_task_execution_slot = lambda task_id: None
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda *, settings=None: StaticToolRegistryProvider({})
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                lambda **_kwargs: {
                    "provider": StaticToolRegistryProvider({}),
                    "provider_source_name": "default",
                }
            )
            chat_execution_module.mark_task_running_started = (
                lambda *args, **kwargs: 1
            )
            chat_execution_module.touch_task_execution_heartbeat = (
                lambda *, task_id, user_id, execution_owner_id: heartbeat_updates.append(
                    (task_id, user_id, execution_owner_id)
                )
                or 1
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = lambda *args, **kwargs: None
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None
            chat_execution_module.monotonic = lambda: next(monotonic_values)

            list(
                chat_execution_module.stream_task_execution(
                    task_id="task-heartbeat",
                    session_id="session-heartbeat",
                    user_id="user-heartbeat",
                    prompt="please stream with db heartbeat",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.release_task_execution_slot = original_release_slot
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.mark_task_running_started = original_mark_running
            chat_execution_module.touch_task_execution_heartbeat = (
                original_touch_heartbeat
            )
            chat_execution_module.update_task_status = original_update_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_trace
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_memory
            chat_execution_module.safe_record_audit_event = original_safe_audit
            chat_execution_module.monotonic = original_monotonic

        self.assertIn(
            ("task-heartbeat", "user-heartbeat", "instance-a"),
            heartbeat_updates,
        )

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
