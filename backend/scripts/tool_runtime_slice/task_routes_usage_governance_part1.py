from __future__ import annotations

from .context import *


class TaskRoutesUsageGovernanceMixinPart1:
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

    def test_tasks_usage_dashboard_response_preserves_cross_section_provider_source_aliases(
        self,
    ) -> None:
        normalized = task_routes_module._coerce_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "by_session": [
                    {
                        "session_id": "session-dashboard-alias",
                        "governance": {
                            "provider_sources": [
                                "suite_access_token=two",
                                "suite_api_key=one",
                            ],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-dashboard-api-key",
                        "governance": {
                            "provider_source": "suite_api_key=one",
                        },
                    },
                    {
                        "task_id": "task-dashboard-access-token",
                        "governance": {
                            "provider_source": "suite_access_token=two",
                        },
                    },
                ],
            }
        )

        self.assertEqual(
            normalized["by_session"][0]["governance"]["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            normalized["top_tasks"][0]["governance"]["provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(
            normalized["top_tasks"][1]["governance"]["provider_source"],
            "suite_[redacted]#1",
        )
        serialized = json.dumps(normalized, ensure_ascii=False)
        self.assertNotIn("api_key=one", serialized)
        self.assertNotIn("access_token=two", serialized)

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

    def test_task_queue_service_duplicate_active_task_does_not_get_execution_slot(
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
            self.assertIsNone(duplicate_slot)

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

    def test_task_queue_service_blocks_new_same_user_when_older_waiter_reserves_user_quota(
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
                task_id="task-user-reserve-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
                max_concurrent_per_user=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-user-reserve-old",
                    user_id="user-old",
                    session_id="session-old-a",
                    max_concurrent=1,
                    max_concurrent_per_user=1,
                )
            )

            active_slot.release()
            same_user_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-user-reserve-new",
                user_id="user-old",
                session_id="session-old-b",
                max_concurrent=2,
                max_concurrent_per_user=1,
            )

            self.assertIsNone(same_user_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=2,
                    task_id="task-user-reserve-new",
                    user_id="user-old",
                ),
                {
                    "active_count": 0,
                    "max_concurrent": 2,
                    "waiting_count": 2,
                    "wait_position": 2,
                    "active_count_for_user": 0,
                    "waiting_count_for_user": 2,
                },
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

    def test_task_queue_service_blocks_new_same_session_when_older_waiter_reserves_session_quota(
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
                task_id="task-session-reserve-active",
                user_id="user-active",
                session_id="session-active",
                max_concurrent=1,
                max_concurrent_per_session=1,
            )
            self.assertIsNotNone(active_slot)
            self.assertIsNone(
                task_queue_module.try_acquire_task_execution_slot(
                    task_id="task-session-reserve-old",
                    user_id="user-old-a",
                    session_id="session-old",
                    max_concurrent=1,
                    max_concurrent_per_session=1,
                )
            )

            active_slot.release()
            same_session_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="task-session-reserve-new",
                user_id="user-old-b",
                session_id="session-old",
                max_concurrent=2,
                max_concurrent_per_session=1,
            )

            self.assertIsNone(same_session_slot)
            self.assertEqual(
                task_queue_module.get_task_queue_snapshot(
                    max_concurrent=2,
                    task_id="task-session-reserve-new",
                    session_id="session-old",
                ),
                {
                    "active_count": 0,
                    "max_concurrent": 2,
                    "waiting_count": 2,
                    "wait_position": 2,
                    "active_count_for_session": 0,
                    "waiting_count_for_session": 2,
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

    def test_backend_queue_e2e_requires_queue_snapshot_count_fields(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        with self.assertRaisesRegex(RuntimeError, "active_count is required"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "max_concurrent": 1,
                            "waiting_count": 1,
                            "wait_position": 1,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

        with self.assertRaisesRegex(RuntimeError, "max_concurrent is required"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "waiting_count": 1,
                            "wait_position": 1,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

        with self.assertRaisesRegex(RuntimeError, "waiting_count is required"):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "max_concurrent": 1,
                            "wait_position": 1,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

    def test_backend_queue_e2e_rejects_non_integer_queue_snapshot_count_fields(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )
        base_queue = {
            "active_count": 1,
            "max_concurrent": 2,
            "waiting_count": 1,
            "wait_position": 1,
        }

        invalid_values = {
            "active_count": "1",
            "max_concurrent": True,
            "waiting_count": 1.5,
        }
        for field_name, invalid_value in invalid_values.items():
            with self.subTest(field_name=field_name):
                queue_payload = dict(base_queue)
                queue_payload[field_name] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"queued {field_name} should be an integer",
                ):
                    queue_e2e_module.assert_safe_queued_state_payload(
                        [
                            {
                                "phase": "queued",
                                "task_id": "task-e2e-queued",
                                "queue": queue_payload,
                            }
                        ],
                        task_id="task-e2e-queued",
                        expected_wait_position=1,
                    )

    def test_backend_queue_e2e_rejects_non_integer_queue_snapshot_wait_position(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        for invalid_value in ("1", True, 1.5):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "queued wait_position should be an integer",
                ):
                    queue_e2e_module.assert_safe_queued_state_payload(
                        [
                            {
                                "phase": "queued",
                                "task_id": "task-e2e-queued",
                                "queue": {
                                    "active_count": 1,
                                    "max_concurrent": 2,
                                    "waiting_count": 1,
                                    "wait_position": invalid_value,
                                },
                            }
                        ],
                        task_id="task-e2e-queued",
                        expected_wait_position=1,
                    )

    def test_backend_queue_e2e_rejects_non_integer_queue_snapshot_scope_counts(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )
        base_queue = {
            "active_count": 1,
            "max_concurrent": 2,
            "waiting_count": 1,
            "wait_position": 1,
            "active_count_for_user": 1,
            "waiting_count_for_user": 1,
            "active_count_for_session": 1,
            "waiting_count_for_session": 1,
        }

        invalid_values = {
            "active_count_for_user": "1",
            "waiting_count_for_user": 1.5,
            "active_count_for_session": True,
            "waiting_count_for_session": "1",
        }
        for field_name, invalid_value in invalid_values.items():
            with self.subTest(field_name=field_name):
                queue_payload = dict(base_queue)
                queue_payload[field_name] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"queued {field_name} should be an integer",
                ):
                    queue_e2e_module.assert_safe_queued_state_payload(
                        [
                            {
                                "phase": "queued",
                                "task_id": "task-e2e-queued",
                                "queue": queue_payload,
                            }
                        ],
                        task_id="task-e2e-queued",
                        expected_wait_position=1,
                    )

    def test_backend_queue_e2e_rejects_queue_snapshot_scope_counts_above_global(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )
        base_queue = {
            "active_count": 1,
            "max_concurrent": 2,
            "waiting_count": 1,
            "wait_position": 1,
            "active_count_for_user": 1,
            "waiting_count_for_user": 1,
            "active_count_for_session": 1,
            "waiting_count_for_session": 1,
        }
        invalid_values = {
            "active_count_for_user": 2,
            "waiting_count_for_user": 2,
            "active_count_for_session": 2,
            "waiting_count_for_session": 2,
        }

        for field_name, invalid_value in invalid_values.items():
            with self.subTest(field_name=field_name):
                queue_payload = dict(base_queue)
                queue_payload[field_name] = invalid_value
                expected_global_field = (
                    "active_count"
                    if field_name.startswith("active_count")
                    else "waiting_count"
                )
                with self.assertRaisesRegex(
                    RuntimeError,
                    (
                        f"queued {field_name} should not exceed "
                        f"{expected_global_field}"
                    ),
                ):
                    queue_e2e_module.assert_safe_queued_state_payload(
                        [
                            {
                                "phase": "queued",
                                "task_id": "task-e2e-queued",
                                "queue": queue_payload,
                            }
                        ],
                        task_id="task-e2e-queued",
                        expected_wait_position=1,
                    )

    def test_backend_queue_e2e_rejects_inconsistent_queue_snapshot_counts(self) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queued_state_payload"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "active_count should not exceed max_concurrent",
        ):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 2,
                            "max_concurrent": 1,
                            "waiting_count": 1,
                            "wait_position": 1,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=1,
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "wait_position should be positive",
        ):
            queue_e2e_module.assert_safe_queued_state_payload(
                [
                    {
                        "phase": "queued",
                        "task_id": "task-e2e-queued",
                        "queue": {
                            "active_count": 1,
                            "max_concurrent": 1,
                            "waiting_count": 1,
                            "wait_position": 0,
                        },
                    }
                ],
                task_id="task-e2e-queued",
                expected_wait_position=0,
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "wait_position should not exceed waiting_count",
        ):
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
                expected_wait_position=2,
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
                            "waiting_count": 2,
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
                "current_session_active_count": 1,
                "current_session_waiting_count": 1,
                "current_session_available_slots": 0,
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
            expected_current_session_active_count=1,
            expected_current_session_waiting_count=1,
            expected_current_session_available_slots=0,
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

    def test_backend_queue_e2e_requires_settings_diagnostics_count_fields(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(RuntimeError, "active_count is required"):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "waiting_count": 0,
                    "available_slots": 2,
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

        with self.assertRaisesRegex(RuntimeError, "waiting_count is required"):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 0,
                    "available_slots": 2,
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

        with self.assertRaisesRegex(RuntimeError, "available_slots is required"):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 0,
                    "waiting_count": 0,
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

    def test_backend_queue_e2e_rejects_non_integer_settings_diagnostics_count_fields(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        invalid_values = {
            "active_count": "0",
            "waiting_count": 0.5,
            "available_slots": True,
        }
        for field_name, invalid_value in invalid_values.items():
            with self.subTest(field_name=field_name):
                payload = dict(base_payload)
                payload[field_name] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{field_name} should be an integer",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_non_integer_settings_diagnostics_max_concurrent(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "max_concurrent should be an integer",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": True,
                    "active_count": 0,
                    "waiting_count": 0,
                    "available_slots": 1,
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "idle",
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
            )

    def test_backend_queue_e2e_requires_settings_diagnostics_governance_fields(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        required_fields = (
            "max_concurrent_per_user",
            "max_concurrent_per_session",
            "poll_interval_sec",
            "per_user_limit_enabled",
            "per_session_limit_enabled",
            "fairness_limits_enabled",
            "waiting_policy",
            "capacity_aware_fifo_enabled",
        )
        for missing_field in required_fields:
            with self.subTest(missing_field=missing_field):
                payload = dict(base_payload)
                payload.pop(missing_field)
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{missing_field} is required",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_non_integer_settings_diagnostics_limits(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        invalid_values = {
            "max_concurrent_per_user": "0",
            "max_concurrent_per_session": 0.5,
        }
        for field_name, invalid_value in invalid_values.items():
            with self.subTest(field_name=field_name):
                payload = dict(base_payload)
                payload[field_name] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{field_name} should be an integer",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_non_numeric_settings_diagnostics_poll_interval(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        for invalid_value in ("0.1", True):
            with self.subTest(invalid_value=invalid_value):
                payload = dict(base_payload)
                payload["poll_interval_sec"] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    "poll_interval_sec should be a number",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_negative_settings_diagnostics_limits(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        for limit_field in (
            "max_concurrent_per_user",
            "max_concurrent_per_session",
        ):
            with self.subTest(limit_field=limit_field):
                payload = dict(base_payload)
                payload[limit_field] = -1
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{limit_field} should be non-negative",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_requires_settings_diagnostics_status_fields(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        for missing_field in ("has_waiting_tasks", "saturated", "pressure_state"):
            with self.subTest(missing_field=missing_field):
                payload = dict(base_payload)
                payload.pop(missing_field)
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{missing_field} is required",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_non_boolean_settings_diagnostics_flags(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        for flag_field in (
            "has_waiting_tasks",
            "saturated",
            "per_user_limit_enabled",
            "per_session_limit_enabled",
            "fairness_limits_enabled",
            "capacity_aware_fifo_enabled",
        ):
            with self.subTest(flag_field=flag_field):
                payload = dict(base_payload)
                payload[flag_field] = "false"
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{flag_field} should be boolean",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_non_exact_pressure_state_diagnostic(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )
        base_payload = {
            "max_concurrent": 2,
            "active_count": 0,
            "waiting_count": 0,
            "available_slots": 2,
            "has_waiting_tasks": False,
            "saturated": False,
            "pressure_state": "idle",
            "max_concurrent_per_user": 0,
            "max_concurrent_per_session": 0,
            "poll_interval_sec": 0.1,
            "per_user_limit_enabled": False,
            "per_session_limit_enabled": False,
            "fairness_limits_enabled": False,
            "waiting_policy": "capacity_aware_oldest_eligible_fifo",
            "capacity_aware_fifo_enabled": True,
        }

        for invalid_value in (" IDLE ", "Idle"):
            with self.subTest(invalid_value=invalid_value):
                payload = dict(base_payload)
                payload["pressure_state"] = invalid_value
                with self.assertRaisesRegex(
                    RuntimeError,
                    "pressure_state should be an exact enum value",
                ):
                    queue_e2e_module.assert_safe_queue_settings_diagnostics(
                        payload,
                        expected_max_concurrent=2,
                    )

    def test_backend_queue_e2e_rejects_inconsistent_has_waiting_tasks_diagnostic(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "has_waiting_tasks should match waiting_count",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 1,
                    "waiting_count": 1,
                    "available_slots": 1,
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "scope_limited",
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

    def test_backend_queue_e2e_rejects_inconsistent_saturated_diagnostic(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "saturated should match available_slots",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 1,
                    "waiting_count": 0,
                    "available_slots": 1,
                    "has_waiting_tasks": False,
                    "saturated": True,
                    "pressure_state": "active",
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

    def test_backend_queue_e2e_rejects_inconsistent_pressure_state_diagnostic(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "pressure_state should match queue pressure",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 1,
                    "waiting_count": 1,
                    "available_slots": 1,
                    "has_waiting_tasks": True,
                    "saturated": False,
                    "pressure_state": "active",
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
            )

    def test_backend_queue_e2e_rejects_unknown_pressure_state_diagnostic(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "pressure_state should be an exact enum value",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 2,
                    "active_count": 0,
                    "waiting_count": 0,
                    "available_slots": 2,
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "waiting",
                    "max_concurrent_per_user": 0,
                    "max_concurrent_per_session": 0,
                    "poll_interval_sec": 0.1,
                    "per_user_limit_enabled": False,
                    "per_session_limit_enabled": False,
                    "fairness_limits_enabled": False,
                    "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                    "capacity_aware_fifo_enabled": True,
                },
                expected_max_concurrent=2,
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
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "idle",
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

    def test_backend_queue_e2e_requires_current_user_active_count_for_available_slots(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "current_user_available_slots requires current_user_active_count",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 1,
                    "active_count": 0,
                    "waiting_count": 0,
                    "available_slots": 1,
                    "current_user_available_slots": 1,
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "idle",
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
            )

    def test_backend_queue_e2e_requires_current_user_active_count_for_waiting_count(
        self,
    ) -> None:
        queue_e2e_module = __import__(
            "scripts.e2e_queue_concurrency",
            fromlist=["assert_safe_queue_settings_diagnostics"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "current_user_waiting_count requires current_user_active_count",
        ):
            queue_e2e_module.assert_safe_queue_settings_diagnostics(
                {
                    "max_concurrent": 1,
                    "active_count": 0,
                    "waiting_count": 0,
                    "available_slots": 1,
                    "current_user_waiting_count": 0,
                    "has_waiting_tasks": False,
                    "saturated": False,
                    "pressure_state": "idle",
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
            )
