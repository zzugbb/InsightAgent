from __future__ import annotations

from .context import SimpleNamespace, chat_execution_module


class ProductionReliabilityExecutionMixin:
    def test_production_reliability_mark_queued_does_not_resurrect_terminal_tasks(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["mark_task_queued_waiting"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        captured: dict[str, object] = {}

        class FakeCursor:
            rowcount = 0

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

            updated_count = persistence_module.mark_task_queued_waiting(
                task_id="task-queued-terminal-race",
                user_id="user-queued-terminal-race",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertEqual(updated_count, 0)
        self.assertIn("LOWER(status) IN", rendered_query)
        self.assertNotIn("completed", rendered_params)
        self.assertEqual(
            rendered_params[-2:],
            ("task-queued-terminal-race", "user-queued-terminal-race"),
        )

    def test_production_reliability_mark_running_does_not_resurrect_terminal_tasks(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["mark_task_running_started"],
        )
        original_get_db_connection = persistence_module.get_db_connection
        captured: dict[str, object] = {}

        class FakeCursor:
            rowcount = 0

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

            updated_count = persistence_module.mark_task_running_started(
                task_id="task-terminal-race",
                user_id="user-terminal-race",
                execution_owner_id="instance-a",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertEqual(updated_count, 0)
        self.assertIn("LOWER(status) IN", rendered_query)
        self.assertNotIn("cancelled", rendered_params)
        self.assertEqual(rendered_params[-2:], ("task-terminal-race", "user-terminal-race"))

    def test_production_reliability_stream_does_not_execute_when_running_start_lost_race(
        self,
    ) -> None:
        provider_calls: list[str] = []
        completion_calls: list[dict[str, object]] = []
        released_slots: list[str] = []

        class FakeSlot:
            def release(self) -> None:
                released_slots.append("released")

        original_get_settings = chat_execution_module.get_settings
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_mark_running = chat_execution_module.mark_task_running_started
        original_get_task = chat_execution_module.get_task
        original_get_stored_settings = chat_execution_module.get_stored_settings
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-a",
                task_execution_heartbeat_interval_sec=0.0,
            )
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: FakeSlot()
            )
            chat_execution_module.release_task_execution_slot = lambda task_id: None
            chat_execution_module.mark_task_running_started = (
                lambda *args, **kwargs: 0
            )
            chat_execution_module.get_task = lambda *args, **kwargs: {
                "id": "task-terminal-race",
                "status": "completed",
                "session_id": "session-terminal-race",
            }
            chat_execution_module.get_stored_settings = (
                lambda user_id: provider_calls.append("settings") or None
            )
            chat_execution_module.get_llm_provider = (
                lambda user_id: provider_calls.append("provider") or None
            )
            chat_execution_module.complete_task = (
                lambda **kwargs: completion_calls.append(dict(kwargs))
            )
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-terminal-race",
                    session_id="session-terminal-race",
                    user_id="user-terminal-race",
                    prompt="do not resurrect terminal task",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.release_task_execution_slot = original_release_slot
            chat_execution_module.mark_task_running_started = original_mark_running
            chat_execution_module.get_task = original_get_task
            chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.safe_record_audit_event = original_safe_audit

        self.assertEqual(provider_calls, [])
        self.assertEqual(completion_calls, [])
        self.assertEqual(released_slots, ["released"])
        self.assertTrue(any(event.startswith("event: error\n") for event in events))

    def test_production_reliability_stream_does_not_requeue_when_wait_mark_lost_race(
        self,
    ) -> None:
        queued_updates: list[dict[str, object]] = []
        completion_calls: list[dict[str, object]] = []

        original_get_settings = chat_execution_module.get_settings
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_mark_queued = getattr(chat_execution_module, "mark_task_queued_waiting", None)
        original_update_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event
        original_sleep = chat_execution_module.sleep

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-a",
                task_execution_heartbeat_interval_sec=0.0,
            )
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: None
            )
            chat_execution_module.mark_task_queued_waiting = (  # type: ignore[attr-defined]
                lambda *, task_id, user_id: 0
            )
            chat_execution_module.update_task_status = (
                lambda **kwargs: queued_updates.append(dict(kwargs))
            )
            chat_execution_module.get_task = lambda *args, **kwargs: {
                "id": "task-queued-terminal-race",
                "status": "completed",
                "session_id": "session-queued-terminal-race",
            }
            chat_execution_module.complete_task = (
                lambda **kwargs: completion_calls.append(dict(kwargs))
            )
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None
            chat_execution_module.sleep = (
                lambda _seconds: (_ for _ in ()).throw(
                    AssertionError("stream kept waiting after queued mark race")
                )
            )

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-queued-terminal-race",
                    session_id="session-queued-terminal-race",
                    user_id="user-queued-terminal-race",
                    prompt="do not requeue terminal task",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            if original_mark_queued is None:
                if hasattr(chat_execution_module, "mark_task_queued_waiting"):
                    delattr(chat_execution_module, "mark_task_queued_waiting")
            else:
                chat_execution_module.mark_task_queued_waiting = original_mark_queued  # type: ignore[attr-defined]
            chat_execution_module.update_task_status = original_update_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.safe_record_audit_event = original_safe_audit
            chat_execution_module.sleep = original_sleep

        self.assertEqual(queued_updates, [])
        self.assertEqual(completion_calls, [])
        self.assertTrue(any(event.startswith("event: error\n") for event in events))
