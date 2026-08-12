from __future__ import annotations

from .context import *


class SseProviderSourceArtifactsMixin:
    def test_sse_error_payload_redacts_provider_source_values(
        self,
    ) -> None:
        payload = chat_execution_module.sse_error_payload(
            task_id="task-sse-source-redaction",
            message=(
                "tool registry failed "
                "provider_source=suite_api_key=hidden "
                "tool_registry_provider_source=fallback_access_token=hidden"
            ),
            code="task_stream_failure",
            fatal=True,
            retry_count=0,
            detail=(
                "diagnostics provider_source_name=suite_api_key=hidden "
                "provider_source=fallback_access_token=hidden"
            ),
            status_code=502,
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("provider_source=suite_[redacted]", serialized)
        self.assertIn(
            "tool_registry_provider_source=fallback_[redacted]",
            serialized,
        )
        self.assertIn("provider_source_name=suite_[redacted]", serialized)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token=hidden", serialized)
        self.assertEqual(payload["task_id"], "task-sse-source-redaction")
        self.assertEqual(payload["code"], "task_stream_failure")
        self.assertEqual(payload["status_code"], 502)

    def test_sse_error_payload_preserves_colliding_provider_source_aliases(
        self,
    ) -> None:
        payload = chat_execution_module.sse_error_payload(
            task_id="task-sse-source-alias",
            message=(
                "registry failed provider_source=suite_api_key=one "
                "tool_registry_provider_source=suite_access_token=two"
            ),
            code="task_stream_failure",
            fatal=True,
            retry_count=1,
            detail=(
                "diagnostics provider_source_name=suite_access_token=two "
                "provider_source=suite_api_key=one"
            ),
            status_code=502,
        )

        self.assertEqual(
            payload["message"],
            (
                "registry failed provider_source=suite_[redacted]#1 "
                "tool_registry_provider_source=suite_[redacted]#2"
            ),
        )
        self.assertEqual(
            payload["detail"],
            (
                "diagnostics provider_source_name=suite_[redacted]#2 "
                "provider_source=suite_[redacted]#1"
            ),
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("api_key=one", serialized)
        self.assertNotIn("access_token=two", serialized)
