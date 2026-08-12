from __future__ import annotations

from .context import *


class RagSharedScopeGovernanceMixin:
    def test_rag_run_tool_task_retrieve_sanitizes_helper_output_identifiers(
        self,
    ) -> None:
        original_query = tool_runtime_module.query_knowledge_base

        def fake_query_knowledge_base(
            *,
            user_id: str,
            knowledge_base_id: str,
            query_text: str,
            top_k: int,
        ) -> dict[str, object]:
            return {
                "hits": [
                    {
                        "id": "hit?api_key=raw-secret&token=raw-token",
                        "content": "safe shared runtime content",
                        "metadata": {
                            "source": "shared.md?api_key=raw-secret",
                            "document_id": "doc token=raw-token",
                            "document_version": "Bearer raw-secret",
                            "content_hash": "token=raw-token",
                        },
                    }
                ],
                "hit_count": 1,
                "knowledge_base_id": "shared-handbook-api_key-raw-secret",
                "collection": (
                    "kb_shared_shared-handbook-api_key-raw-secret-token-raw-token"
                ),
            }

        tool_runtime_module.query_knowledge_base = fake_query_knowledge_base
        try:
            output = run_tool(
                name="task_retrieve",
                tool_input={
                    "query": "检索 shared handbook",
                    "knowledge_base_id": "shared-handbook",
                    "top_k": 1,
                },
                prompt="检索 shared handbook",
                user_id="user-private-runtime",
                attempt=0,
            )
        finally:
            tool_runtime_module.query_knowledge_base = original_query

        self.assertEqual(output["knowledge_base_id"], "shared-handbook-redacted")
        self.assertEqual(output["collection"], "kb_shared_shared-handbook-redacted")
        self.assertEqual(output["hit_count"], 1)
        self.assertEqual(output["chunks"], ["safe shared runtime content"])
        hits = output["hits"]
        self.assertIsInstance(hits, list)
        self.assertEqual(hits[0]["id"], "hit?[redacted]&[redacted]")
        self.assertEqual(
            hits[0]["metadata"],
            {
                "source": "shared.md?[redacted]",
                "document_id": "doc [redacted]",
            },
        )
        serialized = json.dumps(output, ensure_ascii=False)
        self.assertIn("shared-handbook-redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_run_tool_rag_task_retrieve_routes_shared_kb_to_shared_scope(self) -> None:
        original_query = tool_runtime_module.query_knowledge_base

        calls: list[tuple[str, str, str, int]] = []

        def fake_query_knowledge_base(
            *,
            user_id: str,
            knowledge_base_id: str,
            query_text: str,
            top_k: int,
        ) -> dict[str, object]:
            calls.append((user_id, knowledge_base_id, query_text, top_k))
            return {
                "hits": [{"content": "shared alpha"}],
                "hit_count": 1,
                "knowledge_base_id": knowledge_base_id,
                "collection": "kb_shared_shared-handbook",
            }

        tool_runtime_module.query_knowledge_base = fake_query_knowledge_base
        try:
            output = run_tool(
                name="task_retrieve",
                tool_input={
                    "query": "检索 shared handbook",
                    "knowledge_base_id": "shared-handbook",
                    "top_k": 3,
                },
                prompt="检索 shared handbook",
                user_id="user-private-runtime",
                attempt=0,
            )
        finally:
            tool_runtime_module.query_knowledge_base = original_query

        self.assertEqual(
            calls,
            [
                (
                    chroma_rag_module.SHARED_RAG_SCOPE_USER_ID,
                    "shared-handbook",
                    "检索 shared handbook",
                    3,
                )
            ],
        )
        self.assertEqual(
            output,
            {
                "chunks": ["shared alpha"],
                "hits": [{"content": "shared alpha"}],
                "hit_count": 1,
                "knowledge_base_id": "shared-handbook",
                "collection": "kb_shared_shared-handbook",
            },
        )
