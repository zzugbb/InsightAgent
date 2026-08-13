from __future__ import annotations

import asyncio
import json

from .context import SimpleNamespace, task_routes_module


class ProductionReliabilityQueueMixin:
    def test_production_reliability_task_queue_reports_active_execution(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "is_task_execution_active",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            self.assertFalse(task_queue_module.is_task_execution_active("task-active"))
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertTrue(task_queue_module.is_task_execution_active("task-active"))
            active_slot.release()
            self.assertFalse(task_queue_module.is_task_execution_active("task-active"))
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_production_reliability_pending_active_stream_uses_reconnect(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_stream_execution = task_routes_module.stream_task_execution
        original_stream_reconnect = task_routes_module.stream_running_task_reconnect
        original_is_active = getattr(task_routes_module, "is_task_execution_active", None)
        captured: dict[str, object] = {}

        def fake_stream_task_execution(**kwargs):
            captured["execution"] = dict(kwargs)
            return iter(())

        def fake_stream_running_task_reconnect(task_id: str, user_id: str, *, after_seq: int = 0):
            captured["reconnect"] = {
                "task_id": task_id,
                "user_id": user_id,
                "after_seq": after_seq,
            }
            return iter(())

        try:
            task_routes_module.get_task = lambda task_id, user_id: {
                "id": task_id,
                "user_id": user_id,
                "session_id": "session-active-race",
                "prompt": "active race prompt",
                "status": "pending",
            }
            task_routes_module.stream_task_execution = fake_stream_task_execution
            task_routes_module.stream_running_task_reconnect = (
                fake_stream_running_task_reconnect
            )
            task_routes_module.is_task_execution_active = lambda task_id: True  # type: ignore[attr-defined]

            response = task_routes_module.stream_task_detail(
                "task-active-race",
                request=SimpleNamespace(headers={"Last-Event-ID": "3"}),
                after_seq=5,
                current_user={"id": "user-active-race"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.stream_task_execution = original_stream_execution
            task_routes_module.stream_running_task_reconnect = original_stream_reconnect
            if original_is_active is None:
                if hasattr(task_routes_module, "is_task_execution_active"):
                    delattr(task_routes_module, "is_task_execution_active")
            else:
                task_routes_module.is_task_execution_active = original_is_active  # type: ignore[attr-defined]

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertNotIn("execution", captured)
        self.assertEqual(
            captured.get("reconnect"),
            {
                "task_id": "task-active-race",
                "user_id": "user-active-race",
                "after_seq": 5,
            },
        )

    def test_production_reliability_reconnect_stream_terminates_on_cancelled(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_task = task_routes_module.get_task
        original_sleep = task_routes_module.asyncio.sleep
        original_delta_snapshot_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        task_reads = [
            {
                "id": "task-reconnect-cancelled",
                "session_id": "session-reconnect-cancelled",
                "status": "running",
            },
            {
                "id": "task-reconnect-cancelled",
                "session_id": "session-reconnect-cancelled",
                "status": "cancelled",
            },
        ]

        async def fail_sleep(_delay: float) -> None:
            raise AssertionError(
                "reconnect stream must terminate instead of sleeping after cancelled"
            )

        async def collect_events() -> list[str]:
            events: list[str] = []
            async for event in task_routes_module.stream_running_task_reconnect(
                "task-reconnect-cancelled",
                "user-reconnect-cancelled",
            ):
                events.append(event)
            return events

        try:
            task_routes_module.get_settings = lambda: SimpleNamespace(
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.5,
                stream_reconnect_heartbeat_interval_sec=60.0,
            )
            task_routes_module.get_task = lambda *_args, **_kwargs: task_reads.pop(0)
            task_routes_module.asyncio.sleep = fail_sleep
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: ([], after_seq, False, 0, None)
            )

            events = asyncio.run(collect_events())
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_task = original_get_task
            task_routes_module.asyncio.sleep = original_sleep
            if original_delta_snapshot_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_helper  # type: ignore[attr-defined]

        event_names = [
            event.split("\n", 1)[0].replace("event: ", "")
            for event in events
            if event.startswith("event: ")
        ]
        error_payloads = [
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: error\n")
        ]
        self.assertEqual(event_names, ["start", "state", "cancelled", "error"])
        self.assertEqual(error_payloads[-1]["code"], "task_cancelled")
        self.assertTrue(error_payloads[-1]["resumed"])

    def test_production_reliability_forget_waiting_tasks_for_session_preserves_active_slot(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "forget_waiting_tasks_for_scope",
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active",
                user_id="user-a",
                session_id="session-a",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-session-a",
                    user_id="user-a",
                    session_id="session-a",
                    max_concurrent=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-session-b",
                    user_id="user-a",
                    session_id="session-b",
                    max_concurrent=1,
                )
            )

            removed_count = task_queue_module.forget_waiting_tasks_for_scope(
                session_id="session-a"
            )

            self.assertEqual(removed_count, 1)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-wait-session-b",
                    user_id="user-a",
                    session_id="session-b",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": 1,
                    "active_count_for_user": 1,
                    "waiting_count_for_user": 1,
                    "active_count_for_session": 0,
                    "waiting_count_for_session": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_production_reliability_forget_waiting_tasks_for_user_preserves_other_waiters(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "forget_waiting_tasks_for_scope",
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-user-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-user-a-1",
                    user_id="user-a",
                    session_id="session-a-1",
                    max_concurrent=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-user-b",
                    user_id="user-b",
                    session_id="session-b",
                    max_concurrent=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-user-a-2",
                    user_id="user-a",
                    session_id="session-a-2",
                    max_concurrent=1,
                )
            )

            removed_count = task_queue_module.forget_waiting_tasks_for_scope(
                user_id="user-a"
            )

            self.assertEqual(removed_count, 2)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-wait-user-b",
                    user_id="user-b",
                    session_id="session-b",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": 1,
                    "active_count_for_user": 0,
                    "waiting_count_for_user": 1,
                    "active_count_for_session": 0,
                    "waiting_count_for_session": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_production_reliability_delete_session_forgets_session_waiters(
        self,
    ) -> None:
        sessions_routes_module = __import__(
            "app.api.routes.sessions",
            fromlist=["delete_session_route"],
        )
        original_get_session = sessions_routes_module.get_session
        original_delete_session = sessions_routes_module.delete_session
        original_cleanup_memory = sessions_routes_module.cleanup_session_memory_collection
        original_forget_scope = getattr(
            sessions_routes_module,
            "forget_waiting_tasks_for_scope",
            None,
        )
        forgotten_scopes: list[dict[str, str | None]] = []
        try:
            sessions_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Reliability Session",
                }
            )
            sessions_routes_module.delete_session = (
                lambda session_id, user_id: session_id == "session-delete"
                and user_id == "user-delete"
            )
            sessions_routes_module.cleanup_session_memory_collection = (
                lambda _session_id: None
            )
            sessions_routes_module.forget_waiting_tasks_for_scope = (  # type: ignore[attr-defined]
                lambda **kwargs: forgotten_scopes.append(dict(kwargs)) or 2
            )

            response = sessions_routes_module.delete_session_route(
                "session-delete",
                current_user={"id": "user-delete"},
            )
        finally:
            sessions_routes_module.get_session = original_get_session
            sessions_routes_module.delete_session = original_delete_session
            sessions_routes_module.cleanup_session_memory_collection = (
                original_cleanup_memory
            )
            if original_forget_scope is None:
                if hasattr(sessions_routes_module, "forget_waiting_tasks_for_scope"):
                    delattr(sessions_routes_module, "forget_waiting_tasks_for_scope")
            else:
                sessions_routes_module.forget_waiting_tasks_for_scope = (  # type: ignore[attr-defined]
                    original_forget_scope
                )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            forgotten_scopes,
            [{"user_id": "user-delete", "session_id": "session-delete"}],
        )
