from __future__ import annotations

from .context import *


class TaskTraceResponseSummariesMixin:
    def test_get_task_trace_preview_summary_reuses_shared_trace_export_summary_helper(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_export_helper = getattr(
            chat_persistence_module,
            "get_task_trace_export_summary_from_task",
            None,
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "trace preview summary should reuse get_task_trace_export_summary_from_task(task) instead of touching parsed trace steps directly"
                )
            )
            chat_persistence_module.get_task_trace_export_summary_from_task = lambda _task: {  # type: ignore[attr-defined]
                "steps": [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-1",
                        type="thought",
                        content="planner note",
                        seq=1,
                    ),
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-2",
                        type="tool_result",
                        content="result body",
                        seq=2,
                    ),
                ],
                "step_count": 2,
                "rag_hit_count": 2,
                "rag_knowledge_base_ids": ["kb-shared"],
                "rag_chunks": [
                    {
                        "step_id": "step-1",
                        "knowledge_base_id": "kb-shared",
                        "content": "chunk-1",
                    }
                ],
            }
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            if original_export_helper is None:
                if hasattr(
                    chat_persistence_module,
                    "get_task_trace_export_summary_from_task",
                ):
                    delattr(
                        chat_persistence_module,
                        "get_task_trace_export_summary_from_task",
                    )
            else:
                chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["trace_step_count"], 2)
        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(
            payload["trace_preview"],
            [
                {
                    "id": "step-2",
                    "seq": 2,
                    "type": "tool_result",
                    "title": "tool result",
                    "content_excerpt": "result body",
                }
            ],
        )

    def test_get_task_trace_preview_summary_coerces_trace_step_dicts(self) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-dict",
                            "type": "tool_result",
                            "content": "preview dict body",
                            "seq": 12,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"],
            [
                {
                    "id": "step-preview-dict",
                    "seq": 12,
                    "type": "tool_result",
                    "title": "tool result",
                    "content_excerpt": "preview dict body",
                }
            ],
        )

    def test_get_task_trace_preview_summary_prefers_inferred_result_summary_from_preview_only_action_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool",
                            "type": "action",
                            "content": "Tool done: Task Planner",
                            "seq": 21,
                            "meta": {
                                "tool": {
                                    "name": "task_plan",
                                    "label": "Task Planner",
                                    "status": "done",
                                    "output_preview": {
                                        "plan": "Analyze request -> synthesize answer",
                                        "prompt_preview": "trace preview prompt",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Planned steps - Analyze request -> synthesize answer.", excerpt)
        self.assertNotIn("Tool done: Task Planner", excerpt)
        self.assertIn('Preview: {"plan":"Analyze request -> synthesize answer","prompt_preview":"trace preview prompt"}', excerpt)
        self.assertIn("Analyze request -> synthesize answer", excerpt)
        self.assertIn("trace preview prompt", excerpt)

    def test_get_task_trace_preview_summary_prefers_output_preview_without_leaking_raw_output(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-safe",
                            "type": "action",
                            "content": "Tool done: Hot Retrieval",
                            "seq": 22,
                            "meta": {
                                "tool": {
                                    "name": "task_retrieve_hot",
                                    "label": "Hot Retrieval",
                                    "status": "done",
                                    "output": {
                                        "tool_kind": "hot_knowledge_retrieval",
                                        "knowledge_base_id": "demo-kb",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                    "output_preview": {
                                        "tool_kind": "hot_knowledge_retrieval",
                                        "knowledge_base_id": "demo-kb",
                                        "hit_count": 2,
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn('"knowledge_base_id":"demo-kb"', excerpt)
        self.assertIn('"hit_count":2', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_appends_safe_tool_output_when_effective_result_output_keys_present(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 23,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Preview: {"documents_total":2}', excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)

    def test_get_task_trace_preview_summary_filters_safe_tool_output_to_effective_result_output_keys_subset(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy-filtered",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 24,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_accepts_tuple_effective_result_output_keys(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy-tuple",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 25,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": (
                                        "documents_total",
                                        "request_id",
                                    ),
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_appends_tuple_tool_output_preview_for_action_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-tuple-preview",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 26,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "output_preview": (
                                        "alpha",
                                        "beta",
                                    ),
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn('Preview: ["alpha","beta"]', excerpt)

    def test_get_task_trace_preview_summary_uses_productized_tool_title_for_real_tool_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-provider-search",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 23,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "semantic_kind": "provider_search",
                                    "semantic_family": "knowledge_retrieval",
                                    "status": "done",
                                    "output_preview": {
                                        "hit_count": 2,
                                        "knowledge_base_id": "demo-kb",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Provider Search [provider_search · knowledge_retrieval]",
        )

    def test_get_task_trace_preview_summary_uses_productized_title_for_rag_followup_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-rag-followup",
                            "type": "thought",
                            "content": "Provider Search returned snippets.",
                            "seq": 24,
                            "meta": {
                                "step_type": "rag_retrieval",
                                "rag": {
                                    "chunks": ["alpha", "beta"],
                                    "knowledge_base_id": "demo-kb",
                                },
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 2,
                    "rag_knowledge_base_ids": ["demo-kb"],
                    "rag_chunks": [
                        {
                            "step_id": "step-rag-followup",
                            "knowledge_base_id": "demo-kb",
                            "content": "alpha",
                        },
                        {
                            "step_id": "step-rag-followup",
                            "knowledge_base_id": "demo-kb",
                            "content": "beta",
                        },
                    ],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Knowledge Retrieval Snippets",
        )

    def test_get_task_trace_preview_summary_infers_calc_summary_from_structural_kind_output_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 27,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "result": 7,
                                    },
                                    "output": {
                                        "kind": "provider_calc",
                                        "result": 7,
                                        "request_id": "req-calc-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Preview: {"result":7}', excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)

    def test_get_task_trace_preview_summary_uses_file_backed_real_calc_summary(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-file-backed-provider-math",
                            "type": "action",
                            "content": "Tool done: Provider Calculator",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "provider_math",
                                    "label": "Provider Calculator",
                                    "kind": "provider_calc",
                                    "semantic_kind": "provider_math",
                                    "semantic_family": "local_calculator",
                                    "execution_kind": "http_json",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "expression",
                                        "result",
                                        "request_id",
                                        "source",
                                        "profile",
                                    ],
                                    "output_preview": {
                                        "expression": "8/4",
                                        "result": 2,
                                        "source": "calculator_suite",
                                        "profile": "calculator_only",
                                    },
                                    "output": {
                                        "expression": "8/4",
                                        "result": 2,
                                        "request_id": "req-calc-1",
                                        "source": "calculator_suite",
                                        "profile": "calculator_only",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        preview = payload["trace_preview"][0]
        self.assertEqual(
            preview["title"],
            "Provider Calculator [provider_math · local_calculator]",
        )
        excerpt = preview["content_excerpt"]
        self.assertIn("Calculated 8/4 = 2 (request id req-calc-1).", excerpt)
        self.assertIn(
            'Output: {"expression":"8/4","result":2,"request_id":"req-calc-1"',
            excerpt,
        )
        self.assertNotIn("Tool done: Provider Calculator", excerpt)

    def test_get_task_trace_preview_summary_infers_calc_summary_from_json_string_safe_output_without_preview(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math-json-string-safe-output",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Math [calculator]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)
        self.assertNotIn("secret", excerpt)

    def test_get_task_trace_preview_summary_infers_calc_summary_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "result": 7,
                                    },
                                    "output": {
                                        "result": 7,
                                        "request_id": "req-calc-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Math [calculator]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Preview: {"result":7}', excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)

    def test_get_task_trace_preview_summary_infers_planner_title_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-planner-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Planner",
                            "seq": 29,
                            "meta": {
                                "tool": {
                                    "name": "hosted_planner",
                                    "label": "Hosted Planner",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "steps",
                                    ],
                                    "output_preview": {
                                        "steps": [
                                            "Analyze request",
                                            "Synthesize final answer",
                                        ],
                                    },
                                    "output": {
                                        "steps": [
                                            "Analyze request",
                                            "Synthesize final answer",
                                        ],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Planner [planner]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn(
            "Planned steps - Analyze request -> Synthesize final answer.",
            excerpt,
        )
        self.assertNotIn("Tool done: Hosted Planner", excerpt)

    def test_get_task_trace_preview_summary_infers_retrieval_title_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-search-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Search",
                            "seq": 30,
                            "meta": {
                                "tool": {
                                    "name": "hosted_search",
                                    "label": "Hosted Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-search-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Search [retrieval]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn(
            "Retrieved 2 documents (request id req-search-1).",
            excerpt,
        )
        self.assertIn('Preview: {"documents_total":2}', excerpt)
        self.assertIn(
            'Output: {"documents_total":2,"request_id":"req-search-1"}',
            excerpt,
        )
        self.assertNotIn("Tool done: Hosted Search", excerpt)

    def test_get_task_trace_preview_summary_redacts_http_json_tool_label_title_diagnostics(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-http-json-tool-label-diagnostic",
                            "type": "action",
                            "content": (
                                'Tool done: Provider Status Preview: {"message":"ok"}'
                            ),
                            "seq": 31,
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
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("[redacted]", payload["trace_preview"][0]["title"])
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_rag_export_summary_reuses_shared_trace_steps_shape(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": [" chunk-1 ", "", "chunk-2"],
                            "knowledge_base_id": " kb-1 ",
                        }
                    },
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-2",
                    type="tool_result",
                    content="result body",
                    seq=2,
                    meta={
                        "rag": {
                            "chunks": ["chunk-3"],
                            "knowledge_base_id": "kb-1",
                        }
                    },
                ),
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 3)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
                {
                    "step_id": "step-2",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-3",
                },
            ],
        )

    def test_get_trace_rag_export_summary_accepts_tuple_chunks(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-tuple-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": (" chunk-1 ", "", "chunk-2"),
                            "knowledge_base_id": " kb-1 ",
                        }
                    },
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-tuple-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-tuple-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
            ],
        )

    def test_get_trace_rag_export_summary_accepts_wrapped_chunks(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                SimpleNamespace(
                    id="step-wrapped-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta=SimpleNamespace(
                        rag={
                            "chunks": UserList(
                                [
                                    UserString(" chunk-1 "),
                                    UserString(""),
                                    UserString("chunk-2"),
                                ]
                            ),
                            "knowledge_base_id": UserString(" kb-1 "),
                        }
                    ),
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-wrapped-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-wrapped-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
            ],
        )

    def test_get_task_trace_export_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        fake_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-1",
            type="thought",
            content="export summary body",
            seq=3,
        )
        captured: list[list[object]] = []
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                fake_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda trace_steps: captured.append(  # type: ignore[attr-defined]
                trace_steps
            ) or {
                "rag_hit_count": 2,
                "rag_knowledge_base_ids": ["kb-shared"],
                "rag_chunks": [
                    {
                        "step_id": "export-step-1",
                        "knowledge_base_id": "kb-shared",
                        "content": "chunk-shared",
                    }
                ],
            }
            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, [[fake_step]])
        self.assertEqual(payload["step_count"], 1)
        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-shared"])
        self.assertEqual(payload["steps"], [fake_step])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "export-step-1",
                    "knowledge_base_id": "kb-shared",
                    "content": "chunk-shared",
                }
            ],
        )

    def test_get_task_trace_export_summary_sanitizes_http_json_tool_meta_for_json_export(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-http-json-sensitive",
            type="action",
            content="Tool done: Provider Status",
            seq=5,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "input": {
                        "query": "status token=hidden",
                        "access_token": "hidden",
                        "headers": {
                            "Authorization": "Bearer hidden",
                        },
                    },
                    "effective_result_preview_keys": ["status", "message"],
                    "effective_result_output_keys": [
                        "status",
                        "message",
                        "request_id",
                    ],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                    "output": {
                        "status": "ready",
                        "message": "secret=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            }

            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        exported_step = payload["steps"][0]
        tool_meta = exported_step.meta.tool  # type: ignore[union-attr]

        self.assertEqual(
            tool_meta["input"],
            {
                "query": "status token=[redacted]",
                "access_token": "[redacted]",
                "headers": {
                    "Authorization": "[redacted]",
                },
            },
        )
        self.assertEqual(
            tool_meta["output_preview"],
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        self.assertEqual(
            tool_meta["output"],
            {
                "status": "ready",
                "message": "secret=[redacted]",
            },
        )
        exported_json = json.dumps(exported_step.model_dump(), ensure_ascii=False)
        self.assertNotIn('"access_token": "hidden"', exported_json)
        self.assertNotIn("Bearer hidden", exported_json)
        self.assertNotIn("secret-token", exported_json)
        self.assertNotIn("token=hidden", exported_json)
        self.assertNotIn("secret=hidden", exported_json)

    def test_get_task_trace_export_summary_sanitizes_legacy_http_json_content_for_json_export(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-http-json-legacy-content",
            type="action",
            content=(
                'Tool done: Provider Status Preview: {"status":"ready",'
                '"message":"gateway token=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"} Output: {"status":"ready",'
                '"message":"secret=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"}'
            ),
            seq=6,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": ["status", "message"],
                    "effective_result_output_keys": ["status", "message"],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                    "output": {
                        "status": "ready",
                        "message": "secret=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            }

            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-legacy-content"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        exported_step = payload["steps"][0]
        exported_json = json.dumps(exported_step.model_dump(), ensure_ascii=False)

        self.assertIn("Provider Status: ", exported_step.content)
        self.assertIn("gateway token=[redacted]", exported_step.content)
        self.assertIn("secret=[redacted]", exported_step.content)
        self.assertNotIn("access_token", exported_json)
        self.assertNotIn("token=hidden", exported_json)
        self.assertNotIn("secret=hidden", exported_json)
        self.assertNotIn("Bearer", exported_json)
        self.assertNotIn("secret-token", exported_json)

    def test_get_task_trace_export_summary_from_task_coerces_model_rag_chunks(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        fake_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-model-rag",
            type="thought",
            content="export summary body",
            seq=4,
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                fake_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 1,
                "rag_knowledge_base_ids": ["kb-model"],
                "rag_chunks": (
                    ResponseReadyChunk(
                        {
                            "step_id": "export-step-model-rag",
                            "knowledge_base_id": "kb-model",
                            "content": "chunk-model",
                        }
                    ),
                ),
            }
            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "export-step-model-rag",
                    "knowledge_base_id": "kb-model",
                    "content": "chunk-model",
                }
            ],
        )

    def test_get_task_export_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_usage_helper = chat_persistence_module.get_task_usage_from_task
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        task = {
            "id": "task-export-summary",
            "session_id": "session-export-summary",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "usage_json": "usage-json-guarded",
            "governance": {"profile": "shared_profile"},
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"trace:{raw_task.get('id')}")
                or {
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
                    "rag_knowledge_base_ids": ["kb-shared"],
                    "rag_chunks": [
                        {
                            "step_id": "step-1",
                            "knowledge_base_id": "kb-shared",
                            "content": "chunk-shared",
                        }
                    ],
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"usage:{raw_task.get('id')}")
                or {"usage_task_id": str(raw_task.get("id"))}
            )
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 23
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "trace:task-export-summary",
                "normalize:completed",
                "label:completed",
                "rank:completed",
                "usage:task-export-summary",
            ],
        )
        self.assertEqual(payload["usage"], {"usage_task_id": "task-export-summary"})
        self.assertEqual(
            payload["task"],
            {
                "id": "task-export-summary",
                "session_id": "session-export-summary",
                "prompt": "export summary prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 23,
                "created_at": "2026-06-22T13:00:00",
                "updated_at": "2026-06-22T13:05:00",
            },
        )
        self.assertEqual(payload["trace"]["governance"], {"profile": "shared_profile"})
        self.assertEqual(payload["trace"]["step_count"], 1)
        self.assertEqual(payload["trace"]["rag_hit_count"], 2)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-shared"])
        self.assertEqual(payload["trace"]["rag_chunks"], [{"step_id": "step-1", "knowledge_base_id": "kb-shared", "content": "chunk-shared"}])

    def test_get_task_export_summary_from_task_accepts_model_dump_row(self) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_usage_helper = chat_persistence_module.get_task_usage_from_task

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-export-model-row",
                    "session_id": "session-export-model-row",
                    "prompt": "export model row",
                    "status": "completed",
                    "created_at": "2026-07-02T15:40:00",
                    "updated_at": "2026-07-02T15:41:00",
                    "governance": {"profile": "planning_only"},
                }

        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda _task: {"total_tokens": 12}
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["task"]["id"], "task-export-model-row")
        self.assertEqual(payload["usage"], {"total_tokens": 12})
        self.assertEqual(payload["trace"]["governance"], {"profile": "planning_only"})

    def test_get_task_export_summary_from_task_coerces_model_rag_chunks(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-rag",
            "session_id": "session-export-summary-model-rag",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": None,
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: {
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 1,
                    "rag_knowledge_base_ids": ["kb-model"],
                    "rag_chunks": [
                        ResponseReadyChunk(
                            {
                                "step_id": "step-model-rag",
                                "knowledge_base_id": "kb-model",
                                "content": "chunk-model",
                            }
                        )
                    ],
                }
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace"]["rag_chunks"],
            [
                {
                    "step_id": "step-model-rag",
                    "knowledge_base_id": "kb-model",
                    "content": "chunk-model",
                }
            ],
        )

    def test_get_task_export_summary_from_task_coerces_governance_models(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-governance",
            "session_id": "session-export-summary-model-governance",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": ResponseReadyGovernance(
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ),
        }
        payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
            task
        )

        self.assertIsInstance(payload["trace"]["governance"], dict)
        self.assertIsNot(payload["trace"]["governance"], task["governance"])
        self.assertEqual(payload["trace"]["governance"]["profile"], "planning_only")

    def test_get_task_export_summary_from_task_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-governance-source-context",
            "session_id": "session-export-summary-model-governance-source-context",
            "prompt": "export summary prompt source context",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": ResponseReadyGovernance(
                {
                    "profile": "calculator_only",
                    "provider_source": "calculator_suite",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["calc_eval"],
                }
            ),
        }
        payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
            task
        )

        self.assertEqual(
            payload["trace"]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_task_export_summary_from_task_coerces_trace_step_dicts(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        task = {
            "id": "task-export-summary-dict-steps",
            "session_id": "session-export-summary-dict-steps",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: {
                    "steps": [
                        {
                            "id": "step-export-dict",
                            "type": "thought",
                            "content": "export dict body",
                            "seq": 11,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertIsInstance(
            payload["trace"]["steps"][0],
            chat_persistence_module.TraceStep,  # type: ignore[attr-defined]
        )
        self.assertEqual(payload["trace"]["steps"][0].id, "step-export-dict")
        self.assertEqual(payload["trace"]["steps"][0].seq, 11)

    def test_get_task_trace_response_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        task = {
            "id": "task-trace-response-summary",
            "status": "running",
            "trace_json": "trace-json-shared",
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"trace:{raw_task.get('id')}")
                or {
                    "steps": [
                        chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                            id="trace-step-1",
                            type="thought",
                            content="trace response body",
                            seq=5,
                        )
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 17
            )
            payload = chat_persistence_module.get_task_trace_response_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "trace:task-trace-response-summary",
                "normalize:running",
                "label:running",
                "rank:running",
            ],
        )
        self.assertEqual(
            [
                step.id
                for step in payload["steps"]
                if isinstance(step, chat_persistence_module.TraceStep)  # type: ignore[attr-defined]
            ],
            ["trace-step-1"],
        )
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["status_normalized"], "normalized::running")
        self.assertEqual(payload["status_label"], "label::running")
        self.assertEqual(payload["status_rank"], 17)

    def test_get_task_trace_response_summary_from_task_coerces_trace_step_dicts(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-response-dict",
                            "type": "thought",
                            "content": "response dict body",
                            "seq": 13,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_response_summary_from_task(  # type: ignore[attr-defined]
                {
                    "id": "task-trace-response-dict",
                    "status": "running",
                }
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["steps"]), 1)
        self.assertIsInstance(
            payload["steps"][0],
            chat_persistence_module.TraceStep,  # type: ignore[attr-defined]
        )
        self.assertEqual(payload["steps"][0].id, "step-response-dict")
        self.assertEqual(payload["steps"][0].seq, 13)

    def test_get_task_trace_delta_response_summary_from_task_reuses_shared_snapshot_helper(
        self,
    ) -> None:
        original_delta_snapshot_helper = getattr(
            chat_persistence_module,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        captured: list[tuple[str, int, int]] = []
        task = {
            "id": "task-trace-delta-response-summary",
            "trace_json": "trace-delta-response-summary",
        }
        try:
            chat_persistence_module.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda raw_task, after_seq=0, limit=200: captured.append(
                    (str(raw_task.get("id", "")), after_seq, limit)
                )
                or (
                    [
                        chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                            id="delta-step-1",
                            type="thought",
                            content="delta body",
                            seq=8,
                        )
                    ],
                    8,
                    False,
                    11,
                    "delta-step-1",
                )
            )
            payload = chat_persistence_module.get_task_trace_delta_response_summary_from_task(  # type: ignore[attr-defined]
                task,
                after_seq=3,
                limit=50,
            )
        finally:
            if original_delta_snapshot_helper is None:
                if hasattr(
                    chat_persistence_module,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        chat_persistence_module,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                chat_persistence_module.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [("task-trace-delta-response-summary", 3, 50)],
        )
        self.assertEqual(
            [
                step.id
                for step in payload["steps"]
                if isinstance(step, chat_persistence_module.TraceStep)  # type: ignore[attr-defined]
            ],
            ["delta-step-1"],
        )
        self.assertEqual(payload["next_cursor"], 8)
        self.assertFalse(payload["has_more"])
        self.assertEqual(payload["lag_seq"], 3)
        self.assertFalse(payload["dropped"])
