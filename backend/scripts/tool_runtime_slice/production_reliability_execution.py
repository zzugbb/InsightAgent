from __future__ import annotations

from .context import SimpleNamespace, chat_execution_module, task_routes_module


class ProductionReliabilityExecutionMixin:
    def test_production_reliability_complete_task_does_not_overwrite_terminal_tasks(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["complete_task"],
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

            updated_count = persistence_module.complete_task(
                "task-complete-terminal-race",
                [],
                "user-complete-terminal-race",
                status="completed",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertEqual(updated_count, 0)
        self.assertIn("LOWER(status) IN", rendered_query)
        self.assertNotIn("cancelled", rendered_params)
        self.assertNotIn("timed_out", rendered_params)
        self.assertEqual(
            rendered_params[-2:],
            ("task-complete-terminal-race", "user-complete-terminal-race"),
        )

    def test_production_reliability_stream_does_not_emit_done_when_complete_lost_race(
        self,
    ) -> None:
        complete_calls: list[dict[str, object]] = []
        memory_calls: list[dict[str, object]] = []
        released_slots: list[str] = []

        class FakeProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                yield "final answer after cancel race"

        class FakeSlot:
            def release(self) -> None:
                released_slots.append("released")

        original_get_settings = chat_execution_module.get_settings
        original_get_stored_settings = chat_execution_module.get_stored_settings
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_mark_running = chat_execution_module.mark_task_running_started
        original_get_task = chat_execution_module.get_task
        original_update_trace = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_append_memory = chat_execution_module.try_append_task_memory
        original_safe_audit = chat_execution_module.safe_record_audit_event

        complete_attempted = {"value": False}

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
                usage_prompt_token_price_per_1k=0.0,
                usage_completion_token_price_per_1k=0.0,
            )
            chat_execution_module.get_stored_settings = lambda _user_id: None
            chat_execution_module.get_llm_provider = lambda _user_id: FakeProvider()
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda **_kwargs: SimpleNamespace()
            )
            chat_execution_module.build_tool_plan_artifacts = (
                lambda *args, **kwargs: SimpleNamespace(
                    tool_plan=[],
                    planning_prompt=None,
                    provider_usage=None,
                    planning_provider_attempted=False,
                    planning_provider_used=False,
                    allowed_tool_names=(),
                    allowed_tool_labels=(),
                )
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                lambda **_kwargs: {
                    "provider": SimpleNamespace(),
                    "provider_source_name": "default",
                }
            )
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: FakeSlot()
            )
            chat_execution_module.release_task_execution_slot = lambda _task_id: None
            chat_execution_module.mark_task_running_started = (
                lambda *args, **kwargs: 1
            )
            chat_execution_module.get_task = (
                lambda *args, **kwargs: {
                    "id": "task-complete-terminal-race",
                    "session_id": "session-complete-terminal-race",
                    "status": "cancelled" if complete_attempted["value"] else "running",
                }
            )
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None

            def fake_complete_task(**kwargs):
                complete_attempted["value"] = True
                complete_calls.append(dict(kwargs))
                return 0

            chat_execution_module.complete_task = fake_complete_task
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = (
                lambda *args, **kwargs: memory_calls.append(dict(kwargs))
            )
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-complete-terminal-race",
                    session_id="session-complete-terminal-race",
                    user_id="user-complete-terminal-race",
                    prompt="do not emit done after cancel race",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.release_task_execution_slot = original_release_slot
            chat_execution_module.mark_task_running_started = original_mark_running
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_trace
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_append_memory
            chat_execution_module.safe_record_audit_event = original_safe_audit

        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["completed", "cancelled"],
        )
        self.assertEqual(memory_calls, [])
        self.assertEqual(released_slots, ["released"])
        self.assertFalse(any(event.startswith("event: done\n") for event in events))
        self.assertTrue(any(event.startswith("event: cancelled\n") for event in events))

    def test_production_reliability_mark_cancel_requested_does_not_overwrite_terminal_tasks(
        self,
    ) -> None:
        persistence_module = __import__(
            "app.services.chat_persistence_service",
            fromlist=["mark_task_cancel_requested"],
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

            updated_count = persistence_module.mark_task_cancel_requested(
                task_id="task-cancel-terminal-race",
                user_id="user-cancel-terminal-race",
            )
        finally:
            persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertEqual(updated_count, 0)
        self.assertIn("LOWER(status) IN", rendered_query)
        self.assertNotIn("completed", rendered_params)
        self.assertNotIn("failed", rendered_params)
        self.assertEqual(
            rendered_params[-2:],
            ("task-cancel-terminal-race", "user-cancel-terminal-race"),
        )

    def test_production_reliability_cancel_task_does_not_overwrite_terminal_race(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_mark_cancel = getattr(
            task_routes_module,
            "mark_task_cancel_requested",
            None,
        )
        original_update_status = task_routes_module.update_task_status
        original_forget_waiting_task = task_routes_module.forget_waiting_task
        original_safe_audit = task_routes_module.safe_record_audit_event

        status_updates: list[dict[str, object]] = []
        forgotten: list[str] = []
        audits: list[dict[str, object]] = []
        task_reads = [
            {
                "id": "task-cancel-terminal-race",
                "session_id": "session-cancel-terminal-race",
                "status": "running",
            },
            {
                "id": "task-cancel-terminal-race",
                "session_id": "session-cancel-terminal-race",
                "status": "completed",
            },
        ]

        try:
            task_routes_module.get_task = (
                lambda _task_id, _user_id: dict(task_reads.pop(0))
            )
            task_routes_module.mark_task_cancel_requested = (  # type: ignore[attr-defined]
                lambda *, task_id, user_id: 0
            )
            task_routes_module.update_task_status = (
                lambda **kwargs: status_updates.append(dict(kwargs))
            )
            task_routes_module.forget_waiting_task = forgotten.append  # type: ignore[assignment]
            task_routes_module.safe_record_audit_event = (
                lambda **kwargs: audits.append(dict(kwargs))
            )

            payload = task_routes_module.cancel_task(
                "task-cancel-terminal-race",
                current_user={"id": "user-cancel-terminal-race"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_mark_cancel is None:
                if hasattr(task_routes_module, "mark_task_cancel_requested"):
                    delattr(task_routes_module, "mark_task_cancel_requested")
            else:
                task_routes_module.mark_task_cancel_requested = original_mark_cancel  # type: ignore[attr-defined]
            task_routes_module.update_task_status = original_update_status
            task_routes_module.forget_waiting_task = original_forget_waiting_task
            task_routes_module.safe_record_audit_event = original_safe_audit

        self.assertEqual(status_updates, [])
        self.assertEqual(forgotten, [])
        self.assertEqual(payload.previous_status, "running")
        self.assertEqual(payload.status, "completed")
        self.assertEqual(payload.status_normalized, "completed")
        self.assertTrue(payload.already_terminal)
        self.assertEqual(audits[0]["detail"]["status"], "completed")

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
