from __future__ import annotations


class ProductionReliabilityQueueMixin:
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
