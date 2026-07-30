from __future__ import annotations

from .context import *


class RegistryRuntimeModelsMixin:
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

    def test_build_tool_registry_diagnostics_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertEqual(result.summary.total, 2)
        self.assertEqual(result.trace_step["id"], "step-1")
        self.assertEqual(result.trace_event["step_id"], "step-1")
        self.assertEqual(result.audit_detail["provider_source"], "file_source")

    def test_tool_registry_diagnostics_runtime_artifacts_model_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-diagnostics-model-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-diagnostics-model-http-json-output",
            "step": raw_step,
        }
        model = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=raw_step,
            trace_event=trace_event,
            audit_detail={"trace": trace_event},
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_tool_registry_diagnostics_runtime_artifacts_model_redacts_http_json_wrapper_step_and_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-diagnostics-model-http-json-wrapper-output"
        )
        followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-diagnostics-model-http-json-wrapper-output",
            content="Retrieved snippets",
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-diagnostics-model-http-json-wrapper-output",
            "step": raw_step,
        }
        followup_trace = {
            "task_id": "task-1",
            "step_id": "rag-diagnostics-model-http-json-wrapper-output",
            "step": followup_step,
        }
        model = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=raw_step,
            trace_event=trace_event,
            audit_detail={
                "rag_followup": {
                    "step": followup_step,
                    "trace": followup_trace,
                },
            },
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_registry_diagnostics_runtime_artifacts_keeps_empty_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="default",
            diagnostics=diagnostics,
        )

        self.assertEqual(
            result["summary"],
            {
                "has_diagnostics": False,
                "skipped_total": 0,
                "missing_total": 0,
                "total": 0,
                "entries": (),
            },
        )
        self.assertIsNone(result["trace_step"])
        self.assertIsNone(result["trace_event"])
        self.assertIsNone(result["audit_detail"])

    def test_build_tool_registry_diagnostics_audit_event_keeps_shape(self) -> None:
        diagnostics_runtime = {
            "summary": {
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
            "trace_step": None,
            "trace_event": None,
            "audit_detail": {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        }

        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime=diagnostics_runtime
        )

        self.assertEqual(
            result,
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": diagnostics_runtime["audit_detail"],
            },
        )

    def test_build_tool_registry_diagnostics_audit_event_returns_none_without_audit_detail(
        self,
    ) -> None:
        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime={
                "summary": {
                    "has_diagnostics": False,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
                "trace_step": None,
                "trace_event": None,
                "audit_detail": None,
            }
        )

        self.assertIsNone(result)

    def test_build_tool_registry_diagnostics_audit_service_action_keeps_shape(self) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "Tool registry diagnostics detected during configured provider resolution.",
            "detail": {
                "provider_source": "file_source",
                "missing_total": 1,
            },
        }

        result = build_tool_registry_diagnostics_audit_service_action(
            audit_event=audit_event
        )

        self.assertEqual(
            result,
            {
                "kind": "record_audit_event",
                "kwargs": audit_event,
            },
        )

    def test_build_tool_registry_diagnostics_trace_service_action_keeps_shape(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action(
            trace_step=trace_step,
            trace_event=trace_event,
        )

        self.assertEqual(
            result,
            {
                "kind": "internal_trace_write",
                "trace_step": trace_step,
                "trace_event": trace_event,
                "persist_force": True,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_keeps_shape(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            }
        }

        result = build_configured_tool_registry_provider_runtime_service_actions(
            runtime_artifacts=runtime_artifacts
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "internal_trace_write",
                    "trace_step": runtime_artifacts["diagnostics_runtime"]["trace_step"],
                    "trace_event": runtime_artifacts["diagnostics_runtime"]["trace_event"],
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": runtime_artifacts["audit_event"],
                },
            ],
        )

    def test_build_task_export_payload_reuses_shared_task_export_response_summary_helper(
        self,
    ) -> None:
        task = {
            "id": "task-export-payload-helper",
            "session_id": "session-export-payload-helper",
            "prompt": "poisoned prompt",
            "status": "poisoned_status",
            "created_at": "poisoned_created_at",
            "updated_at": "poisoned_updated_at",
            "trace_json": "poisoned_trace_json",
            "usage_json": "poisoned_usage_json",
        }
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_payload_summary",
            None,
        )
        captured: list[object] = []
        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: [
                {
                    "id": "message-1",
                    "session_id": "poisoned-session",
                    "task_id": "task-export-payload-helper",
                    "role": "assistant",
                    "content": "message body",
                    "created_at": "2026-06-22T15:31:00",
                }
            ]
            task_routes_module.chat_persistence_service.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) instead of calling get_task_export_payload_summary(task, message_rows) directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda raw_task, message_rows: captured.append((raw_task, message_rows))
                or {
                    "task": {
                        "id": "task-export-payload-helper",
                        "session_id": "session-export-payload-helper",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 12,
                        "created_at": "2026-06-22T15:30:00",
                        "updated_at": "2026-06-22T15:35:00",
                    },
                    "usage": {"prompt_tokens": 5},
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
                        "rag_chunks": [
                            {
                                "step_id": "step-1",
                                "knowledge_base_id": "kb-1",
                                "content": "chunk body",
                            }
                        ],
                    },
                    "messages": [
                        {
                            "id": "message-1",
                            "role": "assistant",
                            "content": "message body",
                            "created_at": "2026-06-22T15:31:00",
                        }
                    ],
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-payload-helper",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_payload_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_payload_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], task)
        self.assertEqual(
            captured[0][1],
            [
                {
                    "id": "message-1",
                    "session_id": "poisoned-session",
                    "task_id": "task-export-payload-helper",
                    "role": "assistant",
                    "content": "message body",
                    "created_at": "2026-06-22T15:31:00",
                }
            ],
        )
        self.assertEqual(payload.task.prompt, "shared prompt")
        self.assertEqual(payload.trace.step_count, 2)
        self.assertEqual(payload.trace.rag_hit_count, 1)
        self.assertEqual(payload.messages[0].id, "message-1")

    def test_build_task_export_payload_redacts_http_json_message_content(
        self,
    ) -> None:
        task = {
            "id": "task-export-route-http-json-message",
            "session_id": "session-export-route-http-json-message",
            "prompt": "task export http json message",
            "status": "completed",
            "created_at": "2026-07-20T11:00:00",
            "updated_at": "2026-07-20T11:01:00",
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: {
                    "task": {
                        "id": "task-export-route-http-json-message",
                        "session_id": "session-export-route-http-json-message",
                        "prompt": "task export http json message",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-20T11:00:00",
                        "updated_at": "2026-07-20T11:01:00",
                    },
                    "usage": None,
                    "messages": [
                        {
                            "id": "message-task-export-http-json",
                            "role": "assistant",
                            "content": (
                                "Provider Status [provider_status via http_json] "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                            "created_at": "2026-07-20T11:01:00",
                        }
                    ],
                    "trace": {
                        "governance": None,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-task-export-route-http-json-message",
            )
            markdown = task_routes_module._build_task_export_markdown(payload)  # type: ignore[attr-defined]
        finally:
            task_routes_module.get_task_messages = original_get_task_messages
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        combined = f"{payload.model_dump_json()}\n{markdown}"
        self.assertIn("[redacted]", combined)
        self.assertIn("callback", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("secret-token", combined)
        self.assertNotIn("Bearer", combined)

    def test_build_configured_tool_registry_provider_runtime_service_actions_uses_model_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[bool, bool]] = []

        def record_helper(
            *,
            runtime_artifacts: dict[str, object],
        ) -> object:
            captured.append(
                (
                    isinstance(runtime_artifacts.get("diagnostics_runtime"), dict),
                    isinstance(runtime_artifacts.get("audit_event"), dict),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions(
                runtime_artifacts=runtime_artifacts
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [(True, True)])
        self.assertEqual(
            tuple(item["kind"] for item in result),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_redacts_raw_diagnostics(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "content": (
                            "provider_search: unsupported tool execution kind api_key=hidden"
                        ),
                    },
                    "trace_event": {
                        "step": {
                            "content": (
                                "provider_search: http_json execution query_params.access_token must be safe"
                            ),
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "detail": {
                            "entries": (
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": (
                                        "provider_search: http_json execution headers.x-api-key must be safe",
                                    ),
                                },
                            ),
                        },
                    },
                },
            ],
        )

        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_runtime_service_action_model_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-service-action-model-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-service-action-model-http-json-output",
            "step": raw_step,
        }
        model = tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionModel(
            kind="internal_trace_write",
            trace_step=raw_step,
            trace_event=trace_event,
            persist_force=True,
            kwargs={"trace_step": raw_step, "trace_event": trace_event},
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_runtime_service_action_model_from_dict_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-service-action-from-dict-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-service-action-from-dict-http-json-output",
            "step": raw_step,
        }
        model = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": raw_step,
                "trace_event": trace_event,
                "persist_force": True,
                "kwargs": {"trace_step": raw_step, "trace_event": trace_event},
            }
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_records_audit(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            }
        ]

        result = execute_configured_tool_registry_provider_runtime_service_actions(
            service_actions=service_actions,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result_model, result_dict = execute_configured_tool_registry_provider_runtime_service_actions_outputs(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])

    def test_build_configured_tool_registry_provider_runtime_artifacts_exposes_selected_source_runtime_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            artifacts = build_configured_tool_registry_provider_runtime_artifacts(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(
            artifacts["diagnostics_runtime"]["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-registry",
                "step": artifacts["diagnostics_runtime"]["trace_step"],
            },
        )
        self.assertEqual(
            artifacts["audit_event"],
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": artifacts["diagnostics_runtime"]["audit_detail"],
            },
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_runtime_artifacts_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.audit_event["event_type"], "tool_registry_diagnostics")
        self.assertEqual(tuple(sorted(result.provider.load_tool_registry())), ("calc_eval_fast",))

    def test_build_configured_tool_registry_provider_service_execution_keeps_shape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            [item["kind"] for item in result["service_actions"]],
            ["internal_trace_write", "record_audit_event"],
        )
        self.assertEqual(
            result["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )

    def test_build_configured_tool_registry_provider_service_execution_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_execute_configured_tool_registry_provider_service_execution_applies_actions(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }

        result = execute_configured_tool_registry_provider_service_execution(
            service_execution=service_execution,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_execution["service_actions"][0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(audit_calls, [service_execution["service_actions"][1]["kwargs"]])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_execute_configured_tool_registry_provider_service_execution_uses_outputs_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    len(service_execution["service_actions"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = record_helper
        try:
            result = execute_configured_tool_registry_provider_service_execution(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_uses_result_model_helper(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(execution_result=execution_result)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = build_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    len(getattr(service_execution, "service_actions")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        execution_result = {
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_default_counts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result={},
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 0)
        self.assertEqual(result.audit_event_count, 0)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        runtime_actions_result_model = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        result = build_configured_tool_registry_provider_service_execution_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=runtime_actions_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result.runtime_artifacts.provider_source_name, service_execution_model.runtime_artifacts.provider_source_name)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )

        result = (
            build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_tool_registry_diagnostics_trace_service_action_model_keeps_fields(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "diagnostics",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action_model(
            trace_step=trace_step,
            trace_event=trace_event,
            persist_force=True,
        )

        self.assertEqual(result.kind, "internal_trace_write")
        self.assertEqual(result.trace_step, trace_step)
        self.assertEqual(result.trace_event, trace_event)
        self.assertTrue(result.persist_force)
        self.assertIsNone(result.kwargs)

    def test_build_tool_registry_diagnostics_audit_service_action_model_keeps_fields(
        self,
    ) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "diagnostics detected",
            "detail": {"provider_source": "default"},
        }

        result = build_tool_registry_diagnostics_audit_service_action_model(
            audit_event=audit_event,
        )

        self.assertEqual(result.kind, "record_audit_event")
        self.assertIsNone(result.trace_step)
        self.assertIsNone(result.trace_event)
        self.assertFalse(result.persist_force)
        self.assertEqual(result.kwargs, audit_event)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 2,
                        "total": 3,
                        "entries": ({"kind": "missing_file"},),
                    },
                    "trace_step": {"id": "step-registry"},
                    "trace_event": {"task_id": "task-1"},
                    "audit_detail": {"provider_source": "file_source"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.total, 3)
        self.assertEqual(result.audit_event, {"event_type": "tool_registry_diagnostics"})

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_raw_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "selected_source_diagnostics": {
                    "invalid_tool_executions": (
                        "provider_search: unsupported tool execution kind api_key=hidden",
                        "provider_search: http_json execution query_params.access_token must be safe",
                    ),
                },
                "source_diagnostics": {
                    "provider_suite": {
                        "invalid_tool_executions": (
                            "provider_search: unsupported tool execution kind api_key=hidden",
                            "provider_search: http_json execution headers.x-api-key must be safe",
                        ),
                    },
                },
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 0,
                        "total": 2,
                        "entries": (),
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                },
            },
        )

        self.assertEqual(
            result.selected_source_diagnostics["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        self.assertEqual(
            result.source_diagnostics["provider_suite"]["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_diagnostics_runtime_payload(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 0,
                        "total": 2,
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 2,
                                "values": (
                                    "provider_search: unsupported tool execution kind api_key=hidden",
                                    "provider_search: http_json execution query_params.access_token must be safe",
                                ),
                            },
                        ),
                    },
                    "trace_step": {
                        "id": "step-registry",
                        "content": (
                            "provider_search: unsupported tool execution kind api_key=hidden\n"
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                    "trace_event": {
                        "step": {
                            "content": (
                                "provider_search: http_json execution query_params.access_token must be safe"
                            ),
                        },
                    },
                    "audit_detail": {
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 1,
                                "values": (
                                    "provider_search: unsupported tool execution kind token=hidden",
                                ),
                            },
                        ),
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "detail": {
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 1,
                                "values": (
                                    "provider_search: http_json execution json_body.client_secret must be safe",
                                ),
                            },
                        ),
                    },
                },
            },
        )

        summary_values = result.diagnostics_runtime.summary.entries[0]["values"]
        self.assertEqual(
            summary_values,
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("client_secret", serialized)

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 1,
                            "total": 1,
                            "entries": (),
                        }
                    }
                },
                "service_actions": [
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {"id": "step-registry"},
                        "trace_event": {"task_id": "task-1"},
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {"event_type": "tool_registry_diagnostics"},
                    },
                ],
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_accepts_tuple_service_actions(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {},
                "service_actions": (
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {"id": "step-registry"},
                        "trace_event": {"task_id": "task-1"},
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {"event_type": "tool_registry_diagnostics"},
                    },
                ),
            }
        )

        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_uses_runtime_service_actions_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_model_from_dict(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                                "entries": (),
                            }
                        }
                    },
                    "service_actions": [
                        {
                            "kind": "internal_trace_write",
                            "trace_step": {"id": "step-registry"},
                            "trace_event": {"task_id": "task-1"},
                            "persist_force": True,
                        },
                        {
                            "kind": "record_audit_event",
                            "kwargs": {"event_type": "tool_registry_diagnostics"},
                        },
                    ],
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_uses_typed_runtime_service_actions_model_helper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = (
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
            )
            captured: list[tuple[str, int]] = []

            def record_helper(
                *,
                runtime_artifacts: object,
            ) -> object:
                captured.append(
                    (
                        str(getattr(runtime_artifacts, "provider_source_name", None)),
                        int(
                            getattr(
                                getattr(runtime_artifacts, "diagnostics_runtime", None),
                                "summary",
                            ).missing_total
                        ),
                    )
                )
                return original_helper(runtime_artifacts=runtime_artifacts)

            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
            try:
                result = build_configured_tool_registry_provider_service_execution_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                )
            finally:
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result.to_dict()),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_uses_typed_runtime_artifacts_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "diagnostics",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "diagnostics detected",
                "detail": {"provider_source": "file_source"},
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: object
        ) -> object:
            captured.append(
                (
                    str(getattr(runtime_artifacts, "provider_source_name", None)),
                    hasattr(runtime_artifacts, "diagnostics_runtime"),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model(
                runtime_artifacts=runtime_artifacts,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("default", True)])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
            )
        )

        self.assertIs(result_model, service_actions_model)
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_uses_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: dict[str, object]
        ) -> object:
            captured.append(
                (
                    str(runtime_artifacts.get("provider_source_name", "")),
                    runtime_artifacts.get("provider") is provider,
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs(
                    runtime_artifacts={
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                            },
                            "trace_step": {"id": "step-registry", "seq": 2},
                            "trace_event": {"task_id": "task-1"},
                        },
                        "audit_event": {"event_type": "tool_registry_diagnostics"},
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [("file_source", True)])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model_uses_service_action_builders(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_trace_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model
        )
        original_audit_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model
        )
        captured: list[str] = []

        def record_helper(
            **kwargs: object,
        ) -> object:
            captured.append("trace")
            return original_trace_helper(**kwargs)

        def record_audit_helper(
            **kwargs: object,
        ) -> object:
            captured.append("audit")
            return original_audit_helper(**kwargs)

        tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = record_helper
        tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = record_audit_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        finally:
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = original_trace_helper
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = original_audit_helper

        self.assertEqual(captured, ["trace", "audit"])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict_uses_result_model_builder(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            trace_write_count: int,
            audit_event_count: int,
        ) -> object:
            captured.append(
                (
                    int(trace_write_count),
                    int(audit_event_count),
                )
            )
            return original_helper(
                trace_write_count=trace_write_count,
                audit_event_count=audit_event_count,
            )

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(
                execution_result=build_configured_tool_registry_provider_runtime_service_actions_result_model(
                    trace_write_count=1,
                    audit_event_count=2,
                )
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[trace_action.to_dict(), audit_action.to_dict()]
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertTrue(result.actions[0].persist_force)
        self.assertEqual(
            result.actions[1].kwargs,
            {"event_type": "tool_registry_diagnostics"},
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_uses_action_model_builder(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict
        )
        captured: list[int] = []

        def record_helper(
            service_action: dict[str, object],
        ) -> object:
            captured.append(len(service_action))
            return original_helper(service_action)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = original_helper

        self.assertEqual(captured, [4, 2])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_uses_model_helper(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                    service_actions=[trace_action.to_dict(), audit_action.to_dict()]
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        result = execute_configured_tool_registry_provider_runtime_service_actions_model(
            service_actions=service_actions_model,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions_model.actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_redacts_raw_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-configured-provider-runtime-action-http-json-output"
        )
        service_actions_model = (
            tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
                actions=(
                    tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionModel(
                        kind="internal_trace_write",
                        trace_step=raw_step,
                        persist_force=True,
                    ),
                )
            )
        )
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []

        result = execute_configured_tool_registry_provider_runtime_service_actions_model(
            service_actions=service_actions_model,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: None,
        )

        serialized = json.dumps(trace_steps, ensure_ascii=False)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(persisted, [True])
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_uses_result_model_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models
        )
        captured: list[tuple[str, ...]] = []

        def record_helper(
            *,
            service_actions: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(tuple(action.kind for action in getattr(service_actions, "actions")))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions_model(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = original_helper

        self.assertEqual(captured, [("internal_trace_write", "record_audit_event")])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(action.kind for action in getattr(service_execution, "service_actions")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("internal_trace_write", "record_audit_event"))])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

            result_model, result_dict = (
                execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            )

        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result_model.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models
            )
            captured: list[tuple[str, int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                execution_result: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        int(getattr(execution_result, "trace_write_count")),
                        int(getattr(execution_result, "audit_event_count")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    execution_result=execution_result,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
            try:
                result_model, result_dict = (
                    execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                        service_execution=service_execution_model,
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(
            captured,
            [("file_source", 1, 1)],
        )
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper_for_trace_execution(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        len(getattr(service_execution, "service_actions", ())),
                        len(trace_steps),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result_model = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [(2, 0)])
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_keeps_shape(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = execute_configured_tool_registry_provider_preflight(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["service_execution"]["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval_fast",),
                "tool_details": (
                    {
                        "name": "calc_eval_fast",
                        "label": "Fast Calculator",
                        "kind": "local_calculator",
                        "semantic_kind": "local_calculator",
                        "retryable_by_default": True,
                        "default_timeout_ms": 3_000,
                        "requires_user_context": True,
                        "supports_result_preview": True,
                        "effective_result_preview_keys": ("expression", "result"),
                    },
                ),
                "service_action_count": 2,
                "service_action_kinds": ("internal_trace_write", "record_audit_event"),
                "trace_write_count": 1,
                "audit_event_count": 1,
                "has_diagnostics": True,
                "diagnostics_total": 1,
                "skipped_total": 0,
                "missing_total": 1,
                "diagnostics_summary": {
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 1,
                    "total": 1,
                    "entries": (
                        {
                            "kind": "missing",
                            "target": "registry_files",
                            "count": 1,
                            "values": (
                                str(missing_file.resolve()),
                            ),
                        },
                    ),
                },
            },
        )

    def test_execute_configured_tool_registry_provider_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

            result = execute_configured_tool_registry_provider_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(trace_steps, [service_execution_model.service_actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_result_keeps_shape(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result["provider"], provider)
        self.assertEqual(result["service_execution"]["provider_source_name"], "file_source")
        self.assertEqual(result["service_execution"]["service_actions"], [])
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval",),
                "tool_details": (
                    {
                        "name": "calc_eval",
                        "label": "Calculator",
                        "kind": "local_calculator",
                        "semantic_kind": "local_calculator",
                        "retryable_by_default": True,
                        "default_timeout_ms": 3_000,
                        "requires_user_context": True,
                        "supports_result_preview": True,
                        "effective_result_preview_keys": ("expression", "result"),
                    },
                ),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 1,
                "audit_event_count": 2,
                "has_diagnostics": True,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
                "diagnostics_summary": {
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
            },
        )

    def test_build_configured_tool_registry_provider_preflight_result_uses_result_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result(
                service_execution=service_execution,
                execution_result={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": service_execution["runtime_artifacts"],
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["summary"]["tool_names"], ("calc_eval",))

    def test_build_configured_tool_registry_provider_preflight_summary_keeps_shape(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                    }
                }
            },
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary(
            preflight_result=preflight_result
        )

        self.assertEqual(
            result,
            {
                "provider_source_name": "default",
                "tool_count": 0,
                "tool_names": (),
                "tool_details": (),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 0,
                "audit_event_count": 1,
                "has_diagnostics": False,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
                "diagnostics_summary": {
                    "has_diagnostics": False,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
            },
        )

    def test_build_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result["provider_source_name"], "default")
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_productized_tool_details_for_real_provider_kinds(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="Provider Math",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                )
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 13_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                    "effective_result_output_keys": ("expression", "result"),
                },
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "effective_result_output_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_diagnostics_summary_entries(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
                provider=provider,
                provider_source_name="file_source",
                runtime_artifacts={
                    "provider_source_name": "file_source",
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 1,
                            "missing_total": 1,
                            "total": 2,
                            "entries": (
                                {
                                    "kind": "skipped",
                                    "target": "registry_sources",
                                    "count": 1,
                                    "values": ("planning_suite",),
                                },
                                {
                                    "kind": "missing",
                                    "target": "registry_files",
                                    "count": 1,
                                    "values": ("/tmp/missing.json",),
                                },
                            ),
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                },
            ),
            service_actions=(),
            trace_write_count=1,
            audit_event_count=2,
        )

        self.assertEqual(
            result.diagnostics_summary,
            {
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_per_tool_invalid_execution_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="Provider Math",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
                provider=provider,
                provider_source_name="provider_suite",
                runtime_artifacts={
                    "provider_source_name": "provider_suite",
                    "selected_source_diagnostics": {
                        "invalid_tool_executions": (
                            "provider_search: http_json execution response_path must not be blank",
                        ),
                    },
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 0,
                            "total": 1,
                            "entries": (
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": (
                                        "provider_search: http_json execution response_path must not be blank",
                                    ),
                                },
                            ),
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                },
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 13_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                    "effective_result_output_keys": ("expression", "result"),
                },
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "effective_result_output_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "execution_diagnostics": (
                        "http_json execution response_path must not be blank",
                    ),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_redacts_sensitive_execution_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
                provider=provider,
                provider_source_name="provider_suite",
                runtime_artifacts={
                    "provider_source_name": "provider_suite",
                    "selected_source_diagnostics": {
                        "invalid_tool_executions": (
                            "provider_search: unsupported tool execution kind api_key=hidden",
                            "provider_search: http_json execution query_params.access_token must be safe",
                        ),
                    },
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 0,
                            "total": 2,
                            "entries": (),
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                },
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        provider_search = result.tool_details[0]
        self.assertEqual(
            provider_search["execution_diagnostics"],
            (
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ),
        )
        joined_diagnostics = "\n".join(provider_search["execution_diagnostics"])
        self.assertNotIn("api_key=hidden", joined_diagnostics)
        self.assertNotIn("access_token", joined_diagnostics)

    def test_build_configured_tool_registry_provider_preflight_summary_model_humanizes_unlabeled_real_tool_names(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            tuple(detail["label"] for detail in result.tool_details),
            ("Provider Math", "Provider Search"),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_result_output_keys_for_real_provider_tools(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    result_preview_keys=("documents_total",),
                    result_output_keys=("documents_total",),
                    runtime_semantic_kind="provider_search",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "documents_total": 1,
                        "documents": [{"id": "doc-1"}],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("documents_total",),
                    "effective_result_output_keys": ("documents_total",),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_tools(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    result_preview_keys=("documents_total",),
                    runtime_semantic_kind="provider_search",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "documents_total": 1,
                        "documents": [{"id": "doc-1"}],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("documents_total",),
                    "effective_result_output_keys": ("documents_total",),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_keeps_fields(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                        "total": 0,
                        "skipped_total": 0,
                        "missing_total": 0,
                    }
                }
            },
            "provider": StaticToolRegistryProvider({}),
            "service_execution": {"service_actions": []},
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary_model(
            preflight_result=preflight_result
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.tool_count, 0)
        self.assertEqual(result.tool_names, ())
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_uses_summary_model_from_dict_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "provider": StaticToolRegistryProvider({}),
                    "service_execution": {"service_actions": []},
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
            preflight_result={
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.missing_total, 1)
        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "calc_eval",
                    "label": "Calculator",
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 3_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_merges_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.service_actions[0].kind, "record_audit_event")
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.skipped_total, 1)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_uses_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(*, preflight_result: dict[str, object]) -> dict[str, object]:
            service_execution = original_helper(preflight_result=preflight_result)
            runtime_artifacts = service_execution["runtime_artifacts"]
            summary = runtime_artifacts["diagnostics_runtime"]["summary"]
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(summary["missing_total"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = original_helper

        self.assertEqual(captured, [("service_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
                            "provider": provider,
                            "provider_source_name": "file_source",
                            "runtime_artifacts": {
                                "diagnostics_runtime": {
                                    "summary": {
                                        "has_diagnostics": True,
                                        "total": 1,
                                        "skipped_total": 0,
                                        "missing_total": 1,
                                    }
                                }
                            },
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    execution_result["trace_write_count"],
                    execution_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(service_execution_model.service_actions[0].kind, "record_audit_event")
        self.assertTrue(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics
        )
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.total, 2
        )
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        captured: list[tuple[str, int]] = []

        def record_models_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_models_helper
        try:
            service_execution_model, execution_result_model = (
                build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
                            "provider": provider,
                            "provider_source_name": "file_source",
                            "runtime_artifacts": {
                                "diagnostics_runtime": {
                                    "summary": {
                                        "has_diagnostics": True,
                                        "total": 1,
                                        "skipped_total": 0,
                                        "missing_total": 1,
                                    }
                                }
                            },
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                    service_execution={
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 2,
                                    "skipped_total": 1,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_uses_execution_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_dict(
            preflight_result={
                "provider_source_name": "top_level_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(result_model.summary.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_uses_execution_models_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        service_execution_model_out, execution_result_model = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model_out, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_models_from_models_helper_via_typed_path(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_parts_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=service_execution_result_model.provider,
            provider_source_name=service_execution_result_model.provider_source_name,
            runtime_artifacts=service_execution_result_model.runtime_artifacts,
            service_actions=service_execution_model.service_actions,
            trace_write_count=service_execution_result_model.trace_write_count,
            audit_event_count=service_execution_result_model.audit_event_count,
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_result_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        result = (
            build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_fills_missing_metadata_from_execution_result(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                service_execution={
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_overlays_execution_result_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": False,
                            "total": 0,
                            "skipped_total": 0,
                            "missing_total": 0,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "provider_source_name": "result_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.provider_source_name, "service_source")
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(result_dict["provider_source_name"], "service_source")
        self.assertEqual(summary_dict["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_outputs_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_models_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[int, int, str]] = []

        def record_models_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                    str(preflight_result["service_execution"]["provider_source_name"]),
                )
            )
            return original_models_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = record_models_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_models_helper

        self.assertEqual(captured, [(1, 2, "file_source")])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_dicts_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            summary_dict, result_dict = build_configured_tool_registry_provider_preflight_dicts(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("record_audit_event",),
        )

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(
            result.runtime_artifacts.provider_source_name,
            service_execution_model.runtime_artifacts.provider_source_name,
        )
        self.assertEqual(
            result.service_execution.provider_source_name,
            service_execution_model.provider_source_name,
        )
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.summary.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.summary.service_action_kinds, ())

    def test_build_configured_tool_registry_provider_preflight_models_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            summary_model.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result_model.summary.tool_names, summary_model.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_dict["provider_source_name"], summary_model.provider_source_name)
        self.assertEqual(summary_dict["tool_names"], summary_model.tool_names)
        self.assertIs(result_dict["provider"], result_model.provider)
        self.assertEqual(result_dict["summary"]["tool_names"], result_model.summary.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_uses_outputs_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload
        )
        captured: list[tuple[int, int, str]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                    str(service_execution["provider_source_name"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = original_helper

        self.assertEqual(captured, [(1, 2, "service_source")])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        original_dict_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = (
            lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("outputs_from_service_execution_payload should not call outputs_from_dict")
            )
        )
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_dict_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
            preflight_result={
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_models_uses_result_model_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_result_model_returns_existing_summary(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        preflight_result_model = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
            preflight_result=preflight_result_model,
        )

        self.assertIs(result, preflight_result_model.summary)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_uses_outputs_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_execute_configured_tool_registry_provider_preflight_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = execute_configured_tool_registry_provider_preflight_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_surfaces_invalid_tool_execution_diagnostics(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        settings = SimpleNamespace(
            tool_registry_provider_source="analytics_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "provider": "default",
                        "profile": "default",
                        "disabled_tool_names": [
                            "task_plan",
                            "task_retrieve",
                            "calc_eval",
                        ],
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "unsupported_transport",
                                },
                            }
                        },
                    }
                }
            ),
        )

        result = execute_configured_tool_registry_provider_preflight_model(
            settings=settings,
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(result.provider_source_name, "analytics_suite")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("provider_search",),
        )
        self.assertTrue(result.summary.has_diagnostics)
        self.assertEqual(result.summary.skipped_total, 0)
        self.assertEqual(result.summary.missing_total, 0)
        self.assertEqual(result.summary.diagnostics_total, 1)
        self.assertEqual(
            result.summary.diagnostics_summary["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (
                        "provider_search: unsupported tool execution kind unsupported_transport",
                    ),
                },
            ),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_surfaces_file_backed_real_calc_diagnostics(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "calc-diagnostics-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_math": {
                                "template": "calc_eval",
                                "label": "Provider Calculator",
                                "kind": "provider_calc",
                                "execution": {
                                    "kind": "http_json",
                                    "method": "POST",
                                    "url": "https://provider.example/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "result": "$.value",
                                    },
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="calculator_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "calculator_suite": {
                            "registry_file": str(registry_file),
                            "profile": "calculator_only",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )

            result = execute_configured_tool_registry_provider_preflight_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        expected_diagnostic = (
            "provider_math: http_json execution references unsupported runtime "
            "template variable settings_api_keey in [redacted]"
        )
        expected_tool_diagnostic = (
            "http_json execution references unsupported runtime template variable "
            "settings_api_keey in [redacted]"
        )
        self.assertEqual(result.provider_source_name, "calculator_suite")
        self.assertTrue(result.summary.has_diagnostics)
        self.assertEqual(result.summary.diagnostics_total, 1)
        self.assertEqual(
            result.summary.diagnostics_summary["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (expected_diagnostic,),
                },
            ),
        )
        provider_math_detail = next(
            detail for detail in result.summary.tool_details if detail["name"] == "provider_math"
        )
        self.assertEqual(
            provider_math_detail["execution_diagnostics"],
            (expected_tool_diagnostic,),
        )
        self.assertEqual(
            result.runtime_artifacts.selected_source_diagnostics["invalid_tool_executions"],
            (expected_diagnostic,),
        )
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry"]["total"],
            1,
        )
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry"]["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (expected_diagnostic,),
                },
            ),
        )
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )

            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_service_execution_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_uses_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        (step_id, str(seq), model),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = execute_configured_tool_registry_provider_preflight_outputs(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ("step-registry", "2", "mock-gpt"))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = execute_configured_tool_registry_provider_preflight_models(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_model_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval_fast",))
        self.assertEqual(result.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["tool_names"], ("calc_eval_fast",))
        self.assertEqual(
            result["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_uses_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_dicts_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                summary_dict, result_dict = (
                    execute_configured_tool_registry_provider_preflight_dicts(
                        settings=settings,
                        task_id="task-1",
                        step_id="step-registry",
                        seq=2,
                        model="mock-gpt",
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(
                            bool(kwargs["force"])
                        ),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(
                            kwargs
                        ),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(summary_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
