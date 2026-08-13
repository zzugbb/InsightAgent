from __future__ import annotations

import json

from app.providers.base import ProviderCallError

from .context import SimpleNamespace, chat_execution_module


class ProductionReliabilityFailurePathsMixin:
    def test_production_reliability_timeout_lost_race_emits_cancelled_terminal(
        self,
    ) -> None:
        complete_calls: list[dict[str, object]] = []
        audits: list[dict[str, object]] = []
        released_slots: list[str] = []

        class FakeProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                yield "should not stream after timeout"

        class FakeSlot:
            def release(self) -> None:
                released_slots.append("released")

        original_get_settings = chat_execution_module.get_settings
        original_get_stored_settings = chat_execution_module.get_stored_settings
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_mark_running = chat_execution_module.mark_task_running_started
        original_get_task = chat_execution_module.get_task
        original_update_trace = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event
        original_monotonic = chat_execution_module.monotonic

        complete_attempted = {"value": False}
        monotonic_values = iter([0.0, 0.1, 0.2, 0.3, 0.4, 2.0, 2.1, 2.2])

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=1.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-a",
                task_execution_heartbeat_interval_sec=0.0,
            )
            chat_execution_module.get_stored_settings = lambda _user_id: None
            chat_execution_module.get_llm_provider = lambda _user_id: FakeProvider()
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda **_kwargs: SimpleNamespace()
            )
            chat_execution_module.build_tool_plan_artifacts = (
                lambda *args, **kwargs: SimpleNamespace(
                    tool_plan=[],
                    planning_prompt=None,
                    provider_usage=None,
                    planning_provider_attempted=False,
                    planning_provider_used=False,
                    allowed_tool_names=(),
                    allowed_tool_labels=(),
                )
            )
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: FakeSlot()
            )
            chat_execution_module.release_task_execution_slot = lambda _task_id: None
            chat_execution_module.mark_task_running_started = (
                lambda *args, **kwargs: 1
            )
            chat_execution_module.get_task = (
                lambda *args, **kwargs: {
                    "id": "task-timeout-cancel-race",
                    "session_id": "session-timeout-cancel-race",
                    "status": "cancelled" if complete_attempted["value"] else "running",
                }
            )
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None

            def fake_complete_task(**kwargs):
                complete_attempted["value"] = True
                complete_calls.append(dict(kwargs))
                return 0

            chat_execution_module.complete_task = fake_complete_task
            chat_execution_module.safe_record_audit_event = (
                lambda **kwargs: audits.append(dict(kwargs))
            )
            chat_execution_module.monotonic = (
                lambda: next(monotonic_values, 2.3)
            )

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-timeout-cancel-race",
                    session_id="session-timeout-cancel-race",
                    user_id="user-timeout-cancel-race",
                    prompt="cancel wins over timeout",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_plan_artifacts
            )
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.release_task_execution_slot = original_release_slot
            chat_execution_module.mark_task_running_started = original_mark_running
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_trace
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.safe_record_audit_event = original_safe_audit
            chat_execution_module.monotonic = original_monotonic

        event_names = [
            event.split("\n", 1)[0].replace("event: ", "")
            for event in events
            if event.startswith("event: ")
        ]
        error_payloads = [
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: error\n")
        ]
        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["timed_out", "cancelled"],
        )
        self.assertEqual(released_slots, ["released"])
        self.assertIn("cancelled", event_names)
        self.assertNotIn("timeout", event_names)
        self.assertEqual(error_payloads[-1]["code"], "task_cancelled")
        self.assertFalse(
            any(audit["event_type"] == "task_timeout" for audit in audits)
        )

    def test_production_reliability_provider_failure_lost_race_emits_cancelled_terminal(
        self,
    ) -> None:
        complete_calls: list[dict[str, object]] = []
        audits: list[dict[str, object]] = []
        released_slots: list[str] = []

        class FailingProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                raise ProviderCallError(
                    code="provider_down",
                    user_message="Provider failed after user cancellation.",
                    status_code=503,
                    retryable=True,
                )
                yield ""

        class FakeSlot:
            def release(self) -> None:
                released_slots.append("released")

        original_get_settings = chat_execution_module.get_settings
        original_get_stored_settings = chat_execution_module.get_stored_settings
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_mark_running = chat_execution_module.mark_task_running_started
        original_get_task = chat_execution_module.get_task
        original_update_trace = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event

        complete_attempted = {"value": False}

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-a",
                task_execution_heartbeat_interval_sec=0.0,
                usage_prompt_token_price_per_1k=0.0,
                usage_completion_token_price_per_1k=0.0,
            )
            chat_execution_module.get_stored_settings = lambda _user_id: None
            chat_execution_module.get_llm_provider = lambda _user_id: FailingProvider()
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda **_kwargs: SimpleNamespace()
            )
            chat_execution_module.build_tool_plan_artifacts = (
                lambda *args, **kwargs: SimpleNamespace(
                    tool_plan=[],
                    planning_prompt=None,
                    provider_usage=None,
                    planning_provider_attempted=False,
                    planning_provider_used=False,
                    allowed_tool_names=(),
                    allowed_tool_labels=(),
                )
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                lambda **_kwargs: {
                    "provider": SimpleNamespace(),
                    "provider_source_name": "default",
                }
            )
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: FakeSlot()
            )
            chat_execution_module.release_task_execution_slot = lambda _task_id: None
            chat_execution_module.mark_task_running_started = (
                lambda *args, **kwargs: 1
            )
            chat_execution_module.get_task = (
                lambda *args, **kwargs: {
                    "id": "task-provider-cancel-race",
                    "session_id": "session-provider-cancel-race",
                    "status": "cancelled" if complete_attempted["value"] else "running",
                }
            )
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None

            def fake_complete_task(**kwargs):
                complete_attempted["value"] = True
                complete_calls.append(dict(kwargs))
                return 0

            chat_execution_module.complete_task = fake_complete_task
            chat_execution_module.safe_record_audit_event = (
                lambda **kwargs: audits.append(dict(kwargs))
            )

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-provider-cancel-race",
                    session_id="session-provider-cancel-race",
                    user_id="user-provider-cancel-race",
                    prompt="cancel wins over provider failure",
                )
            )
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.release_task_execution_slot = original_release_slot
            chat_execution_module.mark_task_running_started = original_mark_running
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_trace
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.safe_record_audit_event = original_safe_audit

        event_names = [
            event.split("\n", 1)[0].replace("event: ", "")
            for event in events
            if event.startswith("event: ")
        ]
        error_payloads = [
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: error\n")
        ]
        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["failed", "cancelled"],
        )
        self.assertEqual(released_slots, ["released"])
        self.assertIn("cancelled", event_names)
        self.assertNotIn("provider_down", [payload["code"] for payload in error_payloads])
        self.assertEqual(error_payloads[-1]["code"], "task_cancelled")
        self.assertFalse(any(audit["event_type"] == "task_failed" for audit in audits))
