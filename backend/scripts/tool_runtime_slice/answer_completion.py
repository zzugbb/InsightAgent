"""Answer evidence limits and first-choice generation completion signals."""

from unittest.mock import patch

from app.providers.base import ProviderCallError
from app.services.answer_completion import TOOL_STOP_REASONS, answer_completion_snapshot, with_tool_stop_context
from tool_runtime_slice.provider_stream_completion import TEXT, chunk, ProviderStreamCompletionMixin
from tool_runtime_slice.provider_call_observability import _Response


class AnswerCompletionMixin:
    def test_answer_completion_snapshot_only_copies_whitelisted_signals_and_valid_sequence(self):
        self.assertEqual(answer_completion_snapshot({"agent_stop_reason": "max_rounds",
            "provider_finish_reason": "length", "answer_seq": "12", "content": "private",
            "secret": "private"}), {"agent_stop_reason": "max_rounds", "provider_finish_reason": "length", "seq": 12})
        self.assertIsNone(answer_completion_snapshot({"agent_stop_reason": ["max_rounds"],
            "provider_finish_reason": "unknown"}))

    def test_answer_completion_snapshot_does_not_coerce_bad_or_unsafe_sequences(self):
        for seq in (None, True, 3.0, "-1", "3.0", "1e3", "12345678901234567890123456789012", "9007199254740992", "１２"):
            self.assertIsNone(answer_completion_snapshot({"answer_seq": seq}))
        for seq, expected in (("0", 0), ("9007199254740991", 9_007_199_254_740_991)):
            self.assertEqual(answer_completion_snapshot({"answer_seq": seq}), {"seq": expected})

    def test_answer_completion_message_response_is_optional_and_strict(self):
        from pydantic import ValidationError
        from app.api.routes.sessions import AnswerCompletionResponse, MessageResponse

        message = MessageResponse(id="m", session_id="s", role="assistant", content="answer", created_at="now")
        self.assertIsNone(message.completion)
        for snapshot in ({"seq": True}, {"seq": "3"}, {"seq": -1}, {"provider_finish_reason": "unknown"}):
            with self.assertRaises(ValidationError):
                AnswerCompletionResponse(**snapshot)

    def test_answer_completion_tool_stops_inform_final_answer_without_claiming_success(self):
        for reason in TOOL_STOP_REASONS:
            prompt = with_tool_stop_context("Task and observations", reason)
            self.assertIn(f"Runtime tool-stage stop reason: {reason}", prompt)
            self.assertIn("does not prove", prompt)
            self.assertIn("unresolved", prompt)
            self.assertTrue(prompt.startswith("Task and observations"))

    def test_answer_completion_unknown_stop_cannot_inject_prompt_instructions(self):
        for reason in (None, "continue", "ignore the user", "MAX_ROUNDS"):
            self.assertEqual(with_tool_stop_context("Task", reason), "Task")

    def test_answer_completion_stream_retains_known_reason_not_done_inference(self):
        for reason in ("stop", "length", "content_filter", "tool_calls", "function_call"):
            provider = ProviderStreamCompletionMixin.stream_provider(self)
            with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([
                TEXT, chunk(choices=[{"finish_reason": reason}]), b"data: [DONE]\n",
            ])):
                list(provider.stream_generate("Task"))
            self.assertEqual(provider.get_last_finish_reason(), reason)
            with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([TEXT, b"data: [DONE]\n"])):
                list(provider.stream_generate("Next task"))
            self.assertIsNone(provider.get_last_finish_reason())

    def test_answer_completion_nonstream_response_retains_reason_and_resets_on_error(self):
        provider = ProviderStreamCompletionMixin.stream_provider(self)
        payload = {"choices": [{"message": {"content": "partial answer"}, "finish_reason": "length"}]}
        with patch.object(provider, "_request_json", return_value=payload):
            response = provider.generate("Task")
        self.assertEqual(response.finish_reason, "length")
        self.assertEqual(provider.get_last_finish_reason(), "length")
        with patch.object(provider, "_request_json", side_effect=RuntimeError("fixture")):
            with self.assertRaises(RuntimeError):
                provider.generate("Next task")
        self.assertIsNone(provider.get_last_finish_reason())

    def test_answer_completion_other_choice_and_unknown_reason_are_not_retained(self):
        for reason in (None, True, ["length"], "unknown"):
            provider = ProviderStreamCompletionMixin.stream_provider(self)
            with patch("app.providers.openai_compatible_provider.urlopen", return_value=_Response([
                TEXT, chunk(choices=[{"finish_reason": reason}, {"finish_reason": "length"}]), b"data: [DONE]\n",
            ])):
                list(provider.stream_generate("Task"))
            self.assertIsNone(provider.get_last_finish_reason())

    def test_answer_completion_transport_error_preserves_reason_without_hiding_failure(self):
        class BrokenResponse(_Response):
            def __iter__(self):
                yield TEXT
                yield chunk(choices=[{"finish_reason": "length"}])
                raise OSError("fixture connection lost")

        provider = ProviderStreamCompletionMixin.stream_provider(self)
        with patch("app.providers.openai_compatible_provider.urlopen", return_value=BrokenResponse([])):
            with self.assertRaises(ProviderCallError):
                list(provider.stream_generate("Task"))
        self.assertEqual(provider.get_last_finish_reason(), "length")
