from __future__ import annotations

from .context import *


class TraceProviderSourceArtifactsMixin:
    def test_trace_step_export_redacts_provider_source_meta_values(
        self,
    ) -> None:
        step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="trace-source-redaction",
            type="thought",
            content="trace provider source redaction",
            seq=1,
            meta={
                "tool_registry_provider_source": "suite_api_key=hidden",
                "provider_source": "fallback_access_token=hidden",
                "nested": {
                    "provider_source_name": "suite_api_key=hidden",
                    "provider_sources": [
                        "suite_api_key=hidden",
                        "fallback_access_token=hidden",
                    ],
                },
            },
        )

        sanitized = chat_persistence_module._sanitize_trace_step_for_export(step)  # type: ignore[attr-defined]
        payload = sanitized.model_dump()

        self.assertEqual(
            payload["meta"]["tool_registry_provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(payload["meta"]["provider_source"], "fallback_[redacted]")
        self.assertEqual(
            payload["meta"]["nested"]["provider_source_name"],
            "suite_[redacted]",
        )
        self.assertEqual(
            payload["meta"]["nested"]["provider_sources"],
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))
        self.assertNotIn("access_token=hidden", json.dumps(payload, default=str))

    def test_task_trace_response_redacts_provider_source_meta_values(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_trace_summary = (
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task
        )
        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: {
                "id": "task-trace-source-redaction",
            }
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "steps": [
                        {
                            "id": "trace-source-redaction",
                            "type": "thought",
                            "content": "trace provider source redaction",
                            "seq": 1,
                            "meta": {
                                "tool_registry_provider_source": "suite_api_key=hidden",
                                "provider_source_name": "fallback_access_token=hidden",
                            },
                        }
                    ],
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 30,
                }
            )

            response = task_routes_module.get_task_trace_detail(
                "task-trace-source-redaction",
                current_user={"id": "user-trace-source-redaction"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_summary  # type: ignore[attr-defined]

        payload = response.model_dump()
        self.assertEqual(
            payload["steps"][0]["meta"]["tool_registry_provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            payload["steps"][0]["meta"]["provider_source_name"],
            "fallback_[redacted]",
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))
        self.assertNotIn("access_token=hidden", json.dumps(payload, default=str))
