from __future__ import annotations

from .context import *


class TaskExportResponseSummaryMixin:
    def test_get_task_export_payload_summary_reuses_shared_helpers(self) -> None:
        original_export_helper = chat_persistence_module.get_task_export_summary_from_task
        captured: list[object] = []
        task = {
            "id": "task-export-payload-summary",
            "session_id": "session-export-payload-summary",
            "prompt": "payload summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T15:00:00",
            "updated_at": "2026-06-22T15:05:00",
        }
        message_rows = [
            {
                "id": "message-1",
                "session_id": "poisoned-session",
                "task_id": "task-export-payload-summary",
                "role": "user",
                "content": "hello",
                "created_at": "2026-06-22T15:01:00",
            },
            {
                "id": "message-2",
                "session_id": "poisoned-session",
                "task_id": "task-export-payload-summary",
                "role": "assistant",
                "content": "world",
                "created_at": "2026-06-22T15:02:00",
            },
        ]
        try:
            chat_persistence_module.get_task_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(raw_task)
                or {
                    "task": {
                        "id": "task-export-payload-summary",
                        "session_id": "session-export-payload-summary",
                        "prompt": "payload summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 31,
                        "created_at": "2026-06-22T15:00:00",
                        "updated_at": "2026-06-22T15:05:00",
                    },
                    "usage": {"prompt_tokens": 2},
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_payload_summary(  # type: ignore[attr-defined]
                task,
                message_rows,
            )
        finally:
            chat_persistence_module.get_task_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, [task])
        self.assertEqual(
            payload,
            {
                "task": {
                    "id": "task-export-payload-summary",
                    "session_id": "session-export-payload-summary",
                    "prompt": "payload summary prompt",
                    "status": "completed",
                    "status_normalized": "normalized::completed",
                    "status_label": "label::completed",
                    "status_rank": 31,
                    "created_at": "2026-06-22T15:00:00",
                    "updated_at": "2026-06-22T15:05:00",
                },
                "usage": {"prompt_tokens": 2},
                "trace": {
                    "governance": None,
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                },
                "messages": [
                    {
                        "id": "message-1",
                        "role": "user",
                        "content": "hello",
                        "created_at": "2026-06-22T15:01:00",
                    },
                    {
                        "id": "message-2",
                        "role": "assistant",
                        "content": "world",
                        "created_at": "2026-06-22T15:02:00",
                    },
                ],
            },
        )

    def test_get_task_export_payload_summary_coerces_model_message_rows(self) -> None:
        original_export_helper = chat_persistence_module.get_task_export_summary_from_task

        class ResponseReadyMessageRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-payload-model-message",
                        "session_id": "session-export-payload-model-message",
                        "prompt": "payload summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 31,
                        "created_at": "2026-07-02T11:20:00",
                        "updated_at": "2026-07-02T11:21:00",
                    },
                    "usage": {"prompt_tokens": 2},
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_payload_summary(  # type: ignore[attr-defined]
                {"id": "task-export-payload-model-message"},
                (
                    ResponseReadyMessageRow(
                        {
                            "id": "message-model-1",
                            "role": "assistant",
                            "content": "hello",
                            "created_at": "2026-07-02T11:22:00",
                        }
                    ),
                ),
            )
        finally:
            chat_persistence_module.get_task_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["messages"],
            [
                {
                    "id": "message-model-1",
                    "role": "assistant",
                    "content": "hello",
                    "created_at": "2026-07-02T11:22:00",
                }
            ],
        )

    def test_get_task_export_payload_summary_redacts_http_json_message_content(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_export_summary_from_task

        try:
            chat_persistence_module.get_task_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-payload-http-json-message",
                        "session_id": "session-export-payload-http-json-message",
                        "prompt": "payload summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 31,
                        "created_at": "2026-07-21T09:20:00",
                        "updated_at": "2026-07-21T09:21:00",
                    },
                    "usage": None,
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_payload_summary(  # type: ignore[attr-defined]
                {"id": "task-export-payload-http-json-message"},
                [
                    {
                        "id": "message-http-json-payload",
                        "role": "assistant",
                        "content": (
                            "Provider Search [provider_search via http_json] "
                            "failed response_path=$.data.access_token "
                            "callback https://provider.example/cb?"
                            "access_token=secret-token#client_secret=hidden "
                            "Bearer secret-token"
                        ),
                        "created_at": "2026-07-21T09:22:00",
                    }
                ],
            )
        finally:
            chat_persistence_module.get_task_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_payload_summary_redacts_plain_wrapped_message_rows(
        self,
    ) -> None:
        original_export_helper = chat_persistence_module.get_task_export_summary_from_task

        try:
            chat_persistence_module.get_task_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-payload-plain-message",
                        "session_id": "session-export-payload-plain-message",
                        "prompt": "payload summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 31,
                        "created_at": "2026-07-21T09:20:00",
                        "updated_at": "2026-07-21T09:21:00",
                    },
                    "usage": None,
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_payload_summary(  # type: ignore[attr-defined]
                {"id": "task-export-payload-plain-message"},
                [
                    {
                        "id": UserString("message-task-payload-plain"),
                        "role": UserString("assistant"),
                        "content": UserString(
                            "Provider Search [provider_search via http_json] "
                            "failed response_path=$.data.access_token "
                            "Bearer secret-token"
                        ),
                        "created_at": UserString("2026-07-21T09:22:00"),
                    }
                ],
            )
        finally:
            chat_persistence_module.get_task_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertEqual(payload["messages"][0]["id"], "message-task-payload-plain")
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_plain_clones_governance_dict(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class GuardedGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_task_export_response_summary should plain-clone trace governance dicts before outward model validation"
                )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-summary",
                        "session_id": "session-export-response-summary",
                        "prompt": "export response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 19,
                        "created_at": "2026-06-22T21:00:00",
                        "updated_at": "2026-06-22T21:05:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": GuardedGovernanceDict(
                            profile="planning_only",
                            provider_source="planning_suite",
                            allowed_tool_names=["task_plan"],
                            allowed_tool_labels=["Task Planner Suite"],
                        ),
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-summary"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertIsInstance(payload["trace"]["governance"], dict)
        self.assertNotIsInstance(
            payload["trace"]["governance"],
            GuardedGovernanceDict,
        )
        self.assertEqual(
            payload["trace"]["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_task_export_response_summary_coerces_governance_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        trace_governance = ResponseReadyGovernance(
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-governance-model",
                        "session_id": "session-export-governance-model",
                        "prompt": "export governance model prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 19,
                        "created_at": "2026-06-22T21:00:00",
                        "updated_at": "2026-06-22T21:05:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": trace_governance,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-governance-model"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertIsInstance(payload["trace"]["governance"], dict)
        self.assertIsNot(payload["trace"]["governance"], trace_governance)
        self.assertEqual(
            payload["trace"]["governance"]["profile"],
            "planning_only",
        )

    def test_get_task_export_response_summary_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        trace_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-governance-source",
                        "session_id": "session-export-governance-source",
                        "prompt": "export governance source prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 19,
                        "created_at": "2026-06-22T21:00:00",
                        "updated_at": "2026-06-22T21:05:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": trace_governance,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-governance-source"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace"]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_task_export_response_summary_reuses_shared_payload_helper(self) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )
        captured: list[tuple[object, object]] = []
        task = {
            "id": "task-export-response-summary",
            "session_id": "session-export-response-summary",
            "prompt": "poisoned prompt",
            "status": "poisoned_status",
            "created_at": "poisoned_created_at",
            "updated_at": "poisoned_updated_at",
        }
        message_rows = [
            {
                "id": "message-1",
                "role": "assistant",
                "content": "hello",
                "created_at": "2026-06-22T16:00:00",
            }
        ]
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda raw_task, rows: captured.append((raw_task, rows))
                or {
                    "task": {
                        "id": "task-export-response-summary",
                        "session_id": "session-export-response-summary",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": {"prompt_tokens": 3},
                    "messages": message_rows,
                    "trace": {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_a",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                        "steps": [
                            chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                                id="step-1",
                                type="thought",
                                content="trace body",
                                seq=1,
                            )
                        ],
                        "step_count": 1,
                        "rag_hit_count": 2,
                        "rag_knowledge_base_ids": ["kb-1"],
                        "rag_chunks": [
                            {
                                "step_id": "step-1",
                                "knowledge_base_id": "kb-1",
                                "content": "chunk body",
                            }
                        ],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                task,
                message_rows,
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, [(task, message_rows)])
        self.assertEqual(payload["task"]["prompt"], "shared prompt")
        self.assertEqual(payload["trace"]["step_count"], 1)
        self.assertEqual(payload["trace"]["rag_hit_count"], 2)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(payload["messages"], message_rows)

    def test_get_task_export_response_summary_accepts_model_dump_payload_summary(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "task": {
                        "id": "task-export-payload-model",
                        "session_id": "session-export-payload-model",
                        "prompt": "payload summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 11,
                        "created_at": "2026-07-03T10:10:00",
                        "updated_at": "2026-07-03T10:11:00",
                    },
                    "usage": {"prompt_tokens": 3},
                    "messages": [],
                    "trace": {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_a",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                        "steps": [],
                        "step_count": 2,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-1"],
                        "rag_chunks": [],
                    },
                }

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-payload-model"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["task"]["id"], "task-export-payload-model")
        self.assertEqual(payload["trace"]["step_count"], 2)
        self.assertEqual(payload["trace"]["governance"]["profile"], "planning_only")

    def test_get_task_export_response_summary_preserves_payload_task_and_messages(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class GuardedTaskSummary(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_task_export_response_summary should pass payload task summary through instead of re-reading task fields"
                )

        task_summary = GuardedTaskSummary(
            id="task-export-response-summary",
            session_id="session-export-response-summary",
            prompt="shared prompt",
            status="completed",
            status_normalized="normalized::completed",
            status_label="label::completed",
            status_rank=9,
            created_at="2026-06-22T16:01:00",
            updated_at="2026-06-22T16:02:00",
        )
        message_sentinel = object()
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": task_summary,
                    "usage": None,
                    "messages": [message_sentinel],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-summary"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertIs(payload["task"], task_summary)
        self.assertEqual(payload["messages"], [message_sentinel])

    def test_get_task_export_response_summary_redacts_http_json_message_content(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-http-json-message",
                        "session_id": "session-export-response-http-json-message",
                        "prompt": "response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-21T10:00:00",
                        "updated_at": "2026-07-21T10:01:00",
                    },
                    "usage": None,
                    "messages": [
                        {
                            "id": "message-task-response-http-json",
                            "role": "assistant",
                            "content": (
                                "Provider Search [provider_search via http_json] "
                                "failed response_path=$.data.access_token "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                            "created_at": "2026-07-21T10:02:00",
                        }
                    ],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-http-json-message"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_redacts_wrapped_message_content(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyMessage:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-wrapped-message",
                        "session_id": "session-export-response-wrapped-message",
                        "prompt": "response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-21T10:00:00",
                        "updated_at": "2026-07-21T10:01:00",
                    },
                    "usage": None,
                    "messages": UserList(
                        [
                            ResponseReadyMessage(
                                {
                                    "id": UserString("message-task-response-wrapped"),
                                    "role": UserString("assistant"),
                                    "content": UserString(
                                        "Provider Search "
                                        "[provider_search via http_json] "
                                        "failed response_path=$.data.access_token "
                                        "Bearer secret-token"
                                    ),
                                    "created_at": UserString("2026-07-21T10:02:00"),
                                }
                            )
                        ]
                    ),
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-wrapped-message"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_redacts_plain_wrapped_message_content(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-plain-wrapped-message",
                        "session_id": "session-export-response-plain-wrapped-message",
                        "prompt": "response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-21T10:00:00",
                        "updated_at": "2026-07-21T10:01:00",
                    },
                    "usage": None,
                    "messages": [
                        {
                            "id": UserString("message-task-response-plain-wrapped"),
                            "role": UserString("assistant"),
                            "content": UserString(
                                "Provider Search "
                                "[provider_search via http_json] "
                                "failed response_path=$.data.access_token "
                                "Bearer secret-token"
                            ),
                            "created_at": UserString("2026-07-21T10:02:00"),
                        }
                    ],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-plain-wrapped-message"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["messages"], ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertEqual(
            payload["messages"][0]["id"],
            "message-task-response-plain-wrapped",
        )
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_preserves_response_ready_trace_models(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyTrace:
            def __init__(self, payload):
                self._payload = payload

            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_task_export_response_summary should not require dict-only trace blocks when payload trace is already response-ready"
                )

            def model_dump(self):
                return dict(self._payload)

        trace_governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-ready-trace",
                        "session_id": "session-export-response-ready-trace",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": ResponseReadyTrace(
                        {
                            "governance": trace_governance,
                            "steps": [
                                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                                    id="step-response-ready",
                                    type="thought",
                                    content="ready trace body",
                                    seq=1,
                                )
                            ],
                            "step_count": 1,
                            "rag_hit_count": 2,
                            "rag_knowledge_base_ids": ["kb-ready"],
                            "rag_chunks": [
                                {
                                    "step_id": "step-response-ready",
                                    "knowledge_base_id": "kb-ready",
                                    "content": "ready chunk",
                                }
                            ],
                        }
                    ),
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-ready-trace"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["trace"]["step_count"], 1)
        self.assertEqual(payload["trace"]["rag_hit_count"], 2)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-ready"])
        self.assertEqual(payload["trace"]["rag_chunks"][0]["content"], "ready chunk")
        self.assertEqual(payload["trace"]["governance"], trace_governance)
        self.assertIsNot(payload["trace"]["governance"], trace_governance)

    def test_get_task_export_response_summary_coerces_model_rag_chunks(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class ResponseReadyTrace:
            def model_dump(self):
                return {
                    "governance": None,
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 1,
                    "rag_knowledge_base_ids": ["kb-model"],
                    "rag_chunks": (
                        ResponseReadyChunk(
                            {
                                "step_id": "step-model-rag-response",
                                "knowledge_base_id": "kb-model",
                                "content": "chunk-model",
                            }
                        ),
                    ),
                }

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-model-rag",
                        "session_id": "session-export-response-model-rag",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": ResponseReadyTrace(),
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-model-rag"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace"]["rag_chunks"],
            [
                {
                    "step_id": "step-model-rag-response",
                    "knowledge_base_id": "kb-model",
                    "content": "chunk-model",
                }
            ],
        )

    def test_get_task_export_response_summary_redacts_provider_rag_chunk_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-rag-redact",
                        "session_id": "session-export-response-rag-redact",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-provider"],
                        "rag_chunks": [
                            {
                                "step_id": "step-provider-rag",
                                "knowledge_base_id": "kb-provider",
                                "content": (
                                    "Matched snippet query_params.access_token "
                                    "Bearer secret-token"
                                ),
                            }
                        ],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-rag-redact"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized_chunks = json.dumps(
            payload["trace"]["rag_chunks"],
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized_chunks)
        self.assertNotIn("access_token", serialized_chunks)
        self.assertNotIn("Bearer", serialized_chunks)
        self.assertNotIn("secret-token", serialized_chunks)

    def test_get_task_export_response_summary_redacts_wrapped_rag_chunk_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-wrapped-rag",
                        "session_id": "session-export-response-wrapped-rag",
                        "prompt": "response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-21T10:00:00",
                        "updated_at": "2026-07-21T10:01:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": UserList([UserString("kb-1")]),
                        "rag_chunks": UserList(
                            [
                                ResponseReadyChunk(
                                    {
                                        "step_id": UserString("step-rag-1"),
                                        "knowledge_base_id": UserString("kb-1"),
                                        "content": UserString(
                                            "chunk query_params.access_token "
                                            "Bearer secret-token"
                                        ),
                                    }
                                )
                            ]
                        ),
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-wrapped-rag"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["trace"], ensure_ascii=False)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["trace"]["rag_chunks"][0]["content"],
            "chunk [redacted] [redacted]",
        )
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_redacts_plain_wrapped_rag_chunk_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-plain-wrapped-rag",
                        "session_id": "session-export-response-plain-wrapped-rag",
                        "prompt": "response summary prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-21T10:00:00",
                        "updated_at": "2026-07-21T10:01:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": [UserString("kb-plain")],
                        "rag_chunks": [
                            {
                                "step_id": UserString("step-rag-plain"),
                                "knowledge_base_id": UserString("kb-plain"),
                                "content": UserString(
                                    "chunk query_params.access_token "
                                    "Bearer secret-token"
                                ),
                            }
                        ],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-plain-wrapped-rag"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload["trace"], ensure_ascii=False)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-plain"])
        self.assertEqual(
            payload["trace"]["rag_chunks"][0]["content"],
            "chunk [redacted] [redacted]",
        )
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_coerces_model_dump_trace_step_dicts(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyTrace:
            def model_dump(self):
                return {
                    "governance": None,
                    "steps": [
                        {
                            "id": "step-dumped-dict",
                            "type": "thought",
                            "content": "dumped trace body",
                            "seq": 7,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-dumped-trace",
                        "session_id": "session-export-dumped-trace",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": ResponseReadyTrace(),
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-dumped-trace"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertIsInstance(
            payload["trace"]["steps"][0],
            chat_persistence_module.TraceStep,  # type: ignore[attr-defined]
        )
        self.assertEqual(payload["trace"]["steps"][0].id, "step-dumped-dict")
        self.assertEqual(payload["trace"]["steps"][0].seq, 7)

    def test_get_task_export_response_summary_coerces_model_trace_step_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyTraceStepRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-model-step-row",
                        "session_id": "session-export-model-step-row",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-02T11:30:00",
                        "updated_at": "2026-07-02T11:31:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": (
                            ResponseReadyTraceStepRow(
                                {
                                    "id": "step-model-row",
                                    "type": "thought",
                                    "content": "model step body",
                                    "seq": 3,
                                }
                            ),
                        ),
                        "step_count": 1,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-model-step-row"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertEqual(payload["trace"]["steps"][0].id, "step-model-row")
        self.assertEqual(payload["trace"]["steps"][0].content, "model step body")

    def test_get_task_export_response_summary_coerces_wrapped_trace_step_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        class ResponseReadyTraceStepRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-wrapped-step-row",
                        "session_id": "session-export-wrapped-step-row",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-02T11:30:00",
                        "updated_at": "2026-07-02T11:31:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": UserList(
                            [
                                ResponseReadyTraceStepRow(
                                    {
                                        "id": UserString("step-wrapped-row"),
                                        "type": UserString("action"),
                                        "content": UserString(
                                            "Tool done: Provider Search "
                                            "query_params.access_token "
                                            "Bearer secret-token"
                                        ),
                                        "seq": 4,
                                        "meta": {
                                            "tool": {
                                                "name": "provider_search",
                                                "label": "Provider Search",
                                                "status": "done",
                                                "input": {
                                                    "query_params": {
                                                        "access_token": "top-secret",
                                                    }
                                                },
                                            }
                                        },
                                    }
                                )
                            ]
                        ),
                        "step_count": 1,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-wrapped-step-row"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized_steps = json.dumps(
            [step.model_dump() for step in payload["trace"]["steps"]],
            ensure_ascii=False,
        )
        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertIn("[redacted]", serialized_steps)
        self.assertNotIn("access_token", payload["trace"]["steps"][0].content)
        self.assertNotIn("Bearer", serialized_steps)
        self.assertNotIn("secret-token", serialized_steps)
        self.assertNotIn("top-secret", serialized_steps)

    def test_get_task_export_response_summary_coerces_plain_wrapped_trace_step_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-plain-wrapped-step-row",
                        "session_id": "session-export-plain-wrapped-step-row",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-02T11:30:00",
                        "updated_at": "2026-07-02T11:31:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": [
                            {
                                "id": UserString("step-plain-wrapped-row"),
                                "type": UserString("action"),
                                "content": UserString(
                                    "Tool done: Provider Search "
                                    "query_params.access_token "
                                    "Bearer secret-token"
                                ),
                                "seq": 4,
                                "meta": {
                                    "tool": {
                                        "name": UserString("provider_search"),
                                        "label": UserString("Provider Search"),
                                        "status": UserString("done"),
                                        "input": {
                                            "query_params": {
                                                "access_token": UserString("top-secret"),
                                            }
                                        },
                                    }
                                },
                            }
                        ],
                        "step_count": 1,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-plain-wrapped-step-row"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        serialized_steps = json.dumps(
            [step.model_dump() for step in payload["trace"]["steps"]],
            ensure_ascii=False,
        )
        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertEqual(payload["trace"]["steps"][0].id, "step-plain-wrapped-row")
        self.assertIn("[redacted]", serialized_steps)
        self.assertNotIn("access_token", payload["trace"]["steps"][0].content)
        self.assertNotIn("Bearer", serialized_steps)
        self.assertNotIn("secret-token", serialized_steps)
        self.assertNotIn("top-secret", serialized_steps)

    def test_get_task_export_response_summary_redacts_provider_trace_step_rows(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-provider-step-row",
                        "session_id": "session-export-provider-step-row",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-07-02T11:30:00",
                        "updated_at": "2026-07-02T11:31:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "steps": [
                            {
                                "id": "step-provider-row",
                                "type": "action",
                                "content": (
                                    "Tool done: Provider Search Preview: "
                                    "query_params.access_token Bearer secret-token"
                                ),
                                "seq": 3,
                                "meta": {
                                    "tool": {
                                        "name": "provider_search",
                                        "label": "Provider Search",
                                        "status": "done",
                                        "input": {
                                            "query_params": {
                                                "access_token": "top-secret",
                                            }
                                        },
                                    }
                                },
                            }
                        ],
                        "step_count": 1,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-provider-step-row"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        step = payload["trace"]["steps"][0]
        serialized_step = json.dumps(step.model_dump(exclude_none=True), ensure_ascii=False)
        self.assertIn("[redacted]", serialized_step)
        self.assertNotIn("Bearer", serialized_step)
        self.assertNotIn("secret-token", serialized_step)
        self.assertNotIn("top-secret", serialized_step)

    def test_task_export_summary_coercion_redacts_provider_trace_step_rows(
        self,
    ) -> None:
        summary = {
            "task": {
                "id": "task-export-route-provider-step",
                "session_id": "session-export-route-provider-step",
                "prompt": "shared prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 9,
                "created_at": "2026-07-02T11:30:00",
                "updated_at": "2026-07-02T11:31:00",
            },
            "usage": None,
            "messages": [],
            "trace": {
                "governance": None,
                "steps": [
                    {
                        "id": "step-provider-route-row",
                        "type": "action",
                        "content": (
                            "Tool done: Provider Search Preview: "
                            "query_params.access_token Bearer secret-token"
                        ),
                        "seq": 3,
                        "meta": {
                            "tool": {
                                "name": "provider_search",
                                "label": "Provider Search",
                                "status": "done",
                                "input": {
                                    "query_params": {
                                        "access_token": "top-secret",
                                    }
                                },
                            }
                        },
                    }
                ],
                "step_count": 1,
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            },
        }

        normalized = task_routes_module._coerce_task_export_summary(summary)  # type: ignore[attr-defined]

        response = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-02T11:32:00",
            **normalized,
        )
        serialized_step = json.dumps(
            response.trace.steps[0].model_dump(exclude_none=True),
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized_step)
        self.assertNotIn("Bearer", serialized_step)
        self.assertNotIn("secret-token", serialized_step)
        self.assertNotIn("top-secret", serialized_step)

    def test_task_export_summary_coercion_redacts_provider_rag_chunk_rows(
        self,
    ) -> None:
        summary = {
            "task": {
                "id": "task-export-route-provider-rag",
                "session_id": "session-export-route-provider-rag",
                "prompt": "shared prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 9,
                "created_at": "2026-07-02T11:30:00",
                "updated_at": "2026-07-02T11:31:00",
            },
            "usage": None,
            "messages": [],
            "trace": {
                "governance": None,
                "steps": [],
                "step_count": 0,
                "rag_hit_count": 1,
                "rag_knowledge_base_ids": ["kb-provider"],
                "rag_chunks": [
                    {
                        "step_id": "step-provider-rag-route",
                        "knowledge_base_id": "kb-provider",
                        "content": (
                            "Matched snippet query_params.access_token "
                            "Bearer secret-token"
                        ),
                    }
                ],
            },
        }

        normalized = task_routes_module._coerce_task_export_summary(summary)  # type: ignore[attr-defined]

        response = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-02T11:32:00",
            **normalized,
        )
        serialized_chunks = json.dumps(
            [chunk.model_dump(exclude_none=True) for chunk in response.trace.rag_chunks],
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized_chunks)
        self.assertNotIn("access_token", serialized_chunks)
        self.assertNotIn("Bearer", serialized_chunks)
        self.assertNotIn("secret-token", serialized_chunks)

    def test_task_export_summary_coercion_redacts_http_json_base_model_trace_rag_chunks(
        self,
    ) -> None:
        summary = {
            "task": {
                "id": "task-export-route-model-trace-rag",
                "session_id": "session-export-route-model-trace-rag",
                "prompt": "shared prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 9,
                "created_at": "2026-07-22T10:20:00",
                "updated_at": "2026-07-22T10:21:00",
            },
            "usage": None,
            "messages": [],
            "trace": task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=0,
                rag_hit_count=1,
                rag_knowledge_base_ids=["kb-http-json"],
                rag_chunks=[
                    task_routes_module.TaskExportRagChunk(  # type: ignore[attr-defined]
                        step_id="step-model-trace-rag",
                        knowledge_base_id="kb-http-json",
                        content=(
                            "Matched snippet query_params.access_token "
                            "response_path=$.data.access_token "
                            "Bearer secret-token"
                        ),
                    )
                ],
                steps=[],
            ),
        }

        normalized = task_routes_module._coerce_task_export_summary(summary)  # type: ignore[attr-defined]

        response = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-22T10:23:00",
            **normalized,
        )
        serialized = response.model_dump_json()
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_task_export_summary_coercion_redacts_http_json_base_model_message_content(
        self,
    ) -> None:
        summary = {
            "task": {
                "id": "task-export-route-model-message",
                "session_id": "session-export-route-model-message",
                "prompt": "shared prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 9,
                "created_at": "2026-07-22T09:20:00",
                "updated_at": "2026-07-22T09:21:00",
            },
            "usage": None,
            "messages": [
                task_routes_module.TaskExportMessage(  # type: ignore[attr-defined]
                    id="message-task-model-http-json",
                    role="assistant",
                    content=(
                        "Provider Search [provider_search via http_json] "
                        "failed response_path=$.data.access_token "
                        "callback https://provider.example/cb?"
                        "access_token=secret-token#client_secret=hidden "
                        "Bearer secret-token"
                    ),
                    created_at="2026-07-22T09:22:00",
                )
            ],
            "trace": {
                "governance": None,
                "steps": [],
                "step_count": 0,
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            },
        }

        normalized = task_routes_module._coerce_task_export_summary(summary)  # type: ignore[attr-defined]

        response = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-22T09:23:00",
            **normalized,
        )
        serialized = response.model_dump_json()
        self.assertIn("[redacted]", serialized)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_export_response_summary_accepts_tuple_trace_steps(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )
        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-tuple-steps",
                        "session_id": "session-export-tuple-steps",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 9,
                        "created_at": "2026-06-22T16:01:00",
                        "updated_at": "2026-06-22T16:02:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "step_count": 2,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": (
                            {
                                "id": "step-tuple-dict",
                                "type": "thought",
                                "content": "tuple dict body",
                                "seq": 3,
                            },
                            chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                                id="step-tuple-model",
                                type="thought",
                                content="tuple model body",
                                seq=4,
                            ),
                        ),
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-tuple-steps"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["trace"]["steps"]), 2)
        self.assertEqual(payload["trace"]["steps"][0].id, "step-tuple-dict")
        self.assertEqual(payload["trace"]["steps"][1].id, "step-tuple-model")

    def test_coerce_export_payload_block_list_to_dicts_accepts_tuple(
        self,
    ) -> None:
        class ResponseReadyRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chat_persistence_module._coerce_export_payload_block_list_to_dicts(  # type: ignore[attr-defined]
            (
                {"day": "2026-06-22", "tokens": 3},
                ResponseReadyRow({"day": "2026-06-23", "tokens": 5}),
            )
        )

        self.assertEqual(
            payload,
            [
                {"day": "2026-06-22", "tokens": 3},
                {"day": "2026-06-23", "tokens": 5},
            ],
        )
