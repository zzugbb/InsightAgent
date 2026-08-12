from __future__ import annotations


class ProductionReliabilityStartupMixin:
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

            recovered_count = (
                persistence_module.recover_orphaned_running_tasks_on_startup()
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(recovered_count, 3)
        self.assertEqual(executed[-1], ("COMMIT", ()))
        update_query, update_params = executed[0]
        self.assertIn("UPDATE tasks", update_query)
        self.assertIn("SET status = ?", update_query)
        self.assertIn("WHERE LOWER(status) = ?", update_query)
        self.assertEqual(update_params[0], "failed")
        self.assertEqual(update_params[-1], "running")

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
                lambda: calls.append("recover") or 2
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
