from __future__ import annotations

from .context import *


class TaskTraceExportGovernanceMixinPart2:
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
