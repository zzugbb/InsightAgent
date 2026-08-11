from __future__ import annotations

from .context import *


class TaskTraceExportGovernanceMixin:
    def test_build_task_export_payload_surfaces_service_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance",
            "session_id": "session-export-governance",
            "prompt": "export governance summary",
            "status": "completed",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "planning_only",
                "provider_source": "default",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: [
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="trace-plan-1",
                        type="thought",
                        content="Planner constrained the tool set.",
                        seq=1,
                        meta={
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "default",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                    )
                ]
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "planning_only")
        self.assertEqual(payload.trace.governance.provider_source, "default")
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.trace.governance.allowed_tool_labels,
            ["Task Planner"],
        )

    def test_get_task_detail_surfaces_service_governance_summary(self) -> None:
        task = {
            "id": "task-response-service-governance",
            "session_id": "session-response-service-governance",
            "prompt": "task response service governance summary",
            "status": "completed",
            "created_at": "2026-06-09T10:00:00",
            "updated_at": "2026-06-09T10:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        }
        original_get_task = task_routes_module.get_task
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: task
            payload = task_routes_module.get_task_detail(
                "task-response-service-governance",
                current_user={"id": "user-response-service-governance"},
            )
        finally:
            task_routes_module.get_task = original_get_task

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profile, "planning_only")
        self.assertEqual(payload.governance.provider_source, "planning_suite")
        self.assertEqual(payload.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_get_task_detail_passes_raw_governance_dict_to_task_response(self) -> None:
        task = {
            "id": "task-response-raw-governance",
            "session_id": "session-response-raw-governance",
            "prompt": "task response raw governance summary",
            "status": "completed",
            "created_at": "2026-06-18T10:00:00",
            "updated_at": "2026-06-18T10:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        }
        original_get_task = task_routes_module.get_task
        original_task_response = task_routes_module.TaskResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: task
            task_routes_module.TaskResponse = lambda **kwargs: captured.append(kwargs) or kwargs  # type: ignore[assignment]
            task_routes_module.get_task_detail(
                "task-response-raw-governance",
                current_user={"id": "user-response-raw-governance"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.TaskResponse = original_task_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["governance"], task["governance"])

    def test_get_task_response_summary_from_task_plain_clones_governance_dict(
        self,
    ) -> None:
        class GuardedGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_task_response_summary_from_task should plain-clone governance dicts before outward model validation"
                )

        guarded_governance = GuardedGovernanceDict(
            profile="planning_only",
            provider_source="planning_suite",
            allowed_tool_names=["task_plan"],
            allowed_tool_labels=["Task Planner Suite"],
        )
        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-with-status-governance",
                "session_id": "session-with-status-governance",
                "prompt": "task response helper governance",
                "status": "completed",
                "created_at": "2026-06-22T18:00:00",
                "updated_at": "2026-06-22T18:01:00",
                "governance": guarded_governance,
            }
        )

        self.assertEqual(payload["id"], "task-with-status-governance")
        self.assertEqual(payload["status_normalized"], "completed")
        self.assertEqual(payload["status_label"], "Completed")
        self.assertIsInstance(payload["governance"], dict)
        self.assertNotIsInstance(payload["governance"], GuardedGovernanceDict)
        self.assertEqual(payload["governance"], dict(guarded_governance))

    def test_get_task_response_summary_from_task_coerces_governance_models(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        governance = ResponseReadyGovernance(
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-with-model-governance",
                "session_id": "session-with-model-governance",
                "prompt": "task response helper governance model",
                "status": "completed",
                "created_at": "2026-06-22T18:00:00",
                "updated_at": "2026-06-22T18:01:00",
                "governance": governance,
            }
        )

        self.assertIsInstance(payload["governance"], dict)
        self.assertIsNot(payload["governance"], governance)
        self.assertEqual(payload["governance"]["profile"], "planning_only")

    def test_get_task_response_summary_from_task_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-with-model-governance-source-context",
                "session_id": "session-with-model-governance-source-context",
                "prompt": "task response helper governance source context",
                "status": "completed",
                "created_at": "2026-06-22T18:00:00",
                "updated_at": "2026-06-22T18:01:00",
                "governance": ResponseReadyGovernance(
                    {
                        "profile": "calculator_only",
                        "provider_source": "calculator_suite",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    }
                ),
            }
        )

        self.assertEqual(
            payload["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_task_response_summary_from_task_shares_provider_source_aliases_with_trace_json(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "task-response-trace-source-alias",
                    "type": "action",
                    "content": "Planner used provider source",
                    "seq": 1,
                    "meta": {
                        "tool_registry_provider_source": "suite_access_token=two",
                        "provider_sources": ["suite_api_key=one"],
                    },
                }
            ]
        )

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-shared-source-alias",
                "session_id": "session-response-shared-source-alias",
                "prompt": "response shared provider source alias",
                "status": "completed",
                "trace_json": trace_json,
                "usage_json": None,
                "created_at": "2026-08-11T10:00:00",
                "updated_at": "2026-08-11T10:01:00",
                "governance": {
                    "profile": "planning_only",
                    "provider_source": "suite_api_key=one",
                },
            }
        )

        trace_steps = json.loads(str(payload["trace_json"]))

        self.assertEqual(
            payload["governance"]["provider_source"],
            "suite_[redacted]#1",
        )
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry_provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(
            trace_steps[0]["meta"]["provider_sources"],
            ["suite_[redacted]#1"],
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("api_key=one", serialized)
        self.assertNotIn("access_token=two", serialized)

    def test_get_task_trace_response_summary_from_task_shares_provider_source_aliases_across_steps(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "trace-response-source-alias-1",
                    "type": "action",
                    "content": "First provider source",
                    "seq": 1,
                    "meta": {
                        "tool_registry_provider_source": "suite_api_key=one",
                    },
                },
                {
                    "id": "trace-response-source-alias-2",
                    "type": "action",
                    "content": "Second provider source",
                    "seq": 2,
                    "meta": {
                        "tool_registry_provider_source": "suite_access_token=two",
                        "provider_sources": ["suite_api_key=one"],
                    },
                },
            ]
        )

        payload = chat_persistence_module.get_task_trace_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-trace-response-shared-source-alias",
                "session_id": "session-trace-response-shared-source-alias",
                "prompt": "trace response shared source alias",
                "status": "completed",
                "trace_json": trace_json,
            }
        )

        step_meta = [step.meta.model_dump() for step in payload["steps"]]

        self.assertEqual(
            step_meta[0]["tool_registry_provider_source"],
            "suite_[redacted]#1",
        )
        self.assertEqual(
            step_meta[1]["tool_registry_provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(step_meta[1]["provider_sources"], ["suite_[redacted]#1"])
        serialized = json.dumps(
            [step.model_dump() for step in payload["steps"]],
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=one", serialized)
        self.assertNotIn("access_token=two", serialized)

    def test_get_task_trace_delta_response_summary_from_task_shares_provider_source_aliases_across_steps(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "trace-delta-source-alias-1",
                    "type": "action",
                    "content": "First provider source",
                    "seq": 1,
                    "meta": {
                        "tool_registry_provider_source": "suite_api_key=one",
                    },
                },
                {
                    "id": "trace-delta-source-alias-2",
                    "type": "action",
                    "content": "Second provider source",
                    "seq": 2,
                    "meta": {
                        "tool_registry_provider_source": "suite_access_token=two",
                        "provider_sources": ["suite_api_key=one"],
                    },
                },
            ]
        )

        payload = chat_persistence_module.get_task_trace_delta_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-trace-delta-shared-source-alias",
                "session_id": "session-trace-delta-shared-source-alias",
                "prompt": "trace delta shared source alias",
                "status": "running",
                "trace_json": trace_json,
            },
            after_seq=0,
            limit=10,
        )

        step_meta = [step.meta.model_dump() for step in payload["steps"]]

        self.assertEqual(
            step_meta[0]["tool_registry_provider_source"],
            "suite_[redacted]#1",
        )
        self.assertEqual(
            step_meta[1]["tool_registry_provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(step_meta[1]["provider_sources"], ["suite_[redacted]#1"])
        serialized = json.dumps(
            [step.model_dump() for step in payload["steps"]],
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=one", serialized)
        self.assertNotIn("access_token=two", serialized)

    def test_get_task_response_summary_from_task_accepts_model_dump_row(self) -> None:
        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-response-model-row",
                    "session_id": "session-response-model-row",
                    "prompt": "response model row",
                    "status": "completed",
                    "created_at": "2026-07-02T15:30:00",
                    "updated_at": "2026-07-02T15:31:00",
                    "governance": {"profile": "planning_only"},
                }

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            TaskRowPayload()
        )

        self.assertEqual(payload["id"], "task-response-model-row")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["governance"], {"profile": "planning_only"})

    def test_get_task_response_summary_from_task_sanitizes_http_json_trace_json(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "task-response-trace-http-json",
                    "type": "action",
                    "content": (
                        'Tool done: Provider Status Preview: {"status":"ready",'
                        '"message":"gateway token=hidden",'
                        '"access_token":"hidden",'
                        '"request_id":"Bearer secret-token"}'
                    ),
                    "seq": 8,
                    "meta": {
                        "tool": {
                            "name": "provider_status",
                            "label": "Provider Status",
                            "execution_kind": "http_json",
                            "status": "done",
                            "effective_result_preview_keys": ["status", "message"],
                            "output_preview": {
                                "status": "ready",
                                "message": "gateway token=hidden",
                                "access_token": "hidden",
                                "request_id": "Bearer secret-token",
                            },
                        }
                    },
                }
            ]
        )

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-trace-json-safe",
                "session_id": "session-response-trace-json-safe",
                "prompt": "response trace json safe",
                "status": "completed",
                "trace_json": trace_json,
                "usage_json": None,
                "created_at": "2026-07-16T10:00:00",
                "updated_at": "2026-07-16T10:01:00",
            }
        )

        serialized = str(payload["trace_json"])
        parsed = json.loads(serialized)

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("gateway token=[redacted]", parsed[0]["content"])
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_response_summary_from_task_redacts_plain_wrapped_trace_json(
        self,
    ) -> None:
        trace_json = UserString(
            "bad trace payload Provider Search [provider_search via http_json] "
            "response_path=$.data.access_token Bearer secret-token"
        )

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": UserString("task-response-wrapped-trace-json-safe"),
                "session_id": UserString("session-response-wrapped-trace-json-safe"),
                "prompt": UserString("response wrapped trace json safe"),
                "status": UserString("failed"),
                "trace_json": trace_json,
                "usage_json": None,
                "created_at": UserString("2026-07-23T10:00:00"),
                "updated_at": UserString("2026-07-23T10:01:00"),
            }
        )

        serialized_payload = json.dumps(payload, ensure_ascii=False)
        serialized_trace = str(payload["trace_json"])

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("[redacted]", serialized_trace)
        self.assertNotIn("UserString", serialized_payload)
        self.assertNotIn("response_path=$.data.access_token", serialized_trace)
        self.assertNotIn("access_token", serialized_trace)
        self.assertNotIn("Bearer", serialized_trace)
        self.assertNotIn("secret-token", serialized_trace)

    def test_get_task_response_summary_from_task_normalizes_plain_wrapped_usage_json(
        self,
    ) -> None:
        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": UserString("task-response-wrapped-usage-json-safe"),
                "session_id": UserString("session-response-wrapped-usage-json-safe"),
                "prompt": UserString("response wrapped usage json safe"),
                "status": UserString("completed"),
                "trace_json": None,
                "usage_json": UserString('{"total_tokens": 12}'),
                "created_at": UserString("2026-07-23T10:02:00"),
                "updated_at": UserString("2026-07-23T10:03:00"),
            }
        )

        serialized_payload = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(payload["usage_json"], '{"total_tokens": 12}')
        self.assertNotIn("UserString", serialized_payload)

    def test_get_task_response_summary_from_task_redacts_http_json_trace_json_label_only_url(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "task-response-trace-http-json-label-only-url",
                    "type": "action",
                    "content": (
                        "Calculator [calculator via http_json]: callback "
                        "https://provider.example/cb?"
                        "access_token=secret-token&state=ok"
                        "#client_secret=hidden"
                    ),
                    "seq": 9,
                    "meta": {
                        "label": "Calculator [calculator via http_json]",
                    },
                }
            ]
        )

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-trace-json-label-only-url-safe",
                "session_id": "session-response-trace-json-label-only-url-safe",
                "prompt": "response trace json label-only safe",
                "status": "completed",
                "trace_json": trace_json,
                "usage_json": None,
                "created_at": "2026-07-20T11:00:00",
                "updated_at": "2026-07-20T11:01:00",
            }
        )

        serialized = str(payload["trace_json"])
        parsed = json.loads(serialized)

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("callback", parsed[0]["content"])
        self.assertIn("[redacted]", parsed[0]["content"])
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_response_summary_from_task_redacts_http_json_trace_json_tool_label_diagnostics(
        self,
    ) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "task-response-trace-http-json-tool-label-diagnostic",
                    "type": "action",
                    "content": 'Tool done: Provider Status Preview: {"message":"ok"}',
                    "seq": 10,
                    "meta": {
                        "tool": {
                            "name": "provider_status",
                            "label": (
                                "Provider token=hidden "
                                "https://provider.example/cb?"
                                "access_token=secret-token"
                            ),
                            "execution_kind": "http_json",
                            "status": "done",
                            "output_preview": {"message": "ok"},
                        }
                    },
                }
            ]
        )

        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-trace-json-tool-label-safe",
                "session_id": "session-response-trace-json-tool-label-safe",
                "prompt": "response trace json tool label safe",
                "status": "completed",
                "trace_json": trace_json,
                "usage_json": None,
                "created_at": "2026-07-20T11:02:00",
                "updated_at": "2026-07-20T11:03:00",
            }
        )

        serialized = str(payload["trace_json"])
        parsed = json.loads(serialized)

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("[redacted]", parsed[0]["meta"]["tool"]["label"])
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_response_summary_from_task_redacts_unparseable_trace_json(
        self,
    ) -> None:
        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-bad-trace-json-safe",
                "session_id": "session-response-bad-trace-json-safe",
                "prompt": "response bad trace json safe",
                "status": "failed",
                "trace_json": (
                    "bad trace payload provider_status token=hidden "
                    "query_params.access_token Bearer secret-token"
                ),
                "usage_json": None,
                "created_at": "2026-07-16T10:02:00",
                "updated_at": "2026-07-16T10:03:00",
            }
        )

        serialized = str(payload["trace_json"])

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_response_summary_from_task_redacts_unparseable_trace_json_mixed_jsonpath(
        self,
    ) -> None:
        payload = chat_persistence_module.get_task_response_summary_from_task(  # type: ignore[attr-defined]
            {
                "id": "task-response-bad-trace-jsonpath-safe",
                "session_id": "session-response-bad-trace-jsonpath-safe",
                "prompt": "response bad trace jsonpath safe",
                "status": "failed",
                "trace_json": (
                    "bad trace payload provider_status "
                    "response_path=$.data['access_token'] Bearer secret-token"
                ),
                "usage_json": None,
                "created_at": "2026-07-16T10:04:00",
                "updated_at": "2026-07-16T10:05:00",
            }
        )

        serialized = str(payload["trace_json"])

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("response_path=$.data['access_token']", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_cancel_response_summary_from_task_reuses_shared_status_summary(
        self,
    ) -> None:
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        try:
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 41
            )
            payload = chat_persistence_module.get_task_cancel_response_summary_from_task(  # type: ignore[attr-defined]
                {
                    "id": "task-cancel-summary",
                    "status": "cancelled",
                },
                previous_status="running",
                already_terminal=False,
            )
        finally:
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "normalize:cancelled",
                "label:cancelled",
                "rank:cancelled",
            ],
        )
        self.assertEqual(payload["task_id"], "task-cancel-summary")
        self.assertEqual(payload["previous_status"], "running")
        self.assertEqual(payload["status"], "cancelled")
        self.assertEqual(payload["status_normalized"], "normalized::cancelled")
        self.assertEqual(payload["status_label"], "label::cancelled")
        self.assertEqual(payload["status_rank"], 41)
        self.assertFalse(payload["already_terminal"])

    def test_get_task_cancel_response_summary_from_task_accepts_model_dump_row(
        self,
    ) -> None:
        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-cancel-model-row",
                    "status": "cancelled",
                }

        payload = chat_persistence_module.get_task_cancel_response_summary_from_task(  # type: ignore[attr-defined]
            TaskRowPayload(),
            previous_status="running",
            already_terminal=False,
        )

        self.assertEqual(payload["task_id"], "task-cancel-model-row")
        self.assertEqual(payload["status"], "cancelled")

    def test_get_task_create_response_summary_reuses_shared_status_summary(
        self,
    ) -> None:
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        try:
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 13
            )
            payload = chat_persistence_module.get_task_create_response_summary(  # type: ignore[attr-defined]
                task_id="task-create-summary",
                session_id="session-create-summary",
                status="pending",
            )
        finally:
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "normalize:pending",
                "label:pending",
                "rank:pending",
            ],
        )
        self.assertEqual(payload["task_id"], "task-create-summary")
        self.assertEqual(payload["session_id"], "session-create-summary")
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["status_normalized"], "normalized::pending")
        self.assertEqual(payload["status_label"], "label::pending")
        self.assertEqual(payload["status_rank"], 13)

    def test_create_task_entry_reuses_shared_create_response_summary_helper(
        self,
    ) -> None:
        original_ensure_session = task_routes_module.ensure_session
        original_create_task = task_routes_module.create_task
        original_create_message = task_routes_module.create_message
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_create_summary_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_create_response_summary",
            None,
        )
        original_normalize = task_routes_module.normalize_task_status
        original_label_exists = hasattr(task_routes_module, "task_status_label")
        original_rank_exists = hasattr(task_routes_module, "task_status_rank")
        original_label = getattr(task_routes_module, "task_status_label", None)
        original_rank = getattr(task_routes_module, "task_status_rank", None)
        original_create_response = task_routes_module.TaskCreateResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.ensure_session = (
                lambda **_kwargs: "session-create-route-summary"
            )
            task_routes_module.create_task = lambda **_kwargs: "task-create-route-summary"
            task_routes_module.create_message = lambda **_kwargs: None
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.normalize_task_status = lambda _status: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "create_task_entry should reuse get_task_create_response_summary(...) for status normalization"
                )
            )
            task_routes_module.task_status_label = lambda _status: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "create_task_entry should reuse get_task_create_response_summary(...) for status label"
                )
            )
            task_routes_module.task_status_rank = lambda _status: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "create_task_entry should reuse get_task_create_response_summary(...) for status rank"
                )
            )
            task_routes_module.chat_persistence_service.get_task_create_response_summary = (  # type: ignore[attr-defined]
                lambda *, task_id, session_id, status: {
                    "task_id": task_id,
                    "session_id": session_id,
                    "status": status,
                    "status_normalized": "normalized::pending",
                    "status_label": "label::pending",
                    "status_rank": 13,
                }
            )
            task_routes_module.TaskCreateResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.create_task_entry(
                task_routes_module.TaskCreateRequest(
                    user_input="create route summary",
                    session_id=None,
                ),
                current_user={"id": "user-create-route-summary"},
            )
        finally:
            task_routes_module.ensure_session = original_ensure_session
            task_routes_module.create_task = original_create_task
            task_routes_module.create_message = original_create_message
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            if original_create_summary_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_create_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_create_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_create_response_summary = original_create_summary_helper  # type: ignore[attr-defined]
            task_routes_module.normalize_task_status = original_normalize  # type: ignore[assignment]
            if original_label_exists:
                task_routes_module.task_status_label = original_label  # type: ignore[assignment]
            elif hasattr(task_routes_module, "task_status_label"):
                delattr(task_routes_module, "task_status_label")
            if original_rank_exists:
                task_routes_module.task_status_rank = original_rank  # type: ignore[assignment]
            elif hasattr(task_routes_module, "task_status_rank"):
                delattr(task_routes_module, "task_status_rank")
            task_routes_module.TaskCreateResponse = original_create_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["task_id"], "task-create-route-summary")
        self.assertEqual(captured[0]["session_id"], "session-create-route-summary")
        self.assertEqual(captured[0]["status_normalized"], "normalized::pending")
        self.assertEqual(captured[0]["status_label"], "label::pending")
        self.assertEqual(captured[0]["status_rank"], 13)

    def test_cancel_task_reuses_shared_cancel_response_summary_helper(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_update_task_status = task_routes_module.update_task_status
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_cancel_summary_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_cancel_response_summary_from_task",
            None,
        )
        original_normalize = task_routes_module.normalize_task_status
        original_label_exists = hasattr(task_routes_module, "task_status_label")
        original_rank_exists = hasattr(task_routes_module, "task_status_rank")
        original_label = getattr(task_routes_module, "task_status_label", None)
        original_rank = getattr(task_routes_module, "task_status_rank", None)
        original_cancel_response = task_routes_module.TaskCancelResponse
        captured: list[dict[str, object]] = []
        task_reads = [
            {
                "id": "task-cancel-route-summary",
                "session_id": "session-cancel-route-summary",
                "status": "running",
            },
            {
                "id": "task-cancel-route-summary",
                "session_id": "session-cancel-route-summary",
                "status": "cancelled",
            },
        ]
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: dict(  # type: ignore[assignment]
                task_reads.pop(0)
            )
            task_routes_module.update_task_status = lambda **_kwargs: None
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.normalize_task_status = lambda status: (  # type: ignore[assignment]
                "running"
                if status == "running"
                else (_ for _ in ()).throw(
                    AssertionError(
                        "cancel_task should reuse get_task_cancel_response_summary_from_task(...) for current status normalization"
                    )
                )
            )
            task_routes_module.task_status_label = lambda _status: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "cancel_task should reuse get_task_cancel_response_summary_from_task(...) for current status label"
                )
            )
            task_routes_module.task_status_rank = lambda _status: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "cancel_task should reuse get_task_cancel_response_summary_from_task(...) for current status rank"
                )
            )
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, previous_status, already_terminal: {
                    "task_id": task["id"],
                    "previous_status": previous_status,
                    "status": task["status"],
                    "status_normalized": "normalized::cancelled",
                    "status_label": "label::cancelled",
                    "status_rank": 41,
                    "already_terminal": already_terminal,
                }
            )
            task_routes_module.TaskCancelResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.cancel_task(
                "task-cancel-route-summary",
                current_user={"id": "user-cancel-route-summary"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.update_task_status = original_update_task_status
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            if original_cancel_summary_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_cancel_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_cancel_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = original_cancel_summary_helper  # type: ignore[attr-defined]
            task_routes_module.normalize_task_status = original_normalize  # type: ignore[assignment]
            if original_label_exists:
                task_routes_module.task_status_label = original_label  # type: ignore[assignment]
            elif hasattr(task_routes_module, "task_status_label"):
                delattr(task_routes_module, "task_status_label")
            if original_rank_exists:
                task_routes_module.task_status_rank = original_rank  # type: ignore[assignment]
            elif hasattr(task_routes_module, "task_status_rank"):
                delattr(task_routes_module, "task_status_rank")
            task_routes_module.TaskCancelResponse = original_cancel_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["task_id"], "task-cancel-route-summary")
        self.assertEqual(captured[0]["previous_status"], "running")
        self.assertEqual(captured[0]["status"], "cancelled")
        self.assertEqual(captured[0]["status_normalized"], "normalized::cancelled")
        self.assertEqual(captured[0]["status_label"], "label::cancelled")
        self.assertEqual(captured[0]["status_rank"], 41)
        self.assertFalse(captured[0]["already_terminal"])

    def test_task_route_module_does_not_expose_dead_plain_clone_dict_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_plain_clone_dict"))

    def test_get_task_detail_reuses_shared_task_response_summary_helper(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_with_status_meta = getattr(task_routes_module, "_with_status_meta", None)
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )
        original_task_response = task_routes_module.TaskResponse
        cloned_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: list[dict[str, object]] = []
        try:
            self.assertFalse(hasattr(task_routes_module, "_with_status_meta"))
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-response-governance-helper",
                "session_id": "session-response-governance-helper",
                "prompt": "task response governance helper",
                "status": "completed",
                "created_at": "2026-06-18T11:00:00",
                "updated_at": "2026-06-18T11:05:00",
                "trace_json": None,
                "usage_json": None,
            }
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                "id": "task-response-governance-helper",
                "session_id": "session-response-governance-helper",
                "prompt": "task response governance helper",
                "status": "completed",
                "status_normalized": "completed",
                "status_label": "Completed",
                "status_rank": 3,
                "trace_json": None,
                "usage_json": None,
                "created_at": "2026-06-18T11:00:00",
                "updated_at": "2026-06-18T11:05:00",
                "governance": cloned_governance,
            }
            )
            task_routes_module.TaskResponse = lambda **kwargs: captured.append(kwargs) or kwargs  # type: ignore[assignment]
            task_routes_module.get_task_detail(
                "task-response-governance-helper",
                current_user={"id": "user-response-governance-helper"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]
            if original_with_status_meta is not None:
                task_routes_module._with_status_meta = original_with_status_meta  # type: ignore[attr-defined]
            task_routes_module.TaskResponse = original_task_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["governance"], cloned_governance)

    def test_get_task_detail_leaves_governance_empty_without_service_summary(self) -> None:
        task = {
            "id": "task-response-no-service-governance",
            "session_id": "session-response-no-service-governance",
            "prompt": "task response without service governance summary",
            "status": "completed",
            "created_at": "2026-06-09T10:00:00",
            "updated_at": "2026-06-09T10:05:00",
            "tool_registry_profile": "planning_only",
            "tool_registry_provider_source": "planning_suite",
            "allowed_tool_names_json": json.dumps(["task_plan"]),
            "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task = task_routes_module.get_task
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should not fall back to the shared row parser when service governance is absent"
                    )
                )
            )
            payload = task_routes_module.get_task_detail(
                "task-response-no-service-governance",
                current_user={"id": "user-response-no-service-governance"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNone(payload.governance)

    def test_serialize_task_governance_columns_trusts_shared_extractor_shape(
        self,
    ) -> None:
        class GuardedGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "task governance column serializer should trust the shared extractor's normalized dict shape"
                )

        original_extractor = (
            chat_persistence_module._extract_task_governance_from_trace_steps
        )
        original_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._extract_task_governance_from_trace_steps = (
                lambda _trace_steps: GuardedGovernanceDict(
                    profile="guarded_profile",
                    provider_source="guarded_source",
                    allowed_tool_names=["guarded_tool"],
                    allowed_tool_labels=["Guarded Tool"],
                )
            )
            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                lambda _governance: (_ for _ in ()).throw(
                    AssertionError(
                        "task governance column serializer should not re-normalize an already normalized governance dict"
                    )
                )
            )
            payload = chat_persistence_module._serialize_task_governance_columns(  # type: ignore[attr-defined]
                [{"id": "trace-governance-1"}]
            )
        finally:
            chat_persistence_module._extract_task_governance_from_trace_steps = (
                original_extractor
            )
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]
        self.assertEqual(
            payload,
            (
                "guarded_profile",
                "guarded_source",
                json.dumps(["guarded_tool"], ensure_ascii=False),
                json.dumps(["Guarded Tool"], ensure_ascii=False),
            ),
        )

    def test_serialize_task_governance_columns_accepts_tuple_allowed_tool_values(
        self,
    ) -> None:
        original_extractor = (
            chat_persistence_module._extract_task_governance_from_trace_steps
        )
        try:
            chat_persistence_module._extract_task_governance_from_trace_steps = (
                lambda _trace_steps: {
                    "profile": "guarded_profile",
                    "provider_source": "guarded_source",
                    "allowed_tool_names": ("guarded_tool",),
                    "allowed_tool_labels": ("Guarded Tool",),
                }
            )
            payload = chat_persistence_module._serialize_task_governance_columns(  # type: ignore[attr-defined]
                [{"id": "trace-governance-2"}]
            )
        finally:
            chat_persistence_module._extract_task_governance_from_trace_steps = (
                original_extractor
            )

        self.assertEqual(
            payload,
            (
                "guarded_profile",
                "guarded_source",
                json.dumps(["guarded_tool"], ensure_ascii=False),
                json.dumps(["Guarded Tool"], ensure_ascii=False),
            ),
        )

    def test_extract_task_governance_from_trace_steps_reuses_shared_normalizer(self) -> None:
        original_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_extract_task_governance_from_trace_steps_forwards_raw_governance_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-raw-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": " Planning_Only ",
                            "tool_registry_provider_source": " Planning_Suite ",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )

    def test_extract_task_governance_from_trace_steps_forwards_raw_allowed_tool_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-raw-tools-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": [" task_plan "],
                            "allowed_tool_labels": [" Task Planner Suite "],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )

    def test_extract_task_governance_from_trace_steps_forwards_blank_governance_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-blank-governance-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "   ",
                            "tool_registry_provider_source": " Planning_Suite ",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "   ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )

    def test_extract_task_governance_from_trace_steps_forwards_blank_allowed_tool_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-blank-tools-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["   ", " task_plan "],
                            "allowed_tool_labels": ["   ", " Task Planner Suite "],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["   ", " task_plan "],
                    "allowed_tool_labels": ["   ", " Task Planner Suite "],
                }
            ],
        )

    def test_extract_task_governance_from_task_row_reuses_shared_normalizer(self) -> None:
        original_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "planning_suite",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_extract_task_governance_from_task_row_forwards_raw_governance_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": " Planning_Only ",
                    "tool_registry_provider_source": " Planning_Suite ",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )

    def test_extract_task_governance_from_task_row_forwards_raw_allowed_tool_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "planning_suite",
                    "allowed_tool_names_json": json.dumps([" task_plan "]),
                    "allowed_tool_labels_json": json.dumps([" Task Planner Suite "]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )

    def test_extract_task_governance_from_task_row_forwards_blank_raw_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            payload = chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": "   ",
                    "tool_registry_provider_source": "   ",
                    "allowed_tool_names_json": json.dumps(["   "]),
                    "allowed_tool_labels_json": json.dumps(["   "]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "   ",
                    "provider_source": "   ",
                    "allowed_tool_names": ["   "],
                    "allowed_tool_labels": ["   "],
                }
            ],
        )
        self.assertEqual(
            payload,
            {
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_with_task_governance_drops_raw_governance_source_columns(self) -> None:
        payload = chat_persistence_module._with_task_governance(  # type: ignore[attr-defined]
            {
                "id": "task-governance-shape",
                "trace_json": "[]",
                "usage_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
            }
        )

        self.assertEqual(payload["id"], "task-governance-shape")
        self.assertIn("governance", payload)
        self.assertNotIn("tool_registry_profile", payload)
        self.assertNotIn("tool_registry_provider_source", payload)
        self.assertNotIn("allowed_tool_names_json", payload)
        self.assertNotIn("allowed_tool_labels_json", payload)
        self.assertIn("trace_json", payload)
        self.assertIn("usage_json", payload)

    def test_extract_task_governance_from_trace_steps_skips_empty_governance_dicts(
        self,
    ) -> None:
        payload = chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
            [
                {
                    "id": "trace-empty-governance-1",
                    "type": "thought",
                    "content": "empty governance",
                    "meta": {},
                },
                {
                    "id": "trace-empty-governance-2",
                    "type": "thought",
                    "content": "real governance",
                    "meta": {
                        "tool_registry_profile": "planning_only",
                        "tool_registry_provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                },
            ]
        )

        self.assertEqual(
            payload,
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_normalize_task_governance_dict_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                }
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profile": "profile::normalized",
                "provider_source": "source::normalized",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_normalize_task_governance_dict_returns_none_for_empty_governance(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
            {
                "profile": "   ",
                "provider_source": None,
                "allowed_tool_names": [],
                "allowed_tool_labels": [],
            }
        )

        self.assertIsNone(payload)

    def test_normalize_task_governance_dict_upgrades_builtin_calculator_label_from_internal_name(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
            {
                "profile": "calculator_only",
                "provider_source": "default",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )

        self.assertEqual(
            payload,
            {
                "profile": "calculator_only",
                "provider_source": "default",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator"],
            },
        )

    def test_normalize_task_governance_dict_preserves_selected_source_override_label_for_internal_tool_name(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )

        self.assertEqual(
            payload,
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_normalize_task_governance_dict_drops_productized_bracket_suffix_from_selected_source_override_label(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite [calculator]"],
            }
        )

        self.assertEqual(
            payload,
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_parse_task_governance_json_list_blob_preserves_raw_string_items(
        self,
    ) -> None:
        payload = chat_persistence_module._parse_task_governance_json_list_blob(  # type: ignore[attr-defined]
            json.dumps(["   ", " task_plan ", "Task Planner", 123, None])
        )

        self.assertEqual(payload, ["   ", " task_plan ", "Task Planner"])

    def test_parse_task_governance_json_list_blob_accepts_preparsed_list(
        self,
    ) -> None:
        payload = chat_persistence_module._parse_task_governance_json_list_blob(  # type: ignore[attr-defined]
            ["   ", " task_plan ", "Task Planner", 123, None]
        )

        self.assertEqual(payload, ["   ", " task_plan ", "Task Planner"])

    def test_normalize_task_governance_dict_accepts_tuple_allowed_tool_values(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
            {
                "profile": " Planning_Only ",
                "provider_source": " Planning_Suite ",
                "allowed_tool_names": (" task_plan ", "   "),
                "allowed_tool_labels": (" Task Planner Suite ", "   "),
            }
        )

        self.assertEqual(
            payload,
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_normalize_session_governance_summary_dict_accepts_tuple_summary_values(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
            {
                "profiles": (" Planning_Only ", " "),
                "provider_sources": (" Planning_Suite ",),
                "allowed_tool_names": (" task_plan ", " "),
                "allowed_tool_labels": (" Task Planner Suite ",),
            }
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_normalize_session_governance_summary_uses_single_provider_source_for_internal_tool_labels(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_normalize_session_governance_summary_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
                {
                    "profiles": [" Planning_Only "],
                    "provider_sources": [" Planning_Suite "],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                }
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profiles": ["profile::normalized"],
                "provider_sources": ["source::normalized"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_normalize_session_governance_summary_returns_none_for_empty_summary(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
            {
                "profiles": [],
                "provider_sources": [],
                "allowed_tool_names": [],
                "allowed_tool_labels": [],
            }
        )

        self.assertIsNone(payload)

    def test_normalize_session_governance_summary_deduplicates_and_sorts_list_fields(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
            {
                "profiles": [" Planning_Only ", "analysis_only", "planning_only"],
                "provider_sources": [
                    " Retrieval_Suite ",
                    "analysis_suite",
                    "retrieval_suite",
                ],
                "allowed_tool_names": [" task_plan ", "calc_eval", "task_plan"],
                "allowed_tool_labels": [
                    " Task Planner ",
                    "Calculator",
                    "Task Planner",
                ],
            }
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["analysis_only", "planning_only"],
                "provider_sources": ["analysis_suite", "retrieval_suite"],
                "allowed_tool_names": ["calc_eval", "task_plan"],
                "allowed_tool_labels": ["Calculator", "Task Planner"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_task_normalizer(self) -> None:
        original_task_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                None,
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                },
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_task_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profiles": ["normalized_profile"],
                "provider_sources": ["normalized_source"],
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_task_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": " Planning_Only ",
                "provider_source": " Planning_Suite ",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            }

            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                None,
                {
                    "profile": "ignored",
                    "provider_source": "ignored",
                    "allowed_tool_names": ["ignored"],
                    "allowed_tool_labels": ["ignored"],
                },
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_task_normalizer  # type: ignore[attr-defined]
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profiles": ["profile::normalized"],
                "provider_sources": ["source::normalized"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_session_normalizer(self) -> None:
        original_session_normalizer = chat_persistence_module._normalize_session_governance_summary_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_session_governance_summary_dict = (
                lambda _governance: {
                    "profiles": ["normalized_current_profile"],
                    "provider_sources": ["normalized_current_source"],
                    "allowed_tool_names": ["normalized_current_tool"],
                    "allowed_tool_labels": ["Normalized Current Tool"],
                }
            )
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                },
                None,
            )
        finally:
            chat_persistence_module._normalize_session_governance_summary_dict = original_session_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profiles": ["normalized_current_profile"],
                "provider_sources": ["normalized_current_source"],
                "allowed_tool_names": ["normalized_current_tool"],
                "allowed_tool_labels": ["Normalized Current Tool"],
            },
        )

    def test_merge_session_governance_summary_deduplicates_stale_productized_labels_when_task_names_arrive(
        self,
    ) -> None:
        payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": [],
                "allowed_tool_labels": ["Calculator Suite [calculator]"],
            },
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_task_rows_governance_summary_reuses_shared_merger(self) -> None:
        original_merge = chat_persistence_module._merge_session_governance_summary  # type: ignore[attr-defined]
        captured: list[tuple[object, object]] = []
        try:
            chat_persistence_module._merge_session_governance_summary = (  # type: ignore[attr-defined]
                lambda current, task_governance: captured.append(
                    (current, task_governance)
                )
                or {
                    "profiles": ["shared_summary_profile"],
                    "provider_sources": ["shared_summary_source"],
                    "allowed_tool_names": ["shared_summary_tool"],
                    "allowed_tool_labels": ["Shared Summary Tool"],
                }
            )
            payload = chat_persistence_module.get_task_rows_governance_summary(  # type: ignore[attr-defined]
                [
                    {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "default",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        }
                    }
                ]
            )
        finally:
            chat_persistence_module._merge_session_governance_summary = original_merge  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                (
                    None,
                    {
                        "profile": "planning_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                )
            ],
        )
        self.assertEqual(
            payload,
            {
                "profiles": ["shared_summary_profile"],
                "provider_sources": ["shared_summary_source"],
                "allowed_tool_names": ["shared_summary_tool"],
                "allowed_tool_labels": ["Shared Summary Tool"],
            },
        )

    def test_get_task_rows_governance_summary_coerces_model_dump_governance(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chat_persistence_module.get_task_rows_governance_summary(  # type: ignore[attr-defined]
            [
                {
                    "id": "task-governance-model-dump",
                    "governance": ResponseReadyGovernance(
                        {
                            "profile": "planning_only",
                            "provider_source": "suite_a",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        }
                    ),
                }
            ]
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["planning_only"],
                "provider_sources": ["suite_a"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_get_task_rows_trace_preview_summary_reuses_shared_preview_helper(
        self,
    ) -> None:
        original_preview_helper = (
            chat_persistence_module.get_task_trace_preview_summary_from_task
        )
        captured: list[tuple[str, int]] = []
        try:
            chat_persistence_module.get_task_trace_preview_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, preview_limit=3: captured.append(
                    (str(task.get("id")), int(preview_limit))
                )
                or {
                    "trace_step_count": 4
                    if str(task.get("id")) == "task-preview-1"
                    else 2,
                    "rag_hit_count": 2
                    if str(task.get("id")) == "task-preview-1"
                    else 1,
                    "trace_preview": [
                        {
                            "id": f"preview-{task.get('id')}",
                            "seq": 1,
                            "type": "tool_result",
                            "title": "tool result",
                            "content_excerpt": "preview body",
                        }
                    ],
                }
            )
            payload = chat_persistence_module.get_task_rows_trace_preview_summary(  # type: ignore[attr-defined]
                [
                    {"id": "task-preview-1"},
                    {"id": "task-preview-2"},
                ],
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_trace_preview_summary_from_task = original_preview_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [("task-preview-1", 5), ("task-preview-2", 5)],
        )
        self.assertEqual(payload["trace_step_count"], 6)
        self.assertEqual(payload["rag_hit_count"], 3)
        self.assertEqual(
            payload["tasks"],
            [
                {
                    "task_id": "task-preview-1",
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "trace_preview": [
                        {
                            "id": "preview-task-preview-1",
                            "seq": 1,
                            "type": "tool_result",
                            "title": "tool result",
                            "content_excerpt": "preview body",
                        }
                    ],
                },
                {
                    "task_id": "task-preview-2",
                    "trace_step_count": 2,
                    "rag_hit_count": 1,
                    "trace_preview": [
                        {
                            "id": "preview-task-preview-2",
                            "seq": 1,
                            "type": "tool_result",
                            "title": "tool result",
                            "content_excerpt": "preview body",
                        }
                    ],
                },
            ],
        )

    def test_get_task_rows_trace_preview_summary_coerces_nested_preview_models(
        self,
    ) -> None:
        original_preview_helper = (
            chat_persistence_module.get_task_trace_preview_summary_from_task
        )

        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_trace_preview_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, preview_limit=3: {
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "trace_preview": [
                        ResponseReadyBlock(
                            {
                                "id": f"preview-{task.get('id')}",
                                "seq": int(preview_limit),
                                "type": "tool_result",
                                "title": "tool result",
                                "content_excerpt": "preview model body",
                            }
                        )
                    ],
                }
            )
            payload = chat_persistence_module.get_task_rows_trace_preview_summary(  # type: ignore[attr-defined]
                [
                    {"id": "task-preview-model"},
                ],
                preview_limit=6,
            )
        finally:
            chat_persistence_module.get_task_trace_preview_summary_from_task = original_preview_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["trace_step_count"], 4)
        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(
            payload["tasks"],
            [
                {
                    "task_id": "task-preview-model",
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "trace_preview": [
                        {
                            "id": "preview-task-preview-model",
                            "seq": 6,
                            "type": "tool_result",
                            "title": "tool result",
                            "content_excerpt": "preview model body",
                        }
                    ],
                }
            ],
        )

    def test_get_task_rows_trace_preview_summary_redacts_plain_wrapped_preview_rows(
        self,
    ) -> None:
        original_preview_helper = (
            chat_persistence_module.get_task_trace_preview_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_preview_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, preview_limit=3: {
                    "trace_step_count": 1,
                    "rag_hit_count": 0,
                    "trace_preview": [
                        {
                            "id": UserString(f"preview-{task.get('id')}"),
                            "seq": 1,
                            "type": UserString("action"),
                            "title": UserString(
                                "Provider Search [provider_search via http_json]"
                            ),
                            "content_excerpt": UserString(
                                "Tool done: Provider Search "
                                "query_params.access_token Bearer secret-token"
                            ),
                        }
                    ],
                }
            )
            payload = chat_persistence_module.get_task_rows_trace_preview_summary(  # type: ignore[attr-defined]
                [{"id": "task-preview-plain-wrapped"}],
                preview_limit=3,
            )
        finally:
            chat_persistence_module.get_task_trace_preview_summary_from_task = original_preview_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        preview = payload["tasks"][0]["trace_preview"][0]
        self.assertEqual(preview["id"], "preview-task-preview-plain-wrapped")
        self.assertIn("[redacted]", preview["content_excerpt"])
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_rows_export_summary_reuses_shared_batch_helpers(
        self,
    ) -> None:
        original_trace_preview_helper = (
            chat_persistence_module.get_task_rows_trace_preview_summary
        )
        original_governance_helper = (
            chat_persistence_module.get_task_rows_governance_summary
        )
        captured: list[tuple[str, object]] = []
        task_rows = [{"id": "task-export-1"}, {"id": "task-export-2"}]
        try:
            chat_persistence_module.get_task_rows_trace_preview_summary = (  # type: ignore[attr-defined]
                lambda rows, preview_limit=3: captured.append(
                    ("trace", (rows, preview_limit))
                )
                or {
                    "tasks": [
                        {
                            "task_id": "task-export-1",
                            "trace_step_count": 4,
                            "rag_hit_count": 2,
                            "trace_preview": [],
                        }
                    ],
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                }
            )
            chat_persistence_module.get_task_rows_governance_summary = (  # type: ignore[attr-defined]
                lambda rows: captured.append(("governance", rows))
                or {
                    "profiles": ["shared_summary_profile"],
                    "provider_sources": ["shared_summary_source"],
                    "allowed_tool_names": ["shared_summary_tool"],
                    "allowed_tool_labels": ["Shared Summary Tool"],
                }
            )
            payload = chat_persistence_module.get_task_rows_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_trace_preview_summary = original_trace_preview_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_rows_governance_summary = original_governance_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                ("trace", (task_rows, 5)),
                ("governance", task_rows),
            ],
        )
        self.assertEqual(
            payload,
            {
                "tasks": [
                    {
                        "task_id": "task-export-1",
                        "trace_step_count": 4,
                        "rag_hit_count": 2,
                        "trace_preview": [],
                    }
                ],
                "trace_step_count": 4,
                "rag_hit_count": 2,
                "governance": {
                    "profiles": ["shared_summary_profile"],
                    "provider_sources": ["shared_summary_source"],
                    "allowed_tool_names": ["shared_summary_tool"],
                    "allowed_tool_labels": ["Shared Summary Tool"],
                },
            },
        )

    def test_get_task_rows_export_summary_coerces_response_ready_task_rows(
        self,
    ) -> None:
        original_trace_preview_helper = (
            chat_persistence_module.get_task_rows_trace_preview_summary
        )
        original_governance_helper = (
            chat_persistence_module.get_task_rows_governance_summary
        )

        class ResponseReadyRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_rows = [{"id": "task-export-model"}]
        try:
            chat_persistence_module.get_task_rows_trace_preview_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        ResponseReadyRow(
                            {
                                "task_id": "task-export-model",
                                "trace_step_count": 4,
                                "rag_hit_count": 2,
                                "trace_preview": [],
                            }
                        )
                    ],
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                }
            )
            chat_persistence_module.get_task_rows_governance_summary = (  # type: ignore[attr-defined]
                lambda _rows: {"profiles": ["shared_summary_profile"]}
            )
            payload = chat_persistence_module.get_task_rows_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_trace_preview_summary = original_trace_preview_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_rows_governance_summary = original_governance_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["tasks"],
            [
                {
                    "task_id": "task-export-model",
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "trace_preview": [],
                }
            ],
        )

    def test_get_task_rows_export_summary_normalizes_plain_wrapped_task_rows(
        self,
    ) -> None:
        original_trace_preview_helper = (
            chat_persistence_module.get_task_rows_trace_preview_summary
        )
        original_governance_helper = (
            chat_persistence_module.get_task_rows_governance_summary
        )

        task_rows = [{"id": "task-export-plain-wrapped"}]
        try:
            chat_persistence_module.get_task_rows_trace_preview_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        {
                            "task_id": UserString("task-export-plain-wrapped"),
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": UserString("preview-export-plain-wrapped"),
                                    "seq": 1,
                                    "type": UserString("action"),
                                    "title": UserString(
                                        "Provider Search [provider_search via http_json]"
                                    ),
                                    "content_excerpt": UserString(
                                        "Tool done: Provider Search "
                                        "query_params.access_token Bearer secret-token"
                                    ),
                                }
                            ],
                        }
                    ],
                    "trace_step_count": 1,
                    "rag_hit_count": 0,
                }
            )
            chat_persistence_module.get_task_rows_governance_summary = (  # type: ignore[attr-defined]
                lambda _rows: {"profiles": ["shared_summary_profile"]}
            )
            payload = chat_persistence_module.get_task_rows_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_trace_preview_summary = original_trace_preview_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_rows_governance_summary = original_governance_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["tasks"][0]["task_id"], "task-export-plain-wrapped")
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_rows_session_export_summary_reuses_shared_helpers(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_rows_export_summary
        original_usage_helper = chat_persistence_module.get_task_usage_from_task
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[tuple[str, object]] = []
        task_rows = [
            {
                "id": "task-session-export-1",
                "prompt": "task one",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00",
                "updated_at": "2026-06-22T10:01:00",
                "usage_json": "usage-1",
                "governance": {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                },
            },
            {
                "id": "task-session-export-2",
                "prompt": "task two",
                "status": "running",
                "created_at": "2026-06-22T10:02:00",
                "updated_at": "2026-06-22T10:03:00",
                "usage_json": "usage-2",
                "governance": {
                    "profile": "retrieval_only",
                    "provider_source": "retrieval_suite",
                    "allowed_tool_names": ["task_retrieve"],
                    "allowed_tool_labels": ["Task Retrieve"],
                },
            },
        ]
        try:
            chat_persistence_module.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda rows, preview_limit=3: captured.append(
                    ("export", (rows, preview_limit))
                )
                or {
                    "tasks": [
                        {
                            "task_id": "task-session-export-1",
                            "trace_step_count": 4,
                            "rag_hit_count": 2,
                            "trace_preview": [],
                        },
                        {
                            "task_id": "task-session-export-2",
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                        },
                    ],
                    "trace_step_count": 5,
                    "rag_hit_count": 2,
                    "governance": {"profiles": ["shared_profile"]},
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda task: captured.append(("usage", str(task.get("id"))))
                or {"usage_task_id": str(task.get("id"))}
            )
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(("normalize", status))
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(("label", status))
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(("rank", status))
                or (41 if status == "completed" else 17)
            )
            payload = chat_persistence_module.get_task_rows_session_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_export_summary = original_export_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                ("export", (task_rows, 5)),
                ("normalize", "completed"),
                ("label", "completed"),
                ("rank", "completed"),
                ("usage", "task-session-export-1"),
                ("normalize", "running"),
                ("label", "running"),
                ("rank", "running"),
                ("usage", "task-session-export-2"),
            ],
        )
        self.assertEqual(
            payload,
            {
                "tasks": [
                    {
                        "task": {
                            "id": "task-session-export-1",
                            "prompt": "task one",
                            "status": "completed",
                            "status_normalized": "normalized::completed",
                            "status_label": "label::completed",
                            "status_rank": 41,
                            "created_at": "2026-06-22T10:00:00",
                            "updated_at": "2026-06-22T10:01:00",
                        },
                        "usage": {"usage_task_id": "task-session-export-1"},
                        "trace": {
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                            "step_count": 4,
                            "rag_hit_count": 2,
                            "preview": [],
                        },
                    },
                    {
                        "task": {
                            "id": "task-session-export-2",
                            "prompt": "task two",
                            "status": "running",
                            "status_normalized": "normalized::running",
                            "status_label": "label::running",
                            "status_rank": 17,
                            "created_at": "2026-06-22T10:02:00",
                            "updated_at": "2026-06-22T10:03:00",
                        },
                        "usage": {"usage_task_id": "task-session-export-2"},
                        "trace": {
                            "governance": {
                                "profile": "retrieval_only",
                                "provider_source": "retrieval_suite",
                                "allowed_tool_names": ["task_retrieve"],
                                "allowed_tool_labels": ["Task Retrieve"],
                            },
                            "step_count": 1,
                            "rag_hit_count": 0,
                            "preview": [],
                        },
                    },
                ],
                "stats": {
                    "task_count": 2,
                    "trace_step_count": 5,
                    "rag_hit_count": 2,
                },
                "governance": {"profiles": ["shared_profile"]},
            },
        )

    def test_get_task_rows_session_export_summary_coerces_model_export_rows_and_nested_preview(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_rows_export_summary

        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_rows = [
            {
                "id": "task-session-export-model",
                "prompt": "task model",
                "status": "completed",
                "created_at": "2026-07-02T11:00:00",
                "updated_at": "2026-07-02T11:01:00",
                "usage_json": None,
                "governance": None,
            }
        ]
        try:
            chat_persistence_module.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        ResponseReadyBlock(
                            {
                                "task_id": "task-session-export-model",
                                "trace_step_count": 4,
                                "rag_hit_count": 2,
                                "trace_preview": [
                                    ResponseReadyBlock(
                                        {
                                            "id": "preview-model",
                                            "seq": 4,
                                            "type": "action",
                                            "title": "Provider Search",
                                            "content_excerpt": "preview model body",
                                        }
                                    )
                                ],
                            }
                        )
                    ],
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "governance": None,
                }
            )
            payload = chat_persistence_module.get_task_rows_session_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_export_summary = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["task"]["id"], "task-session-export-model")
        self.assertEqual(payload["tasks"][0]["trace"]["step_count"], 4)
        self.assertEqual(payload["tasks"][0]["trace"]["rag_hit_count"], 2)
        self.assertEqual(
            payload["tasks"][0]["trace"]["preview"],
            [
                {
                    "id": "preview-model",
                    "seq": 4,
                    "type": "action",
                    "title": "Provider Search",
                    "content_excerpt": "preview model body",
                }
            ],
        )

    def test_get_task_rows_session_export_summary_normalizes_plain_wrapped_trace_preview(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_rows_export_summary

        task_rows = [
            {
                "id": "task-session-export-plain-wrapped",
                "prompt": "task plain wrapped",
                "status": "completed",
                "created_at": "2026-07-02T11:00:00",
                "updated_at": "2026-07-02T11:01:00",
                "usage_json": None,
                "governance": None,
            }
        ]
        try:
            chat_persistence_module.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        {
                            "task_id": UserString("task-session-export-plain-wrapped"),
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": UserString("preview-session-plain-wrapped"),
                                    "seq": 2,
                                    "type": UserString("action"),
                                    "title": UserString(
                                        "Provider Search [provider_search via http_json]"
                                    ),
                                    "content_excerpt": UserString(
                                        "Tool done: Provider Search "
                                        "query_params.access_token Bearer secret-token"
                                    ),
                                }
                            ],
                        }
                    ],
                    "trace_step_count": 1,
                    "rag_hit_count": 0,
                    "governance": None,
                }
            )
            payload = chat_persistence_module.get_task_rows_session_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=5,
            )
        finally:
            chat_persistence_module.get_task_rows_export_summary = original_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        preview = payload["tasks"][0]["trace"]["preview"][0]
        self.assertEqual(preview["id"], "preview-session-plain-wrapped")
        self.assertIn("[redacted]", preview["content_excerpt"])
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_rows_session_export_summary_accepts_model_dump_task_rows(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_rows_export_summary
        original_usage_helper = chat_persistence_module.get_task_usage_from_task

        class TaskRowPayload:
            def __init__(self, task_id: str, prompt: str, status: str) -> None:
                self.task_id = task_id
                self.prompt = prompt
                self.status = status

            def model_dump(self):
                return {
                    "id": self.task_id,
                    "prompt": self.prompt,
                    "status": self.status,
                    "created_at": "2026-07-02T16:00:00",
                    "updated_at": "2026-07-02T16:01:00",
                    "usage_json": None,
                    "governance": {"profile": "planning_only"},
                }

        task_rows = [TaskRowPayload("task-row-typed-1", "typed one", "completed")]
        try:
            chat_persistence_module.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda rows, preview_limit=3: {
                    "tasks": [
                        {
                            "task_id": "task-row-typed-1",
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                        }
                    ],
                    "trace_step_count": 1,
                    "rag_hit_count": 0,
                    "governance": {"profiles": ["planning_only"]},
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda _task: {"total_tokens": 9}
            )
            payload = chat_persistence_module.get_task_rows_session_export_summary(  # type: ignore[attr-defined]
                task_rows,
                preview_limit=4,
            )
        finally:
            chat_persistence_module.get_task_rows_export_summary = original_export_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["task"]["id"], "task-row-typed-1")
        self.assertEqual(payload["tasks"][0]["usage"], {"total_tokens": 9})
        self.assertEqual(
            payload["tasks"][0]["trace"]["governance"],
            {
                "profile": "planning_only",
                "provider_source": None,
                "allowed_tool_names": [],
                "allowed_tool_labels": [],
            },
        )

    def test_get_session_export_payload_summary_reuses_shared_helpers(self) -> None:
        original_session_export_helper = (
            chat_persistence_module.get_task_rows_session_export_summary
        )
        captured: list[tuple[object, object]] = []
        task_rows = [
            {
                "id": "task-session-payload-summary",
                "prompt": "task one",
                "status": "completed",
                "created_at": "2026-06-22T15:10:00",
                "updated_at": "2026-06-22T15:11:00",
                "usage_json": None,
                "trace_json": None,
                "governance": None,
            }
        ]
        message_rows = [
            {
                "id": "message-1",
                "session_id": "poisoned-session",
                "task_id": "task-session-payload-summary",
                "role": "assistant",
                "content": "hello",
                "created_at": "2026-06-22T15:12:00",
            }
        ]
        usage_summary = {"tasks_total": 1, "prompt_tokens": 0}
        try:
            chat_persistence_module.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda rows, preview_limit=3: captured.append((rows, preview_limit))
                or {
                    "tasks": [
                        {
                            "task": {
                                "id": "task-session-payload-summary",
                                "prompt": "task one",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 3,
                                "created_at": "2026-06-22T15:10:00",
                                "updated_at": "2026-06-22T15:11:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": None,
                                "step_count": 2,
                                "rag_hit_count": 1,
                                "preview": [],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 5,
                        "trace_step_count": 8,
                        "rag_hit_count": 3,
                    },
                    "governance": {"profiles": ["shared_profile"]},
                }
            )
            payload = chat_persistence_module.get_session_export_payload_summary(  # type: ignore[attr-defined]
                usage_summary=usage_summary,
                task_rows=task_rows,
                message_rows=message_rows,
                preview_limit=7,
            )
        finally:
            chat_persistence_module.get_task_rows_session_export_summary = original_session_export_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, [(task_rows, 7)])
        self.assertEqual(
            payload,
            {
                "usage_summary": usage_summary,
                "tasks": [
                    {
                        "task": {
                            "id": "task-session-payload-summary",
                            "prompt": "task one",
                            "status": "completed",
                            "status_normalized": "normalized::completed",
                            "status_label": "label::completed",
                            "status_rank": 3,
                            "created_at": "2026-06-22T15:10:00",
                            "updated_at": "2026-06-22T15:11:00",
                        },
                        "usage": None,
                        "trace": {
                            "governance": None,
                            "step_count": 2,
                            "rag_hit_count": 1,
                            "preview": [],
                        },
                    }
                ],
                "stats": {
                    "task_count": 5,
                    "message_count": 1,
                    "trace_step_count": 8,
                    "rag_hit_count": 3,
                },
                "governance": {"profiles": ["shared_profile"]},
                "messages": [
                    {
                        "id": "message-1",
                        "task_id": "task-session-payload-summary",
                        "role": "assistant",
                        "content": "hello",
                        "created_at": "2026-06-22T15:12:00",
                    }
                ],
            },
        )

    def test_get_session_export_payload_summary_coerces_model_task_rows_and_stats(
        self,
    ) -> None:
        original_session_export_helper = (
            chat_persistence_module.get_task_rows_session_export_summary
        )

        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        ResponseReadyBlock(
                            {
                                "task": {
                                    "id": "task-session-payload-model",
                                    "prompt": "task one",
                                    "status": "completed",
                                    "status_normalized": "normalized::completed",
                                    "status_label": "label::completed",
                                    "status_rank": 3,
                                    "created_at": "2026-07-02T11:10:00",
                                    "updated_at": "2026-07-02T11:11:00",
                                },
                                "usage": None,
                                "trace": {
                                    "governance": None,
                                    "step_count": 2,
                                    "rag_hit_count": 1,
                                    "preview": [],
                                },
                            }
                        )
                    ],
                    "stats": ResponseReadyBlock(
                        {
                            "task_count": 5,
                            "trace_step_count": 8,
                            "rag_hit_count": 3,
                        }
                    ),
                    "governance": {"profiles": ["shared_profile"]},
                }
            )
            payload = chat_persistence_module.get_session_export_payload_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
                preview_limit=7,
            )
        finally:
            chat_persistence_module.get_task_rows_session_export_summary = original_session_export_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["task"]["id"], "task-session-payload-model")
        self.assertEqual(payload["stats"]["task_count"], 5)
        self.assertEqual(payload["stats"]["trace_step_count"], 8)
        self.assertEqual(payload["stats"]["rag_hit_count"], 3)

    def test_get_session_export_payload_summary_normalizes_plain_wrapped_task_rows(
        self,
    ) -> None:
        original_session_export_helper = (
            chat_persistence_module.get_task_rows_session_export_summary
        )

        try:
            chat_persistence_module.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [
                        {
                            "task": {
                                "id": UserString("task-session-payload-plain-wrapped"),
                                "prompt": UserString("task one"),
                                "status": UserString("completed"),
                                "status_normalized": UserString("normalized::completed"),
                                "status_label": UserString("label::completed"),
                                "status_rank": 3,
                                "created_at": UserString("2026-07-02T11:10:00"),
                                "updated_at": UserString("2026-07-02T11:11:00"),
                            },
                            "usage": None,
                            "trace": {
                                "governance": None,
                                "step_count": 1,
                                "rag_hit_count": 0,
                                "preview": [
                                    {
                                        "id": UserString("preview-payload-plain"),
                                        "seq": 2,
                                        "type": UserString("action"),
                                        "title": UserString(
                                            "Provider Search [provider_search via http_json]"
                                        ),
                                        "content_excerpt": UserString(
                                            "Tool done: Provider Search "
                                            "query_params.access_token Bearer secret-token"
                                        ),
                                    }
                                ],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                }
            )
            payload = chat_persistence_module.get_session_export_payload_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
                preview_limit=7,
            )
        finally:
            chat_persistence_module.get_task_rows_session_export_summary = original_session_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(
            payload["tasks"][0]["task"]["id"],
            "task-session-payload-plain-wrapped",
        )
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_payload_summary_coerces_model_message_rows(
        self,
    ) -> None:
        original_session_export_helper = (
            chat_persistence_module.get_task_rows_session_export_summary
        )

        class ResponseReadyMessageRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                }
            )
            payload = chat_persistence_module.get_session_export_payload_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 0},
                task_rows=[],
                message_rows=(
                    ResponseReadyMessageRow(
                        {
                            "id": "message-model-1",
                            "task_id": "task-1",
                            "role": "assistant",
                            "content": "hello",
                            "created_at": "2026-07-02T11:12:00",
                        }
                    ),
                ),
                preview_limit=7,
            )
        finally:
            chat_persistence_module.get_task_rows_session_export_summary = original_session_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["messages"],
            [
                {
                    "id": "message-model-1",
                    "task_id": "task-1",
                    "role": "assistant",
                    "content": "hello",
                    "created_at": "2026-07-02T11:12:00",
                }
            ],
        )
        self.assertEqual(payload["stats"]["message_count"], 1)

    def test_get_session_export_payload_summary_redacts_plain_wrapped_message_rows(
        self,
    ) -> None:
        original_session_export_helper = (
            chat_persistence_module.get_task_rows_session_export_summary
        )

        try:
            chat_persistence_module.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                }
            )
            payload = chat_persistence_module.get_session_export_payload_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 0},
                task_rows=[],
                message_rows=[
                    {
                        "id": UserString("message-payload-plain"),
                        "task_id": UserString("task-payload-plain"),
                        "role": UserString("assistant"),
                        "content": UserString(
                            "Provider Search [provider_search via http_json] "
                            "failed response_path=$.data.access_token "
                            "Bearer secret-token"
                        ),
                        "created_at": UserString("2026-07-02T11:12:00"),
                    }
                ],
                preview_limit=7,
            )
        finally:
            chat_persistence_module.get_task_rows_session_export_summary = original_session_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertEqual(payload["messages"][0]["id"], "message-payload-plain")
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_plain_clones_governance_dicts(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class GuardedTaskGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_session_export_response_summary should plain-clone task governance dicts before outward model validation"
                )

        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_session_export_response_summary should plain-clone session governance dicts before outward model validation"
                )

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-shared-1",
                                "prompt": "shared prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-06-22T16:10:00",
                                "updated_at": "2026-06-22T16:11:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": GuardedTaskGovernanceDict(
                                    profile="planning_only",
                                    provider_source="suite_a",
                                    allowed_tool_names=["task_plan"],
                                    allowed_tool_labels=["Task Planner"],
                                ),
                                "step_count": 3,
                                "rag_hit_count": 1,
                                "preview": [],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 3,
                        "rag_hit_count": 1,
                    },
                    "governance": GuardedSessionGovernanceDict(
                        profiles=["planning_only"],
                        provider_sources=["suite_a"],
                        allowed_tool_names=["task_plan"],
                        allowed_tool_labels=["Task Planner"],
                    ),
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
                preview_limit=3,
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertIsInstance(payload["tasks"][0]["governance"], dict)
        self.assertNotIsInstance(
            payload["tasks"][0]["governance"],
            GuardedTaskGovernanceDict,
        )
        self.assertEqual(
            payload["tasks"][0]["governance"],
            {
                "profile": "planning_only",
                "provider_source": "suite_a",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )
        self.assertIsInstance(payload["governance"], dict)
        self.assertNotIsInstance(
            payload["governance"],
            GuardedSessionGovernanceDict,
        )
        self.assertEqual(
            payload["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["suite_a"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_get_session_export_response_summary_coerces_governance_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_governance = ResponseReadyGovernance(
            {
                "profile": "planning_only",
                "provider_source": "suite_a",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            }
        )
        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["planning_only"],
                "provider_sources": ["suite_a"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            }
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-governance-model",
                                "prompt": "governance model prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-06-22T16:10:00",
                                "updated_at": "2026-06-22T16:11:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": task_governance,
                                "step_count": 3,
                                "rag_hit_count": 1,
                                "preview": [],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 3,
                        "rag_hit_count": 1,
                    },
                    "governance": session_governance,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
                preview_limit=3,
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertIsInstance(payload["tasks"][0]["governance"], dict)
        self.assertIsNot(payload["tasks"][0]["governance"], task_governance)
        self.assertEqual(
            payload["tasks"][0]["governance"]["profile"],
            "planning_only",
        )
        self.assertIsInstance(payload["governance"], dict)
        self.assertIsNot(payload["governance"], session_governance)
        self.assertEqual(payload["governance"]["profiles"], ["planning_only"])

    def test_get_session_export_response_summary_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-governance-source-model",
                                "prompt": "governance source model prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-06-22T16:10:00",
                                "updated_at": "2026-06-22T16:11:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": task_governance,
                                "step_count": 3,
                                "rag_hit_count": 1,
                                "preview": [],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 3,
                        "rag_hit_count": 1,
                    },
                    "governance": session_governance,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
                preview_limit=3,
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["tasks"][0]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )
        self.assertEqual(
            payload["governance"],
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_session_export_response_summary_reuses_shared_payload_helper(self) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )
        captured: list[dict[str, object]] = []
        usage_summary = {"tasks_total": 1}
        task_rows = [{"id": "task-1"}]
        message_rows = [{"id": "message-1"}]
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **kwargs: captured.append(kwargs)
                or {
                    "usage_summary": usage_summary,
                    "tasks": [
                        {
                            "task": {
                                "id": "task-shared-1",
                                "prompt": "shared prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-06-22T16:10:00",
                                "updated_at": "2026-06-22T16:11:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": {
                                    "profile": "planning_only",
                                    "provider_source": "suite_a",
                                    "allowed_tool_names": ["task_plan"],
                                    "allowed_tool_labels": ["Task Planner"],
                                },
                                "step_count": 3,
                                "rag_hit_count": 1,
                                "preview": [
                                    {
                                        "id": "preview-1",
                                        "seq": 3,
                                        "type": "tool_result",
                                        "title": "tool result",
                                        "content_excerpt": "preview body",
                                    }
                                ],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 7,
                        "message_count": 2,
                        "trace_step_count": 9,
                        "rag_hit_count": 4,
                    },
                    "governance": {"profiles": ["planning_only"]},
                    "messages": [
                        {
                            "id": "message-1",
                            "task_id": "task-shared-1",
                            "role": "assistant",
                            "content": "hello",
                            "created_at": "2026-06-22T16:12:00",
                        }
                    ],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary=usage_summary,
                task_rows=task_rows,
                message_rows=message_rows,
                preview_limit=8,
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "usage_summary": usage_summary,
                    "task_rows": task_rows,
                    "message_rows": message_rows,
                    "preview_limit": 8,
                }
            ],
        )
        self.assertEqual(payload["usage_summary"], usage_summary)
        self.assertEqual(payload["tasks"][0]["id"], "task-shared-1")
        self.assertEqual(payload["tasks"][0]["trace_step_count"], 3)
        self.assertEqual(payload["tasks"][0]["rag_hit_count"], 1)
        self.assertEqual(payload["tasks"][0]["trace_preview"][0]["id"], "preview-1")
        self.assertEqual(payload["stats"]["message_count"], 2)
        self.assertEqual(payload["messages"][0]["id"], "message-1")

    def test_get_session_export_response_summary_preserves_payload_messages(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )
        message_sentinel = object()
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 0},
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "message_count": 1,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [message_sentinel],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 0},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["messages"], [message_sentinel])

    def test_get_session_export_response_summary_redacts_http_json_message_content(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 0},
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "message_count": 1,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [
                        {
                            "id": "message-session-response-http-json",
                            "task_id": "task-session-response-http-json",
                            "role": "assistant",
                            "content": (
                                "Provider Status [provider_status via http_json] "
                                "failed response_path=$.data.access_token "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                            "created_at": "2026-07-21T10:02:00",
                        }
                    ],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 0},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_redacts_plain_wrapped_message_content(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 0},
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "message_count": 1,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [
                        {
                            "id": UserString("message-session-wrapped-dict"),
                            "task_id": UserString("task-session-wrapped-dict"),
                            "role": UserString("assistant"),
                            "content": UserString(
                                "Provider Status [provider_status via http_json] "
                                "failed response_path=$.data.access_token "
                                "Bearer secret-token"
                            ),
                            "created_at": UserString("2026-07-21T10:02:00"),
                        }
                    ],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 0},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertEqual(payload["messages"][0]["id"], "message-session-wrapped-dict")
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_accepts_model_dump_payload_summary(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-payload-model",
                                "prompt": "payload model prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-07-03T10:00:00",
                                "updated_at": "2026-07-03T10:01:00",
                            },
                            "usage": None,
                            "trace": {
                                "governance": {
                                    "profile": "planning_only",
                                    "provider_source": "suite_a",
                                    "allowed_tool_names": ["task_plan"],
                                    "allowed_tool_labels": ["Task Planner"],
                                },
                                "step_count": 2,
                                "rag_hit_count": 1,
                                "preview": [],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 2,
                        "rag_hit_count": 1,
                    },
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["suite_a"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "messages": [],
                }

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: ResponseReadyPayload()
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["id"], "task-payload-model")
        self.assertEqual(payload["stats"]["trace_step_count"], 2)
        self.assertEqual(payload["governance"]["profiles"], ["planning_only"])

    def test_get_session_export_response_summary_preserves_response_ready_task_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class GuardedTaskRow(dict):
            def get(self, key, default=None):
                if key in {"task", "trace"}:
                    raise AssertionError(
                        "get_session_export_response_summary should not require nested task/trace blocks when a payload task row is already response-ready"
                    )
                return super().get(key, default)

        task_governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        response_ready_task = GuardedTaskRow(
            id="task-response-ready",
            prompt="response-ready prompt",
            status="completed",
            status_normalized="normalized::completed",
            status_label="label::completed",
            status_rank=5,
            created_at="2026-06-22T16:10:00",
            updated_at="2026-06-22T16:11:00",
            usage=None,
            trace_step_count=3,
            rag_hit_count=1,
            trace_preview=[],
            governance=task_governance,
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [response_ready_task],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 3,
                        "rag_hit_count": 1,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["id"], "task-response-ready")
        self.assertEqual(payload["tasks"][0]["prompt"], "response-ready prompt")
        self.assertEqual(payload["tasks"][0]["trace_step_count"], 3)
        self.assertEqual(payload["tasks"][0]["governance"], task_governance)
        self.assertIsNot(payload["tasks"][0]["governance"], task_governance)

    def test_get_session_export_response_summary_coerces_response_ready_task_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyTaskRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        ResponseReadyTaskRow(
                            {
                                "id": "task-response-ready-model",
                                "prompt": "response-ready model prompt",
                                "status": "completed",
                                "status_normalized": "normalized::completed",
                                "status_label": "label::completed",
                                "status_rank": 5,
                                "created_at": "2026-06-22T16:10:00",
                                "updated_at": "2026-06-22T16:11:00",
                                "usage": None,
                                "trace_step_count": 4,
                                "rag_hit_count": 2,
                                "trace_preview": [],
                                "governance": task_governance,
                            }
                        )
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 4,
                        "rag_hit_count": 2,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["tasks"]), 1)
        self.assertEqual(payload["tasks"][0]["id"], "task-response-ready-model")
        self.assertEqual(payload["tasks"][0]["trace_step_count"], 4)
        self.assertEqual(payload["tasks"][0]["rag_hit_count"], 2)
        self.assertEqual(payload["tasks"][0]["governance"], task_governance)
        self.assertIsNot(payload["tasks"][0]["governance"], task_governance)

    def test_get_session_export_response_summary_coerces_nested_task_trace_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task_governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": ResponseReadyBlock(
                                {
                                    "id": "task-nested-model",
                                    "prompt": "nested model prompt",
                                    "status": "completed",
                                    "status_normalized": "normalized::completed",
                                    "status_label": "label::completed",
                                    "status_rank": 7,
                                    "created_at": "2026-06-22T16:10:00",
                                    "updated_at": "2026-06-22T16:11:00",
                                }
                            ),
                            "usage": None,
                            "trace": ResponseReadyBlock(
                                {
                                    "governance": task_governance,
                                    "step_count": 6,
                                    "rag_hit_count": 3,
                                    "preview": [
                                        {
                                            "id": "step-nested-model",
                                            "seq": 1,
                                            "type": "thought",
                                            "title": "Thought",
                                            "content_excerpt": "nested preview",
                                        }
                                    ],
                                }
                            ),
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 6,
                        "rag_hit_count": 3,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["id"], "task-nested-model")
        self.assertEqual(payload["tasks"][0]["prompt"], "nested model prompt")
        self.assertEqual(payload["tasks"][0]["trace_step_count"], 6)
        self.assertEqual(payload["tasks"][0]["rag_hit_count"], 3)
        self.assertEqual(payload["tasks"][0]["trace_preview"][0]["id"], "step-nested-model")
        self.assertEqual(payload["tasks"][0]["governance"], task_governance)
        self.assertIsNot(payload["tasks"][0]["governance"], task_governance)

    def test_get_session_export_response_summary_coerces_nested_trace_preview_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "task": ResponseReadyBlock(
                                {
                                    "id": "task-nested-preview-model",
                                    "prompt": "nested preview model prompt",
                                    "status": "completed",
                                    "status_normalized": "normalized::completed",
                                    "status_label": "label::completed",
                                    "status_rank": 8,
                                    "created_at": "2026-07-02T10:00:00",
                                    "updated_at": "2026-07-02T10:01:00",
                                }
                            ),
                            "usage": None,
                            "trace": ResponseReadyBlock(
                                {
                                    "governance": None,
                                    "step_count": 2,
                                    "rag_hit_count": 0,
                                    "preview": [
                                        ResponseReadyBlock(
                                            {
                                                "id": "preview-nested-model",
                                                "seq": 2,
                                                "type": "action",
                                                "title": "Provider Search",
                                                "content_excerpt": "preview model body",
                                            }
                                        )
                                    ],
                                }
                            ),
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 2,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["tasks"][0]["id"], "task-nested-preview-model")
        self.assertEqual(payload["tasks"][0]["trace_step_count"], 2)
        self.assertEqual(
            payload["tasks"][0]["trace_preview"][0]["id"],
            "preview-nested-model",
        )
        self.assertEqual(
            payload["tasks"][0]["trace_preview"][0]["content_excerpt"],
            "preview model body",
        )

    def test_get_session_export_response_summary_redacts_provider_trace_preview_excerpt(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "id": "task-provider-preview",
                            "prompt": "provider preview prompt",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 10,
                            "created_at": "2026-07-02T10:00:00",
                            "updated_at": "2026-07-02T10:01:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": "preview-provider-raw",
                                    "seq": 2,
                                    "type": "action",
                                    "title": "Provider Search [provider_search · knowledge_retrieval]",
                                    "content_excerpt": (
                                        "Tool done: Provider Search Preview: "
                                        "query_params.access_token Bearer secret-token"
                                    ),
                                }
                            ],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        excerpt = payload["tasks"][0]["trace_preview"][0]["content_excerpt"]
        self.assertIn("[redacted]", excerpt)
        self.assertNotIn("access_token", excerpt)
        self.assertNotIn("Bearer", excerpt)
        self.assertNotIn("secret-token", excerpt)

    def test_get_session_export_response_summary_redacts_wrapped_trace_preview_excerpt(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        class ResponseReadyPreview:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "id": "task-provider-preview-wrapped",
                            "prompt": "provider preview prompt",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 10,
                            "created_at": "2026-07-02T10:00:00",
                            "updated_at": "2026-07-02T10:01:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": UserList(
                                [
                                    ResponseReadyPreview(
                                        {
                                            "id": UserString("preview-provider-wrapped"),
                                            "seq": 2,
                                            "type": UserString("action"),
                                            "title": UserString(
                                                "Provider Search [provider_search via http_json]"
                                            ),
                                            "content_excerpt": UserString(
                                                "Tool done: Provider Search "
                                                "query_params.access_token "
                                                "Bearer secret-token"
                                            ),
                                        }
                                    )
                                ]
                            ),
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        excerpt = payload["tasks"][0]["trace_preview"][0]["content_excerpt"]
        self.assertIn("[redacted]", excerpt)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_redacts_plain_wrapped_trace_preview_excerpt(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "id": UserString("task-provider-preview-plain-wrapped"),
                            "prompt": UserString("provider preview prompt"),
                            "status": UserString("completed"),
                            "status_normalized": UserString("completed"),
                            "status_label": UserString("Completed"),
                            "status_rank": 10,
                            "created_at": UserString("2026-07-02T10:00:00"),
                            "updated_at": UserString("2026-07-02T10:01:00"),
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": UserString("preview-provider-plain-wrapped"),
                                    "seq": 2,
                                    "type": UserString("action"),
                                    "title": UserString(
                                        "Provider Search [provider_search via http_json]"
                                    ),
                                    "content_excerpt": UserString(
                                        "Tool done: Provider Search "
                                        "query_params.access_token "
                                        "Bearer secret-token"
                                    ),
                                }
                            ],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        excerpt = payload["tasks"][0]["trace_preview"][0]["content_excerpt"]
        self.assertEqual(payload["tasks"][0]["id"], "task-provider-preview-plain-wrapped")
        self.assertIn("[redacted]", excerpt)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_preserves_file_backed_real_calc_trace_preview(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_session_export_payload_summary
        )

        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {"tasks_total": 1},
                    "tasks": [
                        {
                            "id": "task-file-backed-calc-preview",
                            "prompt": "calculate from file-backed provider",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 10,
                            "created_at": "2026-07-02T10:00:00",
                            "updated_at": "2026-07-02T10:01:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": "preview-file-backed-provider-math",
                                    "seq": 3,
                                    "type": "action",
                                    "title": (
                                        "Provider Calculator "
                                        "[provider_math · local_calculator]"
                                    ),
                                    "content_excerpt": (
                                        "Calculated 8/4 = 2 "
                                        "(request id req-calc-1). "
                                        "Preview: {\"expression\":\"8/4\","
                                        "\"result\":2,\"source\":\"calculator_suite\","
                                        "\"profile\":\"calculator_only\"}"
                                    ),
                                }
                            ],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = chat_persistence_module.get_session_export_response_summary(  # type: ignore[attr-defined]
                usage_summary={"tasks_total": 1},
                task_rows=[],
                message_rows=[],
            )
        finally:
            chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        preview = payload["tasks"][0]["trace_preview"][0]
        self.assertEqual(
            preview["title"],
            "Provider Calculator [provider_math · local_calculator]",
        )
        excerpt = preview["content_excerpt"]
        self.assertIn("Calculated 8/4 = 2 (request id req-calc-1).", excerpt)
        self.assertIn('"source":"calculator_suite"', excerpt)
        self.assertIn('"profile":"calculator_only"', excerpt)
        self.assertNotIn("[redacted]", excerpt)

    def test_session_export_summary_coercion_redacts_provider_trace_preview_excerpt(
        self,
    ) -> None:
        summary = {
            "usage_summary": {"tasks_total": 1},
            "tasks": [
                {
                    "id": "task-provider-preview",
                    "prompt": "provider preview prompt",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 10,
                    "created_at": "2026-07-02T10:00:00",
                    "updated_at": "2026-07-02T10:01:00",
                    "usage": None,
                    "trace_step_count": 1,
                    "rag_hit_count": 0,
                    "trace_preview": [
                        {
                            "id": "preview-provider-raw-route",
                            "seq": 2,
                            "type": "action",
                            "title": "Provider Search [provider_search · knowledge_retrieval]",
                            "content_excerpt": (
                                "Tool done: Provider Search Preview: "
                                "query_params.access_token Bearer secret-token"
                            ),
                        }
                    ],
                    "governance": None,
                }
            ],
            "stats": {
                "task_count": 1,
                "message_count": 0,
                "trace_step_count": 1,
                "rag_hit_count": 0,
            },
            "governance": None,
            "messages": [],
        }

        normalized = session_routes_module._coerce_session_export_summary(summary)  # type: ignore[attr-defined]

        excerpt = normalized["tasks"][0]["trace_preview"][0]["content_excerpt"]
        self.assertIn("[redacted]", excerpt)
        self.assertNotIn("access_token", excerpt)
        self.assertNotIn("Bearer", excerpt)
        self.assertNotIn("secret-token", excerpt)

    def test_session_export_summary_coercion_redacts_http_json_base_model_task_trace_preview(
        self,
    ) -> None:
        summary = {
            "usage_summary": {"tasks_total": 1},
            "tasks": [
                session_routes_module.SessionExportTaskSummary(  # type: ignore[attr-defined]
                    id="task-model-preview-http-json",
                    prompt="model preview prompt",
                    status="completed",
                    status_normalized="completed",
                    status_label="Completed",
                    status_rank=10,
                    created_at="2026-07-22T11:00:00",
                    updated_at="2026-07-22T11:01:00",
                    usage=None,
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(  # type: ignore[attr-defined]
                            id="preview-model-http-json",
                            seq=2,
                            type="action",
                            title="Provider Status [provider_status via http_json]",
                            content_excerpt=(
                                "Tool done: Provider Status Preview: "
                                "response_path=$.data.access_token "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                        )
                    ],
                    governance=None,
                )
            ],
            "stats": {
                "task_count": 1,
                "message_count": 0,
                "trace_step_count": 1,
                "rag_hit_count": 0,
            },
            "governance": None,
            "messages": [],
        }

        normalized = session_routes_module._coerce_session_export_summary(summary)  # type: ignore[attr-defined]

        serialized = json.dumps(
            [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in normalized["tasks"]
            ],
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_session_export_summary_coercion_redacts_http_json_base_model_message_content(
        self,
    ) -> None:
        summary = {
            "usage_summary": {"tasks_total": 0},
            "tasks": [],
            "stats": {
                "task_count": 0,
                "message_count": 1,
                "trace_step_count": 0,
                "rag_hit_count": 0,
            },
            "governance": None,
            "messages": [
                session_routes_module.SessionExportMessage(  # type: ignore[attr-defined]
                    id="message-session-model-http-json",
                    task_id=None,
                    role="assistant",
                    content=(
                        "Provider Status [provider_status via http_json] "
                        "failed response_path=$.data.access_token "
                        "callback https://provider.example/cb?"
                        "access_token=secret-token#client_secret=hidden "
                        "Bearer secret-token"
                    ),
                    created_at="2026-07-22T09:10:00",
                )
            ],
        }

        normalized = session_routes_module._coerce_session_export_summary(summary)  # type: ignore[attr-defined]

        serialized = json.dumps(
            [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in normalized["messages"]
            ],
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
