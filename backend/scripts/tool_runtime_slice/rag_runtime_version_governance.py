from __future__ import annotations

from .context import *


class RagRuntimeVersionGovernanceMixin:
    def test_build_tool_rag_followup_redacts_sensitive_runtime_knowledge_base_id(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-rag-runtime-kb-id",
            step_id="rag-runtime-kb-id-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "knowledge_base_id": "team?api_key=raw-secret&token=raw-token",
                "chunks": ["safe runtime chunk"],
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        rag_meta = followup["step"]["meta"]["rag"]
        self.assertEqual(
            rag_meta["knowledge_base_id"],
            "team-redacted-redacted",
        )
        serialized = json.dumps(followup, ensure_ascii=False)
        self.assertIn("team-redacted-redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

    def test_build_tool_rag_followup_preserves_safe_version_metadata_separately(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-rag-runtime-version",
            step_id="rag-runtime-version-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "knowledge_base_id": "kb-provider",
                "chunks": ["Versioned safe snippet", "Poisoned version snippet"],
                "hits": [
                    {
                        "content": "Versioned safe snippet",
                        "metadata": {
                            "source": "handbook.md?api_key=raw-secret",
                            "document_id": "doc-1 token=raw-token",
                            "document_version": "sha256:aaaaaaaaaaaaaaaa",
                            "content_hash": "b" * 64,
                        },
                    },
                    {
                        "content": "Poisoned version snippet",
                        "metadata": {
                            "source": "legacy.md?access_token=raw-token",
                            "document_id": "legacy-doc",
                            "document_version": "Bearer raw-secret",
                            "content_hash": "token=raw-token",
                        },
                    },
                ],
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        rag_meta = followup["step"]["meta"]["rag"]
        self.assertEqual(
            rag_meta["chunks"],
            ["Versioned safe snippet", "Poisoned version snippet"],
        )
        self.assertEqual(
            rag_meta["chunk_metadata"],
            [
                {
                    "source": "handbook.md?[redacted]",
                    "document_id": "doc-1 [redacted]",
                    "document_version": "sha256:aaaaaaaaaaaaaaaa",
                    "content_hash": "b" * 64,
                },
                {
                    "source": "legacy.md?[redacted]",
                    "document_id": "legacy-doc",
                },
            ],
        )
        self.assertEqual(
            rag_meta["document_versions"],
            [
                {
                    "document_version": "sha256:aaaaaaaaaaaaaaaa",
                    "content_hash": "b" * 64,
                    "source": "handbook.md?[redacted]",
                    "document_id": "doc-1 [redacted]",
                    "chunk_count": 1,
                }
            ],
        )
        serialized = json.dumps(rag_meta, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_build_tool_rag_followup_keeps_legacy_chunk_shape_without_versions(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-rag-runtime-legacy",
            step_id="rag-runtime-legacy-1",
            seq=4,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        rag_meta = followup["step"]["meta"]["rag"]
        self.assertEqual(rag_meta["chunks"], ["a", "b"])
        self.assertNotIn("chunk_metadata", rag_meta)
        self.assertNotIn("document_versions", rag_meta)

    def test_build_tool_rag_followup_aligns_chunk_object_metadata_before_hits(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-rag-runtime-align",
            step_id="rag-runtime-align-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            output={
                "knowledge_base_id": "kb-provider",
                "chunks": [
                    {
                        "content": "chunk object wins",
                        "metadata": {
                            "source": "chunk-source.md",
                            "document_id": "chunk-doc",
                            "document_version": "sha256:cccccccccccccccc",
                            "content_hash": "d" * 64,
                        },
                    }
                ],
                "hits": [
                    {
                        "content": "different hit row",
                        "metadata": {
                            "source": "hit-source.md",
                            "document_id": "hit-doc",
                            "document_version": "sha256:eeeeeeeeeeeeeeee",
                            "content_hash": "f" * 64,
                        },
                    }
                ],
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        rag_meta = followup["step"]["meta"]["rag"]
        self.assertEqual(rag_meta["chunks"], ["chunk object wins"])
        self.assertEqual(
            rag_meta["chunk_metadata"],
            [
                {
                    "source": "chunk-source.md",
                    "document_id": "chunk-doc",
                    "document_version": "sha256:cccccccccccccccc",
                    "content_hash": "d" * 64,
                }
            ],
        )
