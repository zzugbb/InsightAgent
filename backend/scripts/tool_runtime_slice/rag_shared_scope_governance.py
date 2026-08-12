from __future__ import annotations

from .context import *


class RagSharedScopeGovernanceMixin:
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
