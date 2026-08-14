from __future__ import annotations

from .context import *


class AuditLogsFiltersMixin:
    def test_list_audit_logs_applies_keyword_to_event_type_and_detail(
        self,
    ) -> None:
        original_get_db_connection = audit_service_module.get_db_connection
        execute_calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeConnection:
            def execute(self, sql: str, params: tuple[object, ...]):
                execute_calls.append((sql, params))

                class Result:
                    def fetchall(self):
                        return []

                return Result()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            audit_service_module.get_db_connection = lambda: FakeContextManager()  # type: ignore[assignment]
            audit_service_module.list_audit_logs(
                user_id="user-audit-keyword",
                keyword=" Failed Provider ",
                limit=10,
                offset=0,
            )
        finally:
            audit_service_module.get_db_connection = original_get_db_connection  # type: ignore[assignment]

        self.assertEqual(len(execute_calls), 1)
        sql, params = execute_calls[0]
        self.assertIn("LOWER(event_type) LIKE ?", sql)
        self.assertIn("LOWER(COALESCE(event_detail_json, '')) LIKE ?", sql)
        self.assertIn("%failed provider%", params)
        self.assertEqual(params[-2:], (10, 0))

    def test_count_audit_logs_applies_keyword_to_event_type_and_detail(
        self,
    ) -> None:
        original_get_db_connection = audit_service_module.get_db_connection
        execute_calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeRow(dict):
            def __getitem__(self, key):
                return super().__getitem__(key)

        class FakeConnection:
            def execute(self, sql: str, params: tuple[object, ...]):
                execute_calls.append((sql, params))

                class Result:
                    def fetchone(self):
                        return FakeRow(n=3)

                return Result()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            audit_service_module.get_db_connection = lambda: FakeContextManager()  # type: ignore[assignment]
            total = audit_service_module.count_audit_logs(
                user_id="user-audit-keyword",
                keyword=" remote_provider_network_error ",
            )
        finally:
            audit_service_module.get_db_connection = original_get_db_connection  # type: ignore[assignment]

        self.assertEqual(total, 3)
        self.assertEqual(len(execute_calls), 1)
        sql, params = execute_calls[0]
        self.assertIn("LOWER(event_type) LIKE ?", sql)
        self.assertIn("LOWER(COALESCE(event_detail_json, '')) LIKE ?", sql)
        self.assertIn("%remote_provider_network_error%", params)

    def test_get_audit_logs_forwards_keyword_to_list_and_count(self) -> None:
        original_list_audit_logs = audit_routes_module.list_audit_logs
        original_count_audit_logs = audit_routes_module.count_audit_logs
        captured: dict[str, object] = {}

        def fake_list_audit_logs(**kwargs):
            captured["list_keyword"] = kwargs.get("keyword")
            return []

        def fake_count_audit_logs(**kwargs):
            captured["count_keyword"] = kwargs.get("keyword")
            return 0

        try:
            audit_routes_module.list_audit_logs = fake_list_audit_logs  # type: ignore[assignment]
            audit_routes_module.count_audit_logs = fake_count_audit_logs  # type: ignore[assignment]
            payload = audit_routes_module.get_audit_logs(
                limit=10,
                offset=0,
                event_type=None,
                session_id=None,
                task_id=None,
                keyword=" provider failed ",
                start_at=None,
                end_at=None,
                current_user={"id": "user-audit-keyword-route"},
            )
        finally:
            audit_routes_module.list_audit_logs = original_list_audit_logs  # type: ignore[assignment]
            audit_routes_module.count_audit_logs = original_count_audit_logs  # type: ignore[assignment]

        self.assertEqual(payload.items, [])
        self.assertEqual(captured["list_keyword"], "provider failed")
        self.assertEqual(captured["count_keyword"], "provider failed")
