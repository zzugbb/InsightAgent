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
