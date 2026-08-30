from __future__ import annotations

import json
from asyncio import CancelledError

from app.providers.base import ProviderCallError

from .context import (
    SimpleNamespace,
    StaticToolRegistryProvider,
    ToolRegistration,
    chat_execution_module,
)


class ProductionReliabilityFailurePathsMixin:
    def test_production_reliability_sse_error_payload_includes_safe_diagnostic_summary(
        self,
    ) -> None:
        payload = chat_execution_module.sse_error_payload(
            task_id="task-runtime-diagnostic",
            message="Remote provider upstream error (HTTP 503).",
            code="remote_provider_upstream_error",
            fatal=False,
            retry_count=2,
            detail="upstream request failed with Authorization Bearer secret-token",
            status_code=503,
        )

        self.assertEqual(payload["task_id"], "task-runtime-diagnostic")
        self.assertEqual(payload["code"], "remote_provider_upstream_error")
        self.assertEqual(payload["fatal"], False)
        self.assertEqual(payload["retryable"], True)
        self.assertEqual(payload["retryCount"], 2)
        self.assertEqual(payload["status_code"], 503)
        self.assertEqual(
            payload["diagnostic"],
            {
                "category": "remote_provider",
                "reason": "upstream",
                "recoverability": "retryable",
                "http_status_family": "5xx",
                "has_detail": True,
            },
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_production_reliability_sse_error_payload_classifies_safe_reason(
        self,
    ) -> None:
        cases = [
            (
                "remote_provider_network_error",
                False,
                None,
                "network",
            ),
            (
                "remote_api_key_unauthorized",
                True,
                401,
                "auth",
            ),
            (
                "remote_provider_rate_limited",
                False,
                429,
                "rate_limit",
            ),
            (
                "remote_provider_upstream_error",
                False,
                503,
                "upstream",
            ),
            (
                "task_timeout",
                True,
                None,
                "timeout",
            ),
            (
                "task_cancelled",
                True,
                None,
                "cancelled",
            ),
        ]

        for code, fatal, status_code, expected_reason in cases:
            with self.subTest(code=code):
                payload = chat_execution_module.sse_error_payload(
                    task_id=f"task-{code}",
                    message="safe message",
                    code=code,
                    fatal=fatal,
                    detail="safe detail",
                    status_code=status_code,
                )

                self.assertEqual(
                    payload["diagnostic"]["reason"],  # type: ignore[index]
                    expected_reason,
                )

    def _exercise_provider_start_failure(
        self,
        error: BaseException,
        *,
        task_id: str,
        session_id: str,
        user_id: str,
    ) -> tuple[
        list[dict[str, object]],
        list[dict[str, object]],
        list[str],
        list[dict[str, object]],
    ]:
        complete_calls: list[dict[str, object]] = []
        audits: list[dict[str, object]] = []
        released_slots: list[str] = []

        class FailingProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                raise error
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
            def fake_get_llm_provider(_user_id: str):
                if isinstance(error, chat_execution_module.ProviderSelectionError):
                    raise error
                return FailingProvider()

            chat_execution_module.get_llm_provider = fake_get_llm_provider
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
                    "id": task_id,
                    "session_id": session_id,
                    "status": "running",
                }
            )
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = (
                lambda **kwargs: complete_calls.append(dict(kwargs)) or 1
            )
            chat_execution_module.safe_record_audit_event = (
                lambda **kwargs: audits.append(dict(kwargs))
            )

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id=task_id,
                    session_id=session_id,
                    user_id=user_id,
                    prompt="provider failure should be diagnosed",
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

        error_payloads = [
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: error\n")
        ]
        return complete_calls, audits, released_slots, error_payloads

    def test_production_reliability_provider_failure_audit_includes_safe_reason(
        self,
    ) -> None:
        complete_calls, audits, released_slots, error_payloads = (
            self._exercise_provider_start_failure(
                ProviderCallError(
                    code="remote_provider_http_error",
                    user_message="Remote provider rate limited the request.",
                    detail=(
                        "HTTP 429 from provider_source='primary-search' "
                        "with Authorization Bearer secret-token"
                    ),
                    status_code=429,
                    retryable=True,
                ),
                task_id="task-provider-audit-diagnostic",
                session_id="session-provider-audit-diagnostic",
                user_id="user-provider-audit-diagnostic",
            )
        )
        expected_diagnostic = {
            "category": "remote_provider",
            "reason": "rate_limit",
            "recoverability": "retryable",
            "http_status_family": "4xx",
            "has_detail": True,
        }
        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["failed"],
        )
        self.assertEqual(released_slots, ["released"])
        self.assertEqual([audit["event_type"] for audit in audits], ["task_failed"])
        audit_detail = audits[-1]["detail"]
        self.assertEqual(audit_detail["status_code"], 429)
        self.assertEqual(audit_detail["retryable"], True)
        self.assertEqual(audit_detail["diagnostic"], expected_diagnostic)
        self.assertEqual(error_payloads[-1]["diagnostic"], expected_diagnostic)

        serialized_audit = json.dumps(audit_detail, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized_audit)
        self.assertNotIn("secret-token", serialized_audit)

    def test_production_reliability_provider_selection_audit_includes_safe_reason(
        self,
    ) -> None:
        complete_calls, audits, released_slots, error_payloads = (
            self._exercise_provider_start_failure(
                chat_execution_module.ProviderSelectionError(
                    code="remote_api_key_required",
                    user_message="Remote mode requires an API key.",
                ),
                task_id="task-provider-selection-diagnostic",
                session_id="session-provider-selection-diagnostic",
                user_id="user-provider-selection-diagnostic",
            )
        )
        expected_diagnostic = {
            "category": "remote_provider",
            "reason": "auth",
            "recoverability": "fatal",
            "http_status_family": None,
            "has_detail": False,
        }
        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["failed"],
        )
        self.assertEqual(released_slots, ["released"])
        self.assertEqual([audit["event_type"] for audit in audits], ["task_failed"])
        audit_detail = audits[-1]["detail"]
        self.assertEqual(audit_detail["diagnostic"], expected_diagnostic)
        self.assertEqual(error_payloads[-1]["diagnostic"], expected_diagnostic)

    def test_production_reliability_tool_terminal_return_lost_race_emits_cancelled(
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
                yield "should not reach final provider"

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
        original_execute_service_execution = (
            chat_execution_module.execute_tool_plan_item_service_execution
        )
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_release_slot = chat_execution_module.release_task_execution_slot
        original_mark_running = chat_execution_module.mark_task_running_started
        original_get_task = chat_execution_module.get_task
        original_update_trace = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event

        complete_attempted = {"value": False}
        registry_provider = StaticToolRegistryProvider(
            {
                "terminal_tool": ToolRegistration(
                    name="terminal_tool",
                    kind="action",
                    label="Terminal Tool",
                    retryable_by_default=False,
                    default_timeout_ms=1000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda **_kwargs: {},
                )
            }
        )

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
            )
            chat_execution_module.get_stored_settings = lambda _user_id: None
            chat_execution_module.get_llm_provider = lambda _user_id: FakeProvider()
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda **_kwargs: registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                lambda *args, **kwargs: SimpleNamespace(
                    tool_plan=[{"name": "terminal_tool", "input": {}}],
                    planning_prompt=None,
                    provider_usage=None,
                    planning_provider_attempted=False,
                    planning_provider_used=False,
                    allowed_tool_names=("terminal_tool",),
                    allowed_tool_labels=("Terminal Tool",),
                )
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                lambda **_kwargs: {
                    "provider": registry_provider,
                    "provider_source_name": "default",
                }
            )

            def fake_execute_tool_plan_item_service_execution(**_kwargs):
                yield {
                    "kind": "result",
                    "result": {
                        "service_actions": [
                            {
                                "kind": "complete_task",
                                "kwargs": {
                                    "task_id": "task-tool-cancel-race",
                                    "trace_steps": [],
                                    "user_id": "user-tool-cancel-race",
                                    "status": "failed",
                                },
                            },
                            {
                                "kind": "record_failure_event",
                                "kwargs": {
                                    "event_type": "task_failed",
                                    "code": "tool_failed",
                                    "message": "Tool failed after user cancellation.",
                                },
                            },
                            {
                                "kind": "emit_state",
                                "event": "state",
                                "data": {
                                    "task_id": "task-tool-cancel-race",
                                    "phase": "error",
                                },
                            },
                            {"kind": "return"},
                        ],
                    },
                }

            chat_execution_module.execute_tool_plan_item_service_execution = (
                fake_execute_tool_plan_item_service_execution
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
                    "id": "task-tool-cancel-race",
                    "session_id": "session-tool-cancel-race",
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
                    task_id="task-tool-cancel-race",
                    session_id="session-tool-cancel-race",
                    user_id="user-tool-cancel-race",
                    prompt="cancel wins over terminal tool return",
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
            chat_execution_module.execute_tool_plan_item_service_execution = (
                original_execute_service_execution
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
        self.assertEqual(error_payloads[-1]["code"], "task_cancelled")
        self.assertFalse(any(audit["event_type"] == "task_failed" for audit in audits))

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

    def _exercise_running_stream_base_exception(
        self,
        stream_exception: BaseException,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
        complete_calls: list[dict[str, object]] = []
        audits: list[dict[str, object]] = []
        released_slots: list[str] = []

        class InterruptedProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                raise stream_exception
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

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-interrupted",
                task_execution_heartbeat_interval_sec=0.0,
                usage_prompt_token_price_per_1k=0.0,
                usage_completion_token_price_per_1k=0.0,
            )
            chat_execution_module.get_stored_settings = lambda _user_id: None
            chat_execution_module.get_llm_provider = lambda _user_id: InterruptedProvider()
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
                    "id": "task-stream-interrupted",
                    "session_id": "session-stream-interrupted",
                    "status": "running",
                }
            )
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = (
                lambda **kwargs: complete_calls.append(dict(kwargs)) or 1
            )
            chat_execution_module.safe_record_audit_event = (
                lambda **kwargs: audits.append(dict(kwargs))
            )

            with self.assertRaises(type(stream_exception)):
                list(
                    chat_execution_module.stream_task_execution(
                        task_id="task-stream-interrupted",
                        session_id="session-stream-interrupted",
                        user_id="user-stream-interrupted",
                        prompt="client disconnect during provider stream",
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

        return complete_calls, audits, released_slots

    def test_production_reliability_client_stream_close_preserves_running_for_reconnect(
        self,
    ) -> None:
        complete_calls, audits, released_slots = (
            self._exercise_running_stream_base_exception(GeneratorExit())
        )
        self.assertEqual(released_slots, ["released"])
        self.assertEqual(complete_calls, [])
        self.assertEqual(audits, [])

    def test_production_reliability_server_stream_cancel_marks_running_failed(
        self,
    ) -> None:
        complete_calls, audits, released_slots = (
            self._exercise_running_stream_base_exception(CancelledError())
        )
        self.assertEqual(released_slots, ["released"])
        self.assertEqual(
            [call.get("status", "completed") for call in complete_calls],
            ["failed"],
        )
        self.assertEqual(
            complete_calls[-1].get("execution_owner_id"),
            "instance-interrupted",
        )
        self.assertEqual([audit["event_type"] for audit in audits], ["task_failed"])
        self.assertEqual(audits[-1]["detail"]["code"], "task_stream_interrupted")
        self.assertEqual(
            audits[-1]["detail"]["diagnostic"],
            {
                "category": "task_stream",
                "reason": "stream",
                "recoverability": "fatal",
                "http_status_family": None,
                "has_detail": False,
            },
        )

    def test_production_reliability_stream_close_before_running_does_not_mark_failed(
        self,
    ) -> None:
        complete_calls: list[dict[str, object]] = []
        forgotten_waiters: list[str] = []

        original_get_settings = chat_execution_module.get_settings
        original_create_message = chat_execution_module.create_message
        original_try_acquire = chat_execution_module.try_acquire_task_execution_slot
        original_forget_waiting = chat_execution_module.forget_waiting_task
        original_mark_queued = chat_execution_module.mark_task_queued_waiting
        original_get_task = chat_execution_module.get_task
        original_complete_task = chat_execution_module.complete_task
        original_safe_audit = chat_execution_module.safe_record_audit_event
        original_sleep = chat_execution_module.sleep

        try:
            chat_execution_module.get_settings = lambda: SimpleNamespace(
                trace_persist_min_interval_sec=0.0,
                task_timeout_sec=60.0,
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.01,
                task_execution_owner_id="instance-before-running",
                task_execution_heartbeat_interval_sec=0.0,
            )
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_acquire_task_execution_slot = (
                lambda **_kwargs: None
            )
            chat_execution_module.forget_waiting_task = (
                lambda task_id: forgotten_waiters.append(task_id)
            )
            chat_execution_module.mark_task_queued_waiting = (
                lambda *args, **kwargs: 1
            )
            chat_execution_module.get_task = (
                lambda *args, **kwargs: {
                    "id": "task-close-before-running",
                    "session_id": "session-close-before-running",
                    "status": "pending",
                }
            )
            chat_execution_module.complete_task = (
                lambda **kwargs: complete_calls.append(dict(kwargs)) or 1
            )
            chat_execution_module.safe_record_audit_event = lambda **_kwargs: None
            chat_execution_module.sleep = lambda _seconds: None

            stream = chat_execution_module.stream_task_execution(
                task_id="task-close-before-running",
                session_id="session-close-before-running",
                user_id="user-close-before-running",
                prompt="disconnect before slot acquisition",
            )
            first_event = next(stream)
            self.assertTrue(first_event.startswith("event: state\n"))
            stream.close()
        finally:
            chat_execution_module.get_settings = original_get_settings
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_acquire_task_execution_slot = original_try_acquire
            chat_execution_module.forget_waiting_task = original_forget_waiting
            chat_execution_module.mark_task_queued_waiting = original_mark_queued
            chat_execution_module.get_task = original_get_task
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.safe_record_audit_event = original_safe_audit
            chat_execution_module.sleep = original_sleep

        self.assertEqual(forgotten_waiters, ["task-close-before-running"])
        self.assertEqual(complete_calls, [])
