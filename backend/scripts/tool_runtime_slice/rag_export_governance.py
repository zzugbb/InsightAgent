from __future__ import annotations

from .context import *


class RagExportGovernanceMixin:
    def test_get_task_export_response_summary_preserves_safe_rag_version_fields(
        self,
    ) -> None:
        original_payload_helper = (
            chat_persistence_module.get_task_export_payload_summary
        )

        try:
            chat_persistence_module.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-response-rag-version",
                        "session_id": "session-export-response-rag-version",
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
                                "step_id": "step-provider-rag-version",
                                "knowledge_base_id": "kb-provider",
                                "content": "Matched safe snippet",
                                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                                "content_hash": "b" * 64,
                                "source": "handbook.md?api_key=raw-secret",
                                "document_id": "doc-1 token=raw-token",
                            },
                            {
                                "step_id": "step-provider-rag-poisoned-version",
                                "knowledge_base_id": "kb-provider",
                                "content": "Matched poisoned snippet",
                                "document_version": "Bearer raw-secret",
                                "content_hash": "token=raw-token",
                            },
                        ],
                    },
                }
            )
            payload = chat_persistence_module.get_task_export_response_summary(  # type: ignore[attr-defined]
                {"id": "task-export-response-rag-version"},
                [],
            )
        finally:
            chat_persistence_module.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        chunks = payload["trace"]["rag_chunks"]
        self.assertEqual(
            chunks[0]["document_version"],
            "sha256:aaaaaaaaaaaaaaaa",
        )
        self.assertEqual(chunks[0]["content_hash"], "b" * 64)
        self.assertEqual(chunks[0]["source"], "handbook.md?[redacted]")
        self.assertEqual(chunks[0]["document_id"], "doc-1 [redacted]")
        self.assertNotIn("document_version", chunks[1])
        self.assertNotIn("content_hash", chunks[1])
        serialized_chunks = json.dumps(chunks, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized_chunks)
        self.assertNotIn("raw-token", serialized_chunks)
        self.assertNotIn("api_key", serialized_chunks)
        self.assertNotIn("Bearer", serialized_chunks)

    def test_get_trace_rag_export_summary_preserves_safe_chunk_version_fields(
        self,
    ) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-versioned-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": [
                                {
                                    "content": " versioned chunk ",
                                    "source": "handbook.md?api_key=raw-secret",
                                    "document_id": "doc-1 token=raw-token",
                                    "document_version": "sha256:aaaaaaaaaaaaaaaa",
                                    "content_hash": "b" * 64,
                                },
                                {
                                    "content": "poisoned chunk",
                                    "document_version": "Bearer raw-secret",
                                    "content_hash": "token=raw-token",
                                },
                            ],
                            "knowledge_base_id": " kb-1 ",
                        }
                    },
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"][0],
            {
                "step_id": "step-versioned-rag-1",
                "knowledge_base_id": "kb-1",
                "content": "versioned chunk",
                "source": "handbook.md?[redacted]",
                "document_id": "doc-1 [redacted]",
                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                "content_hash": "b" * 64,
            },
        )
        self.assertNotIn("document_version", payload["rag_chunks"][1])
        self.assertNotIn("content_hash", payload["rag_chunks"][1])
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_get_trace_rag_export_summary_merges_parallel_runtime_chunk_metadata(
        self,
    ) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-parallel-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": [
                                "versioned chunk",
                                "poisoned chunk",
                            ],
                            "chunk_metadata": [
                                {
                                    "source": "handbook.md?api_key=raw-secret",
                                    "document_id": "doc-1 token=raw-token",
                                    "document_version": "sha256:aaaaaaaaaaaaaaaa",
                                    "content_hash": "b" * 64,
                                },
                                {
                                    "document_version": "Bearer raw-secret",
                                    "content_hash": "token=raw-token",
                                },
                            ],
                            "knowledge_base_id": "kb-1",
                        }
                    },
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(
            payload["rag_chunks"][0],
            {
                "step_id": "step-parallel-rag-1",
                "knowledge_base_id": "kb-1",
                "content": "versioned chunk",
                "source": "handbook.md?[redacted]",
                "document_id": "doc-1 [redacted]",
                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                "content_hash": "b" * 64,
            },
        )
        self.assertNotIn("document_version", payload["rag_chunks"][1])
        self.assertNotIn("content_hash", payload["rag_chunks"][1])
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_task_export_summary_coercion_preserves_safe_rag_version_fields(
        self,
    ) -> None:
        summary = {
            "task": {
                "id": "task-export-route-rag-version",
                "session_id": "session-export-route-rag-version",
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
                        "step_id": "step-provider-rag-route-version",
                        "knowledge_base_id": "kb-provider",
                        "content": "Matched safe snippet",
                        "document_version": "sha256:aaaaaaaaaaaaaaaa",
                        "content_hash": "b" * 64,
                        "source": "handbook.md?api_key=raw-secret",
                        "document_id": "doc-1 token=raw-token",
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
        self.assertIn("sha256:aaaaaaaaaaaaaaaa", serialized_chunks)
        self.assertIn("handbook.md?[redacted]", serialized_chunks)
        self.assertIn("doc-1 [redacted]", serialized_chunks)
        self.assertNotIn("raw-secret", serialized_chunks)
        self.assertNotIn("raw-token", serialized_chunks)
        self.assertNotIn("api_key", serialized_chunks)

    def test_task_export_markdown_includes_safe_rag_version_header(self) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-02T11:32:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-md-rag-version",
                session_id="session-export-md-rag-version",
                prompt="shared prompt",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=9,
                created_at="2026-07-02T11:30:00",
                updated_at="2026-07-02T11:31:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=0,
                rag_hit_count=1,
                rag_knowledge_base_ids=["kb-provider"],
                rag_chunks=[
                    task_routes_module.TaskExportRagChunk(  # type: ignore[attr-defined]
                        step_id="step-provider-rag-md-version",
                        knowledge_base_id="kb-provider",
                        content="Matched safe snippet",
                        document_version="sha256:aaaaaaaaaaaaaaaa",
                        content_hash="b" * 64,
                        source="handbook.md?[redacted]",
                        document_id="doc-1",
                    )
                ],
                steps=[],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(payload)  # type: ignore[attr-defined]

        self.assertIn(
            "step=step-provider-rag-md-version · kb=kb-provider · "
            "version=sha256:aaaaaaaaaaaaaaaa · source=handbook.md?[redacted]",
            markdown,
        )
        self.assertNotIn("raw-secret", markdown)
        self.assertNotIn("api_key", markdown)
