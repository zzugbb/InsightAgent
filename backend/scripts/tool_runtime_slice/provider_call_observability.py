"""Remote HTTP attempt counts and redaction contract."""

from __future__ import annotations

import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from app.providers.base import ProviderCallError
from app.providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from summarize_provider_attempts import summarize


class _Response:
    status = 200

    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self.lines)

    def read(self):
        return b"".join(self.lines)


class ProviderCallObservabilityMixin:
    def test_provider_attempt_records_non_stream_usage_without_content(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="private-model", provider="private-provider",
            base_url="https://private.example/v1", api_key="secret-key",
        )
        body = b'{"choices":[{"message":{"content":"private answer"}}],"usage":{"total_tokens":3}}'
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([body])):
            with self.assertLogs("insightagent.llm", level="INFO") as logs:
                self.assertEqual(provider.generate("private prompt").content, "private answer")
        event = json.loads(logs.output[0].split(":", 2)[2])
        self.assertEqual((event["outcome"], event["status_family"], event["usage_available"]),
                         ("http_response", "2xx", True))
        self.assertNotIn("private", logs.output[0])

    def test_provider_attempt_logs_http_error_without_sensitive_content(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="private-model", provider="private-provider",
            base_url="https://private.example/v1", api_key="secret-key",
        )
        error = HTTPError(
            provider._endpoint, 429, "limited", {},
            io.BytesIO(b'{"error":{"message":"private prompt leaked"}}'),
        )
        self.addCleanup(error.close)
        with patch("app.providers.openai_compatible_provider.urlopen", side_effect=error):
            with self.assertLogs("insightagent.llm", level="INFO") as logs:
                with self.assertRaises(ProviderCallError):
                    provider.generate("private prompt")

        self.assertEqual(len(logs.output), 1)
        event = json.loads(logs.output[0].split(":", 2)[2])
        self.assertEqual((event["mode"], event["outcome"], event["status_family"]),
                         ("request", "http_error", "4xx"))
        self.assertEqual(set(event), {
            "event", "mode", "outcome", "status_family", "duration_ms", "usage_available",
        })
        for secret in ("private prompt", "secret-key", "private-model", "private-provider", "private.example"):
            self.assertNotIn(secret, logs.output[0])

    def test_provider_attempt_counts_stream_compat_retry_and_success(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="model", provider="provider", base_url="https://example.test/v1", api_key="key",
        )
        calls = [
            HTTPError(provider._endpoint, 400, "unsupported", {}, io.BytesIO(b"{}")),
            _Response([b'data: {"choices":[{"delta":{"content":"hello"}}]}\n', b"data: [DONE]\n"]),
        ]
        self.addCleanup(calls[0].close)
        with patch("app.providers.openai_compatible_provider.urlopen", side_effect=calls):
            with self.assertLogs("insightagent.llm", level="INFO") as logs:
                self.assertEqual(list(provider.stream_generate("private prompt")), ["hello"])

        events = [json.loads(line.split(":", 2)[2]) for line in logs.output]
        self.assertEqual([event["outcome"] for event in events], ["compat_retry", "success"])
        self.assertEqual([event["status_family"] for event in events], ["4xx", "2xx"])
        summary = summarize(json.dumps(event) for event in events)
        self.assertEqual(summary["total_attempts"], 2)
        self.assertEqual(summary["by_outcome"], {"compat_retry": 1, "success": 1})

    def test_provider_attempt_records_early_stream_close_once(self) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="model", provider="provider", base_url="https://example.test/v1", api_key="key",
        )
        response = _Response([b'data: {"choices":[{"delta":{"content":"first"}}]}\n'])
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=response):
            with self.assertLogs("insightagent.llm", level="INFO") as logs:
                stream = provider.stream_generate("private prompt")
                self.assertEqual(next(stream), "first")
                stream.close()
        events = [json.loads(line.split(":", 2)[2]) for line in logs.output]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], "interrupted")

    def test_provider_attempt_summary_skips_other_events_and_private_fields(self) -> None:
        summary = summarize([
            '{"event":"http_request","route":"/private"}',
            '{"event":"llm_http_attempt","mode":"request","outcome":"http_response","status_family":"2xx","usage_available":false,"prompt":"private"}',
            "not json",
        ])
        self.assertEqual(summary["total_attempts"], 1)
        self.assertEqual(summary["malformed_lines"], 1)
        self.assertNotIn("private", json.dumps(summary))
