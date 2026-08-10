from __future__ import annotations

from .context import *


class AuditProviderSourceArtifactsMixin:
    def test_sanitize_audit_event_detail_redacts_provider_source_values(
        self,
    ) -> None:
        result = audit_service_module.sanitize_audit_event_detail(
            {
                "provider_source": "suite_api_key=hidden",
                "nested": {
                    "provider_source_name": "fallback_access_token=hidden",
                    "provider_sources": [
                        "suite_api_key=hidden",
                        "fallback_access_token=hidden",
                    ],
                },
            }
        )

        self.assertIsInstance(result, dict)
        assert isinstance(result, dict)
        self.assertEqual(result["provider_source"], "suite_[redacted]")
        self.assertEqual(
            result["nested"]["provider_source_name"],
            "fallback_[redacted]",
        )
        self.assertEqual(
            result["nested"]["provider_sources"],
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", json.dumps(result, default=str))
        self.assertNotIn("access_token=hidden", json.dumps(result, default=str))

    def test_record_audit_event_redacts_provider_source_values_before_insert(
        self,
    ) -> None:
        original_get_db_connection = audit_service_module.get_db_connection
        execute_calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeConnection:
            def execute(self, sql: str, params: tuple[object, ...]):
                execute_calls.append((sql, params))

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            audit_service_module.get_db_connection = lambda: FakeContextManager()  # type: ignore[assignment]
            audit_service_module.record_audit_event(
                user_id="user-audit-source-redaction",
                event_type="task_failed",
                detail={
                    "task_id": "task-audit-source-redaction",
                    "provider_source": "suite_api_key=hidden",
                    "diagnostics": {
                        "provider_sources": [
                            "suite_api_key=hidden",
                            "fallback_access_token=hidden",
                        ],
                    },
                },
            )
        finally:
            audit_service_module.get_db_connection = original_get_db_connection  # type: ignore[assignment]

        self.assertEqual(len(execute_calls), 1)
        detail_json = execute_calls[0][1][3]
        self.assertIsInstance(detail_json, str)
        inserted_detail = json.loads(str(detail_json))
        self.assertEqual(
            inserted_detail["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            inserted_detail["diagnostics"]["provider_sources"],
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", str(detail_json))
        self.assertNotIn("access_token=hidden", str(detail_json))

    def test_sanitize_audit_event_detail_redacts_tool_registry_provider_source_values(
        self,
    ) -> None:
        result = audit_service_module.sanitize_audit_event_detail(
            {
                "tool_registry_provider_source": "suite_api_key=hidden",
                "nested": {
                    "tool_registry_provider_sources": [
                        "suite_api_key=hidden",
                        "fallback_access_token=hidden",
                    ],
                },
            }
        )

        self.assertIsInstance(result, dict)
        assert isinstance(result, dict)
        self.assertEqual(
            result["tool_registry_provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            result["nested"]["tool_registry_provider_sources"],
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", json.dumps(result, default=str))
        self.assertNotIn("access_token=hidden", json.dumps(result, default=str))
