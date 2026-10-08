"""Completion signals, partial EOF and accounting for compatible HTTP streams."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from app.providers.base import ProviderCallError
from app.providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.providers.response_utils import extract_response_delta_text
from tool_runtime_slice.provider_call_observability import _Response


def chunk(**fields):
    return ("data: " + json.dumps(fields) + "\n").encode()


TEXT = chunk(choices=[{"delta": {"content": "private partial answer"}}])


class ProviderStreamCompletionMixin:
    def test_provider_stream_completion_metadata_frames_have_no_text(self):
        for choices in ([], None, [{"delta": {}}], [{"delta": {"role": "assistant"}}], [{"finish_reason": "stop"}]):
            with self.subTest(choices=choices):
                self.assertEqual(extract_response_delta_text({"choices": choices}), "")

    def test_provider_stream_completion_typed_empty_delta_does_not_recurse(self):
        frame = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))])
        self.assertEqual(extract_response_delta_text(frame), "")
        frame.choices[0].delta.content = "typed text"
        self.assertEqual(extract_response_delta_text(frame), "typed text")

    def test_provider_stream_completion_empty_choices_preserve_top_level_delta(self):
        self.assertEqual(extract_response_delta_text({"choices": [], "delta": {"content": "fallback text"}}), "fallback text")

    def stream_provider(self):
        return OpenAICompatibleLLMProvider(
            model="private-model", provider="private-provider",
            base_url="https://private.example/v1", api_key="secret-key",
        )

    def test_provider_stream_completion_partial_eof_fails_without_replay(self):
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([TEXT])) as request:
            with self.assertLogs("insightagent.llm", level="INFO") as logs:
                stream = self.stream_provider().stream_generate("private prompt")
                self.assertEqual(next(stream), "private partial answer")
                with self.assertRaises(ProviderCallError) as error:
                    next(stream)
        self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")
        self.assertTrue(error.exception.retryable)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(len(logs.output), 1)
        self.assertEqual(json.loads(logs.output[0].split(":", 2)[2])["outcome"], "interrupted")
        for secret in ("private", "secret-key", "partial answer"):
            self.assertNotIn(secret, logs.output[0])

    def test_provider_stream_completion_done_marker_accepts_text(self):
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([TEXT, b"data: [DONE]\n"])):
            self.assertEqual(list(self.stream_provider().stream_generate("prompt")), ["private partial answer"])

    def test_provider_stream_completion_terminal_reason_accepts_eof_and_trailing_usage(self):
        for reason in ("stop", "length", "tool_calls", "content_filter", "function_call"):
            with self.subTest(reason=reason):
                provider = self.stream_provider()
                lines = [TEXT, chunk(choices=[{"delta": {}, "finish_reason": reason}]),
                         chunk(choices=[], usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7})]
                with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response(lines)):
                    self.assertEqual(list(provider.stream_generate("prompt")), ["private partial answer"])
                self.assertEqual(provider.get_last_usage().total_tokens, 7)

    def test_provider_stream_completion_nonterminal_reason_does_not_accept_eof(self):
        for reason in (None, "", "unknown", True, ["stop"]):
            with self.subTest(reason=reason):
                lines = [TEXT, chunk(choices=[{"delta": {}, "finish_reason": reason}])]
                with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response(lines)):
                    with self.assertRaises(ProviderCallError) as error:
                        list(self.stream_provider().stream_generate("prompt"))
                self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")

    def test_provider_stream_completion_other_choice_does_not_finish_selected_text(self):
        lines = [TEXT, chunk(choices=[{"finish_reason": None}, {"finish_reason": "stop"}])]
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response(lines)):
            with self.assertRaises(ProviderCallError) as error:
                list(self.stream_provider().stream_generate("prompt"))
        self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")

    def test_provider_stream_completion_usage_does_not_replace_terminal_signal(self):
        provider = self.stream_provider()
        lines = [TEXT, chunk(choices=[], usage={"total_tokens": 7})]
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response(lines)):
            with self.assertRaises(ProviderCallError) as error:
                list(provider.stream_generate("prompt"))
        self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")
        self.assertEqual(provider.get_last_usage().total_tokens, 7)

    def test_provider_stream_completion_empty_completed_stream_remains_empty_error(self):
        for terminal in (b"data: [DONE]\n", chunk(choices=[{"finish_reason": "stop"}])):
            with self.subTest(terminal=terminal):
                with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([terminal])):
                    with self.assertRaises(ProviderCallError) as error:
                        list(self.stream_provider().stream_generate("prompt"))
                self.assertEqual(error.exception.code, "remote_provider_empty_response")
                self.assertFalse(error.exception.retryable)

    def test_provider_stream_completion_empty_unfinished_stream_is_interrupted(self):
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([b": heartbeat\n"])):
            with self.assertRaises(ProviderCallError) as error:
                list(self.stream_provider().stream_generate("prompt"))
        self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")

    def test_provider_stream_completion_transport_exception_after_finish_is_not_hidden(self):
        class BrokenResponse(_Response):
            def __iter__(self):
                yield TEXT
                yield chunk(choices=[{"finish_reason": "stop"}])
                raise OSError("connection lost")

        with patch("app.providers.openai_compatible_provider.urlopen", return_value=BrokenResponse([])):
            with self.assertRaises(ProviderCallError) as error:
                list(self.stream_provider().stream_generate("prompt"))
        self.assertEqual(error.exception.code, "remote_provider_stream_interrupted")
