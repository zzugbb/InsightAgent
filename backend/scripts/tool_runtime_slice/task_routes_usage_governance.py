from __future__ import annotations

from .context import *


class TaskRoutesUsageGovernanceMixin:
    def test_task_status_service_normalizes_queued_status(self) -> None:
        task_status_module = __import__(
            "app.services.task_status_service",
            fromlist=["normalize_task_status", "task_status_label", "task_status_rank"],
        )

        self.assertEqual(task_status_module.normalize_task_status("queued"), "queued")
        self.assertEqual(task_status_module.task_status_label("queued"), "Queued")
        self.assertLess(
            task_status_module.task_status_rank("queued"),
            task_status_module.task_status_rank("running"),
        )

    def test_stream_task_accepts_queued_tasks_as_executable(self) -> None:
        original_get_task = task_routes_module.get_task
        original_stream_task_execution = task_routes_module.stream_task_execution
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_task = lambda task_id, user_id: {
                "id": task_id,
                "user_id": user_id,
                "session_id": "session-queued",
                "prompt": "queued prompt",
                "status": "queued",
                "trace_json": None,
                "usage_json": None,
                "created_at": "2026-07-30T10:00:00",
                "updated_at": "2026-07-30T10:00:00",
            }

            def fake_stream_task_execution(**kwargs):
                captured.update(kwargs)
                return iter(())

            task_routes_module.stream_task_execution = fake_stream_task_execution

            response = task_routes_module.stream_task_detail(
                "task-queued",
                request=SimpleNamespace(headers={}),
                current_user={"id": "user-queued"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.stream_task_execution = original_stream_task_execution

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(
            captured,
            {
                "task_id": "task-queued",
                "session_id": "session-queued",
                "user_id": "user-queued",
                "prompt": "queued prompt",
                "persist_user_message": False,
            },
        )

    def test_create_task_entry_creates_queued_task(self) -> None:
        original_ensure_session = task_routes_module.ensure_session
        original_create_task = task_routes_module.create_task
        original_create_message = task_routes_module.create_message
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_get_summary = (
            task_routes_module.chat_persistence_service.get_task_create_response_summary
        )
        captured: dict[str, object] = {}
        try:
            task_routes_module.ensure_session = (
                lambda *, prompt, user_id, session_id=None: "session-queue-create"
            )

            def fake_create_task(**kwargs):
                captured.update(kwargs)
                return "task-queue-create"

            task_routes_module.create_task = fake_create_task
            task_routes_module.create_message = lambda **_kwargs: "message-queue-create"
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.chat_persistence_service.get_task_create_response_summary = (
                lambda **kwargs: {
                    "task_id": kwargs["task_id"],
                    "session_id": kwargs["session_id"],
                    "status": kwargs["status"],
                    "status_normalized": "queued",
                    "status_label": "Queued",
                    "status_rank": 5,
                }
            )

            payload = task_routes_module.create_task_entry(
                task_routes_module.TaskCreateRequest(
                    user_input="queued create prompt",
                    session_id=None,
                ),
                current_user={"id": "user-queue-create"},
            )
        finally:
            task_routes_module.ensure_session = original_ensure_session
            task_routes_module.create_task = original_create_task
            task_routes_module.create_message = original_create_message
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            task_routes_module.chat_persistence_service.get_task_create_response_summary = (
                original_get_summary
            )

        self.assertEqual(captured["status"], "queued")
        self.assertEqual(payload.status, "queued")
        self.assertEqual(payload.status_normalized, "queued")
        self.assertEqual(payload.status_label, "Queued")

    def test_stream_task_execution_waits_in_queued_state_when_slot_is_busy(self) -> None:
        original_try_acquire = getattr(
            chat_execution_module,
            "try_acquire_task_execution_slot",
            None,
        )
        original_snapshot = getattr(
            chat_execution_module,
            "get_task_queue_snapshot",
            None,
        )
        original_sleep = getattr(chat_execution_module, "sleep", None)
        original_get_settings = chat_execution_module.get_settings
        original_get_task = chat_execution_module.get_task
        original_update_task_status = chat_execution_module.update_task_status
        status_updates: list[str] = []
        try:
            chat_execution_module.try_acquire_task_execution_slot = (  # type: ignore[attr-defined]
                lambda **_kwargs: None
            )
            chat_execution_module.get_task_queue_snapshot = (  # type: ignore[attr-defined]
                lambda **kwargs: {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": 1
                    if kwargs.get("task_id") == "task-queued-wait"
                    else None,
                }
            )
            chat_execution_module.sleep = lambda _seconds: None  # type: ignore[attr-defined]
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0,
                task_timeout_sec=30,
                task_queue_max_concurrent=1,
                task_queue_poll_interval_sec=0.01,
            )
            chat_execution_module.get_task = (
                lambda task_id, user_id: {
                    "id": task_id,
                    "user_id": user_id,
                    "status": "queued",
                }
            )
            chat_execution_module.update_task_status = (
                lambda *, task_id, status, user_id: status_updates.append(status)
            )

            event = next(
                chat_execution_module.stream_task_execution(
                    task_id="task-queued-wait",
                    session_id="session-queued-wait",
                    user_id="user-queued-wait",
                    prompt="wait for slot",
                    persist_user_message=False,
                )
            )
        finally:
            if original_try_acquire is None:
                delattr(chat_execution_module, "try_acquire_task_execution_slot")
            else:
                chat_execution_module.try_acquire_task_execution_slot = original_try_acquire  # type: ignore[attr-defined]
            if original_snapshot is None:
                delattr(chat_execution_module, "get_task_queue_snapshot")
            else:
                chat_execution_module.get_task_queue_snapshot = original_snapshot  # type: ignore[attr-defined]
            if original_sleep is None:
                if hasattr(chat_execution_module, "sleep"):
                    delattr(chat_execution_module, "sleep")
            else:
                chat_execution_module.sleep = original_sleep  # type: ignore[attr-defined]
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_status = original_update_task_status

        self.assertIn("event: state", event)
        self.assertIn('"phase": "queued"', event)
        self.assertIn('"active_count": 1', event)
        self.assertIn('"wait_position": 1', event)
        self.assertNotIn("active_task_ids", event)
        self.assertNotIn("running", status_updates)

    def test_task_queue_service_enforces_single_execution_slot(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "forget_waiting_task",
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            first_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-slot-1",
                max_concurrent=1,
            )
            self.assertIsNotNone(first_slot)
            second_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-slot-2",
                max_concurrent=1,
            )
            self.assertIsNone(second_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(max_concurrent=1),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": None,
                },
            )

            first_slot.release()
            third_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-slot-2",
                max_concurrent=1,
            )
            self.assertIsNotNone(third_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-slot-2",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 0,
                    "wait_position": 0,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_duplicate_active_slot_release_does_not_free_original(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            original_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active-duplicate",
                max_concurrent=1,
            )
            self.assertIsNotNone(original_slot)
            duplicate_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active-duplicate",
                max_concurrent=1,
            )
            self.assertIsNotNone(duplicate_slot)

            duplicate_slot.release()

            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-active-duplicate",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 0,
                    "wait_position": 0,
                },
            )

            original_slot.release()
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(max_concurrent=1),
                {
                    "active_count": 0,
                    "max_concurrent": 1,
                    "waiting_count": 0,
                    "wait_position": None,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_enforces_per_user_limit_without_blocking_other_users(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            first_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-user-a-1",
                user_id="user-a",
                session_id="session-a-1",
                max_concurrent=4,
                max_concurrent_per_user=1,
            )
            self.assertIsNotNone(first_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-user-a-2",
                    user_id="user-a",
                    session_id="session-a-2",
                    max_concurrent=4,
                    max_concurrent_per_user=1,
                )
            )
            other_user_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-user-b-1",
                user_id="user-b",
                session_id="session-b-1",
                max_concurrent=4,
                max_concurrent_per_user=1,
            )
            self.assertIsNotNone(other_user_slot)

            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=4,
                    task_id="task-user-a-2",
                ),
                {
                    "active_count": 2,
                    "max_concurrent": 4,
                    "waiting_count": 1,
                    "wait_position": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_enforces_per_session_limit_without_blocking_other_sessions(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            first_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-session-a-1",
                user_id="user-a",
                session_id="session-a",
                max_concurrent=4,
                max_concurrent_per_session=1,
            )
            self.assertIsNotNone(first_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-session-a-2",
                    user_id="user-a",
                    session_id="session-a",
                    max_concurrent=4,
                    max_concurrent_per_session=1,
                )
            )
            other_session_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-session-b-1",
                user_id="user-a",
                session_id="session-b",
                max_concurrent=4,
                max_concurrent_per_session=1,
            )
            self.assertIsNotNone(other_session_slot)

            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=4,
                    task_id="task-session-a-2",
                ),
                {
                    "active_count": 2,
                    "max_concurrent": 4,
                    "waiting_count": 1,
                    "wait_position": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_snapshot_exposes_wait_position_without_task_ids(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-1",
                    max_concurrent=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-2",
                    max_concurrent=1,
                )
            )

            snapshot = task_queue_module.get_task_queue_snapshot(
                max_concurrent=1,
                task_id="task-wait-2",
            )

            self.assertEqual(
                snapshot,
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 2,
                    "wait_position": 2,
                },
            )
            self.assertNotIn("active_task_ids", snapshot)
            self.assertNotIn("waiting_task_ids", snapshot)
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_forgets_cancelled_waiting_task(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "forget_waiting_task",
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-cancelled",
                    max_concurrent=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-wait-next",
                    max_concurrent=1,
                )
            )

            task_queue_module.forget_waiting_task("task-wait-cancelled")

            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-wait-next",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_preserves_waiting_fifo_when_slot_is_released(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-fifo-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-fifo-old",
                    user_id="user-old",
                    session_id="session-old",
                    max_concurrent=1,
                )
            )

            active_slot.release()

            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-fifo-new",
                    user_id="user-new",
                    session_id="session-new",
                    max_concurrent=1,
                )
            )
            old_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-fifo-old",
                user_id="user-old",
                session_id="session-old",
                max_concurrent=1,
            )
            self.assertIsNotNone(old_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=1,
                    task_id="task-fifo-new",
                ),
                {
                    "active_count": 1,
                    "max_concurrent": 1,
                    "waiting_count": 1,
                    "wait_position": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_allows_new_task_when_capacity_can_fit_older_waiters(self) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-fifo-capacity-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-fifo-capacity-old",
                    user_id="user-old",
                    session_id="session-old",
                    max_concurrent=1,
                )
            )

            new_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-fifo-capacity-new",
                user_id="user-new",
                session_id="session-new",
                max_concurrent=3,
            )
            self.assertIsNotNone(new_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=3,
                    task_id="task-fifo-capacity-old",
                ),
                {
                    "active_count": 2,
                    "max_concurrent": 3,
                    "waiting_count": 1,
                    "wait_position": 1,
                },
            )
            old_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-fifo-capacity-old",
                user_id="user-old",
                session_id="session-old",
                max_concurrent=3,
            )
            self.assertIsNotNone(old_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(max_concurrent=3),
                {
                    "active_count": 3,
                    "max_concurrent": 3,
                    "waiting_count": 0,
                    "wait_position": None,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_counts_only_mutually_eligible_older_waiters_for_capacity(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "get_task_queue_snapshot",
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-mutual-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
                max_concurrent_per_user=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-mutual-old-a",
                    user_id="user-old",
                    session_id="session-old-a",
                    max_concurrent=1,
                    max_concurrent_per_user=1,
                )
            )
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-mutual-old-b",
                    user_id="user-old",
                    session_id="session-old-b",
                    max_concurrent=1,
                    max_concurrent_per_user=1,
                )
            )

            new_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-mutual-new",
                user_id="user-new",
                session_id="session-new",
                max_concurrent=3,
                max_concurrent_per_user=1,
            )

            self.assertIsNotNone(new_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=3,
                    task_id="task-mutual-old-a",
                ),
                {
                    "active_count": 2,
                    "max_concurrent": 3,
                    "waiting_count": 2,
                    "wait_position": 1,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_backend_queue_e2e_asserts_safe_queue_state_payload(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        queue_e2e_module.assert_safe_queued_state_payload(
            [
                {
                    "phase": "queued",
                    "task_id": "task-e2e-queued",
                    "queue": {
                        "active_count": 1,
                        "max_concurrent": 1,
                        "waiting_count": 1,
                        "wait_position": 1,
                    },
                }
            ],
            task_id="task-e2e-queued",
            expected_wait_position=1,
        )

    def test_backend_queue_e2e_rejects_queue_state_that_leaks_task_ids(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        with self.assertRaisesRegex(RuntimeError, "leaked active_task_ids"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "max_concurrent": 1,
                            "waiting_count": 1,
                            "wait_position": 1,
                            "active_task_ids": ["task-active"],
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

    def test_backend_queue_e2e_rejects_missing_queued_state_payload(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        with self.assertRaisesRegex(RuntimeError, "missing queued state payload"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "running",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "max_concurrent": 1,
                            "waiting_count": 0,
                            "wait_position": 0,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

    def test_backend_queue_e2e_rejects_unexpected_wait_position(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        with self.assertRaisesRegex(RuntimeError, "wait_position should be 1"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "max_concurrent": 1,
                            "waiting_count": 1,
                            "wait_position": 2,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

    def test_backend_queue_e2e_asserts_safe_settings_diagnostics_payload(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        queue_e2e_module.assert_safe_queue_settings_diagnostics(
            {
                "max_concurrent": 1,
                "active_count": 1,
                "waiting_count": 1,
                "available_slots": 0,
                "current_user_active_count": 1,
                "current_user_waiting_count": 1,
                "current_user_available_slots": 0,
                "has_waiting_tasks": True,
                "saturated": True,
                "pressure_state": "saturated",
                "max_concurrent_per_user": 0,
                "max_concurrent_per_session": 0,
                "poll_interval_sec": 0.1,
                "per_user_limit_enabled": False,
                "per_session_limit_enabled": False,
                "fairness_limits_enabled": False,
                "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                "capacity_aware_fifo_enabled": True,
            },
            expected_max_concurrent=1,
            expected_active_count=1,
            expected_waiting_count=1,
            expected_available_slots=0,
            expected_current_user_active_count=1,
            expected_current_user_waiting_count=1,
            expected_current_user_available_slots=0,
            expected_pressure_state="saturated",
        )

    def test_backend_queue_e2e_rejects_settings_diagnostics_that_leak_task_ids(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "task_queue_diagnostics leaked active_task_ids",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 1,
                    "active_count": 1,
                    "waiting_count": 1,
                    "available_slots": 0,
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                    "active_task_ids": ["task-active"],
                },
                expected_max_concurrent=1,
                expected_active_count=1,
                expected_waiting_count=1,
                expected_available_slots=0,
            )

    def test_backend_queue_e2e_requires_current_user_count_fields_when_expected(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "current_user_active_count is required",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 1,
                    "active_count": 0,
                    "waiting_count": 0,
                    "available_slots": 1,
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=1,
                expected_current_user_active_count=0,
            )

    def test_backend_queue_e2e_rejects_inconsistent_current_user_available_slots(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "current_user_available_slots should match per-user limit-active",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 8,
                    "active_count": 3,
                    "waiting_count": 1,
                    "available_slots": 5,
                    "current_user_active_count": 1,
                    "current_user_waiting_count": 1,
                    "current_user_available_slots": 2,
                    "max_concurrent_per_user": 2,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": True,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": True,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=8,
            )

    def test_backend_queue_e2e_rejects_current_user_available_slots_above_global_capacity(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "current_user_available_slots should not exceed available_slots",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 2,
                    "waiting_count": 0,
                    "available_slots": 0,
                    "current_user_active_count": 1,
                    "current_user_waiting_count": 0,
                    "current_user_available_slots": 2,
                    "max_concurrent_per_user": 3,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": True,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": True,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

    def test_cancel_queued_task_forgets_waiting_queue_entry(self) -> None:
        original_get_task = task_routes_module.get_task
        original_update_task_status = task_routes_module.update_task_status
        original_forget_waiting_task = getattr(
            task_routes_module,
            "forget_waiting_task",
            None,
        )
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_cancel_summary_helper = (
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task
        )
        forgotten: list[str] = []
        task_reads = [
            {
                "id": "task-cancel-queued",
                "session_id": "session-cancel-queued",
                "status": "queued",
            },
            {
                "id": "task-cancel-queued",
                "session_id": "session-cancel-queued",
                "status": "cancelled",
            },
        ]
        try:
            task_routes_module.get_task = (
                lambda _task_id, _user_id: dict(task_reads.pop(0))
            )
            task_routes_module.update_task_status = lambda **_kwargs: None
            task_routes_module.forget_waiting_task = forgotten.append  # type: ignore[attr-defined]
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = (
                lambda task, previous_status, already_terminal: {
                    "task_id": task["id"],
                    "previous_status": previous_status,
                    "status": task["status"],
                    "status_normalized": "cancelled",
                    "status_label": "Cancelled",
                    "status_rank": 40,
                    "already_terminal": already_terminal,
                }
            )

            payload = task_routes_module.cancel_task(
                "task-cancel-queued",
                current_user={"id": "user-cancel-queued"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.update_task_status = original_update_task_status
            if original_forget_waiting_task is None:
                if hasattr(task_routes_module, "forget_waiting_task"):
                    delattr(task_routes_module, "forget_waiting_task")
            else:
                task_routes_module.forget_waiting_task = original_forget_waiting_task  # type: ignore[attr-defined]
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = (
                original_cancel_summary_helper
            )

        self.assertEqual(forgotten, ["task-cancel-queued"])
        self.assertEqual(payload.status, "cancelled")

    def test_get_tasks_forwards_query_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        calls: list[tuple[str, str | None]] = []
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Query Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("list", query))
                return [
                    {
                        "id": "task-query-1",
                        "session_id": session_id or "session-query",
                        "prompt": "query matched task",
                        "status": "completed",
                        "trace_json": None,
                        "usage_json": None,
                        "created_at": "2026-06-09T11:00:00",
                        "updated_at": "2026-06-09T11:05:00",
                    }
                ]

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("count", query))
                return 1

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-query",
                query="planning_suite",
                current_user={"id": "user-query"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(calls, [("list", "planning_suite"), ("count", "planning_suite")])
        self.assertEqual(payload.total, 1)
        self.assertEqual(len(payload.items), 1)

    def test_get_tasks_forwards_governance_filters_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile="planning_only",
                tool_registry_provider_source="planning_suite",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )

    def test_get_tasks_trusts_service_governance_filter_normalizer(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            chat_persistence_module._normalize_governance_filter = (
                lambda _value: (_ for _ in ()).throw(
                    AssertionError(
                        "task list route should trust service-layer governance filter normalization"
                    )
                )
            )
            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": " Planning_Only ",
                "tool_registry_provider_source_filter": " Planning_Suite ",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": " Planning_Only ",
                "tool_registry_provider_source_filter": " Planning_Suite ",
            },
        )

    def test_list_tasks_applies_query_to_prompt_id_and_trace_json(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-query",
                limit=20,
                session_id="session-query",
                offset=40,
                query="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(prompt) LIKE ?", rendered_query)
        self.assertIn("LOWER(id) LIKE ?", rendered_query)
        self.assertIn("LOWER(COALESCE(trace_json, '')) LIKE ?", rendered_query)
        self.assertEqual(
            rendered_params,
            (
                "user-query",
                "session-query",
                "%planning_suite%",
                "%planning_suite%",
                "%planning_suite%",
                20,
                40,
            ),
        )

    def test_list_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
                20,
                0,
            ),
        )

    def test_count_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
            ),
        )

    def test_task_list_queries_reuse_shared_governance_filter_normalizer(self) -> None:
        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {
            "normalize_inputs": [],
            "queries": [],
        }

        class FakeListCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeCountCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["queries"].append((str(query), tuple(params)))
                if "COUNT(*) AS n" in str(query):
                    return FakeCountCursor()
                return FakeListCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )

            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["normalize_inputs"],
            [
                " Planning_Only ",
                " Planning_Suite ",
                " Planning_Only ",
                " Planning_Suite ",
            ],
        )
        self.assertEqual(len(captured["queries"]), 2)
        list_query, list_params = captured["queries"][0]
        count_query, count_params = captured["queries"][1]
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", list_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            list_query,
        )
        self.assertEqual(
            list_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
                20,
                0,
            ),
        )
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", count_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            count_query,
        )
        self.assertEqual(
            count_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
            ),
        )

    def test_update_task_trace_steps_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.update_task_trace_steps(
                "task-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[2], "planning_only")
        self.assertEqual(rendered_params[3], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[4])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[5])), ["Task Planner Suite"])

    def test_complete_task_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.complete_task(
                "task-complete-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
                usage={"prompt_tokens": 1, "completion_tokens": 2},
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[4], "planning_only")
        self.assertEqual(rendered_params[5], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[6])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[7])), ["Task Planner Suite"])

    def test_initialize_postgres_database_ensures_task_governance_columns(self) -> None:
        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return SimpleNamespace(rowcount=0)

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = db_module.get_db_connection
        original_ensure_column = db_module._ensure_postgres_column
        original_ensure_indexes = db_module._ensure_common_indexes
        calls: list[tuple[str, str, str]] = []
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

        self.assertIn(("tasks", "tool_registry_profile", "TEXT"), calls)
        self.assertIn(("tasks", "tool_registry_provider_source", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_names_json", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_labels_json", "TEXT"), calls)

    def test_get_task_detail_trusts_service_governance_shape(self) -> None:
        original_get_task = task_routes_module.get_task
        original_response_builder = getattr(task_routes_module, "_build_task_response", None)
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "get_task_detail should construct governance directly from the shared row parser output"
                    )

            if original_response_builder is not None:
                task_routes_module._build_task_response = lambda _task: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                    AssertionError(
                        "get_task_detail should route governance through the shared dict-builder directly"
                    )
                )
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-service-governance-route",
                "session_id": "session-service-governance-route",
                "prompt": "service governance route task",
                "status": "completed",
                "trace_json": None,
                "usage_json": None,
                "governance": GuardedGovernanceDict(
                    profile="guarded_profile",
                    provider_source="guarded_source",
                    allowed_tool_names=["guarded_tool"],
                    allowed_tool_labels=["Guarded Tool"],
                ),
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "default",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-11T15:00:00",
                "updated_at": "2026-06-11T15:01:00",
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should trust service governance instead of reusing the shared row parser"
                    )
                )
            )
            response = task_routes_module.get_task_detail(
                "task-service-governance-route",
                current_user={"id": "user-service-governance-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )
            if original_response_builder is None:
                if hasattr(task_routes_module, "_build_task_response"):
                    delattr(task_routes_module, "_build_task_response")
            else:
                task_routes_module._build_task_response = original_response_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "guarded_profile")
        self.assertEqual(response.governance.provider_source, "guarded_source")
        self.assertEqual(response.governance.allowed_tool_names, ["guarded_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Guarded Tool"])

    def test_get_task_detail_trusts_service_governance_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-service-governance-summary-route",
                "session_id": "session-service-governance-summary-route",
                "prompt": "service governance summary route task",
                "status": "completed",
                "trace_json": None,
                "usage_json": None,
                "governance": {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                },
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "default",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-11T16:00:00",
                "updated_at": "2026-06-11T16:01:00",
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should not re-parse governance when service already provides it"
                    )
                )
            )
            response = task_routes_module.get_task_detail(
                "task-service-governance-summary-route",
                current_user={"id": "user-service-governance-summary-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "normalized_profile")
        self.assertEqual(response.governance.provider_source, "normalized_source")
        self.assertEqual(response.governance.allowed_tool_names, ["normalized_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Normalized Tool"])

    def test_task_route_module_no_longer_exposes_task_governance_summary_dict_builder(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_governance_summary_from_dict")
        )

    def test_task_route_module_no_longer_exposes_latest_seq_from_task(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_latest_seq_from_task"))

    def test_chat_persistence_service_no_longer_exposes_governance_clone_helpers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(chat_persistence_module, "_clone_task_governance_dict")
        )
        self.assertFalse(
            hasattr(chat_persistence_module, "_clone_session_governance_summary_dict")
        )

    def test_chat_persistence_service_no_longer_exposes_raw_task_trace_helpers(
        self,
    ) -> None:
        self.assertFalse(hasattr(chat_persistence_module, "get_task_trace"))
        self.assertFalse(hasattr(chat_persistence_module, "get_task_trace_delta"))
        self.assertFalse(
            hasattr(chat_persistence_module, "get_task_trace_delta_from_task")
        )

    def test_chat_persistence_service_load_trace_steps_from_trace_json_filters_and_normalizes_steps(
        self,
    ) -> None:
        original_normalizer = chat_persistence_module._normalize_trace_steps
        captured: list[object] = []
        try:
            chat_persistence_module._normalize_trace_steps = lambda steps: captured.append(  # type: ignore[attr-defined]
                steps
            ) or [
                {
                    "id": "normalized-step",
                    "type": "thought",
                    "content": "normalized",
                    "seq": 3,
                }
            ]
            payload = chat_persistence_module._load_trace_steps_from_trace_json(  # type: ignore[attr-defined]
                json.dumps(
                    [
                        {"id": "raw-step", "type": "thought", "content": "raw", "seq": 3},
                        "skip-me",
                    ]
                )
            )
        finally:
            chat_persistence_module._normalize_trace_steps = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [[{"id": "raw-step", "type": "thought", "content": "raw", "seq": 3}]],
        )
        self.assertEqual(
            payload,
            [
                {
                    "id": "normalized-step",
                    "type": "thought",
                    "content": "normalized",
                    "seq": 3,
                }
            ],
        )

    def test_chat_persistence_service_load_parsed_trace_steps_from_trace_json_reuses_shared_loader_and_trace_parser(
        self,
    ) -> None:
        original_loader = chat_persistence_module._load_trace_steps_from_trace_json  # type: ignore[attr-defined]
        original_parser = chat_persistence_module.parse_trace_steps  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._load_trace_steps_from_trace_json = lambda raw: captured.append(  # type: ignore[attr-defined]
                ("loader", raw)
            ) or [
                {
                    "id": "raw-step",
                    "type": "thought",
                    "content": "raw",
                    "seq": 4,
                }
            ]
            chat_persistence_module.parse_trace_steps = lambda steps: captured.append(  # type: ignore[attr-defined]
                ("parser", steps)
            ) or [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="parsed-step",
                    type="thought",
                    content="parsed",
                    seq=4,
                )
            ]
            payload = chat_persistence_module._load_parsed_trace_steps_from_trace_json(  # type: ignore[attr-defined]
                "guarded-trace-json"
            )
        finally:
            chat_persistence_module._load_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.parse_trace_steps = original_parser  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                ("loader", "guarded-trace-json"),
                (
                    "parser",
                    [
                        {
                            "id": "raw-step",
                            "type": "thought",
                            "content": "raw",
                            "seq": 4,
                        }
                    ],
                ),
            ],
        )
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0].id, "parsed-step")

    def test_legacy_task_governance_trace_json_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_trace_json",
            )
        )

    def test_legacy_task_governance_parsed_trace_steps_helper_is_removed(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_parsed_trace_steps",
            )
        )

    def test_legacy_task_governance_parsed_trace_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_task_with_parsed_trace_steps",
            )
        )

    def test_get_task_trace_steps_reuses_shared_parsed_trace_steps_loader(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "get_task_trace_steps",
            )
        )

    def test_get_task_trace_steps_from_task_reuses_shared_parsed_trace_steps_loader(
        self,
    ) -> None:
        original_loader = chat_persistence_module._load_parsed_trace_steps_from_trace_json  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="parsed-step",
                        type="thought",
                        content="parsed",
                        seq=6,
                    )
                ]
            )
            payload = chat_persistence_module.get_task_trace_steps_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"}
            )
        finally:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]

        self.assertEqual(captured, ["guarded-trace-json"])
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0].seq, 6)

    def test_get_task_trace_steps_from_task_accepts_model_dump_row(self) -> None:
        original_loader = chat_persistence_module._load_parsed_trace_steps_from_trace_json  # type: ignore[attr-defined]

        class TaskRowPayload:
            def model_dump(self):
                return {"trace_json": "typed-trace-json"}

        captured: list[object] = []
        try:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="typed-parsed-step",
                        type="thought",
                        content="typed parsed",
                        seq=8,
                    )
                ]
            )
            payload = chat_persistence_module.get_task_trace_steps_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]

        self.assertEqual(captured, ["typed-trace-json"])
        self.assertEqual([step.id for step in payload], ["typed-parsed-step"])

    def test_legacy_task_trace_delta_steps_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "get_task_trace_delta_steps_from_task",
            )
        )

    def test_get_task_trace_delta_snapshot_from_task_reuses_shared_task_trace_steps_helper(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-1",
                    type="thought",
                    content="first",
                    seq=1,
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-3",
                    type="thought",
                    content="third",
                    seq=3,
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-5",
                    type="thought",
                    content="fifth",
                    seq=5,
                ),
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                {"status": "completed", "trace_json": "guarded-trace-json"},
                after_seq=1,
                limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        self.assertEqual([step.seq for step in payload], [3])
        self.assertEqual(next_cursor, 3)
        self.assertTrue(has_more)
        self.assertEqual(latest_seq, 5)
        self.assertEqual(latest_step_id, "step-5")

    def test_get_task_trace_delta_snapshot_from_task_accepts_model_dump_row(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]

        class TaskRowPayload:
            def model_dump(self):
                return {"status": "running", "trace_json": "typed-trace-json"}

        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="typed-delta-step",
                    type="thought",
                    content="typed delta",
                    seq=5,
                )
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                TaskRowPayload(),
                after_seq=0,
                limit=20,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        self.assertEqual([step.id for step in payload], ["typed-delta-step"])
        self.assertEqual(next_cursor, 5)
        self.assertTrue(has_more)
        self.assertEqual(latest_seq, 5)
        self.assertEqual(latest_step_id, "typed-delta-step")

    def test_get_task_trace_delta_snapshot_from_task_sanitizes_legacy_http_json_content(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="delta-step-http-json-legacy-content",
            type="action",
            content=(
                'Tool done: Provider Status Preview: {"status":"ready",'
                '"message":"gateway token=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"}'
            ),
            seq=9,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": ["status", "message"],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                {"status": "completed", "trace_json": "guarded-delta-trace-json"},
                after_seq=0,
                limit=20,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        serialized = json.dumps([step.model_dump() for step in payload], ensure_ascii=False)
        self.assertEqual(next_cursor, 9)
        self.assertFalse(has_more)
        self.assertEqual(latest_seq, 9)
        self.assertEqual(latest_step_id, "delta-step-http-json-legacy-content")
        self.assertIn("gateway token=[redacted]", payload[0].content)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_task_route_module_no_longer_exposes_task_trace_delta_steps_helper(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "get_task_trace_delta_steps_from_task"))

    def test_stream_running_task_reconnect_reuses_task_trace_steps_from_current_task_for_terminal_step_id(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_task = task_routes_module.get_task
        original_trace_steps_loader = (
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task
        )
        original_delta_snapshot_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        try:
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_steps"))
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_delta_steps_from_task"))
            task = {
                "id": "task-reconnect-terminal-step-id",
                "session_id": "session-reconnect-terminal-step-id",
                "status": "completed",
                "usage_json": json.dumps({"prompt_tokens": 3, "completion_tokens": 5}),
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.get_settings = lambda: SimpleNamespace(
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.5,
                stream_reconnect_heartbeat_interval_sec=1.0,
            )
            task_routes_module.get_task = lambda _task_id, _user_id: dict(task)
            task_routes_module.get_task_trace_steps = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "terminal reconnect stream should reuse get_task_trace_steps_from_task(task) instead of refetching full trace by task id"
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "terminal reconnect stream should reuse get_task_trace_delta_snapshot_from_task(task) instead of reloading full steps after delta polling"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: (
                    [],
                    after_seq,
                    False,
                    7,
                    "fallback::guarded-trace-json",
                )
            )

            async def collect_events() -> list[str]:
                events: list[str] = []
                async for event in task_routes_module.stream_running_task_reconnect(
                    "task-reconnect-terminal-step-id",
                    "user-reconnect-terminal-step-id",
                ):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_task = original_get_task
            if hasattr(task_routes_module, "get_task_trace_steps"):
                delattr(task_routes_module, "get_task_trace_steps")
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (
                original_trace_steps_loader
            )
            if original_delta_snapshot_loader is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_loader  # type: ignore[attr-defined]

        self.assertEqual(len(events), 2)
        self.assertIn('"status": "completed"', events[-1])
        self.assertIn(
            '"step_id": "fallback::guarded-trace-json"',
            events[-1],
        )

    def test_chat_persistence_service_parse_usage_json_blob_accepts_only_dict_payloads(
        self,
    ) -> None:
        payload = chat_persistence_module._parse_usage_json_blob(  # type: ignore[attr-defined]
            json.dumps(
                {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "cost_estimate": 0.12,
                }
            )
        )
        self.assertEqual(
            payload,
            {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost_estimate": 0.12,
            },
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob(json.dumps(["skip"]))  # type: ignore[attr-defined]
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob("not-json")  # type: ignore[attr-defined]
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob(None)  # type: ignore[attr-defined]
        )

    def test_get_task_usage_from_task_reuses_shared_usage_json_parser(self) -> None:
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or {
                    "prompt_tokens": 8,
                    "completion_tokens": 13,
                    "cost_estimate": 0.03,
                }
            )
            payload = chat_persistence_module.get_task_usage_from_task(  # type: ignore[attr-defined]
                {"usage_json": "usage-json-guarded"}
            )
        finally:
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-guarded"])
        self.assertEqual(
            payload,
            {
                "prompt_tokens": 8,
                "completion_tokens": 13,
                "cost_estimate": 0.03,
            },
        )

    def test_get_task_usage_from_task_accepts_model_dump_row(self) -> None:
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []

        class TaskRowPayload:
            def model_dump(self):
                return {"usage_json": "typed-usage-json"}

        try:
            chat_persistence_module._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw) or {"total_tokens": 21}
            )
            payload = chat_persistence_module.get_task_usage_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["typed-usage-json"])
        self.assertEqual(payload, {"total_tokens": 21})
