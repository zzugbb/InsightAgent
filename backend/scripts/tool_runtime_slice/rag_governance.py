from __future__ import annotations

from .context import *


class RagGovernanceMixin:
    def test_ingest_knowledge_documents_redacts_sensitive_source_metadata_before_persist(
        self,
    ) -> None:
        class FakeCollection:
            def __init__(self) -> None:
                self.metadatas: list[dict[str, object]] = []

            def add(
                self,
                *,
                ids: list[str],
                documents: list[str],
                metadatas: list[dict[str, object]],
            ) -> None:
                self.metadatas = metadatas

            def count(self) -> int:
                return len(self.metadatas)

        class FakeClient:
            def __init__(self, collection: FakeCollection) -> None:
                self.collection = collection

            def get_or_create_collection(self, *, name: str) -> FakeCollection:
                return self.collection

        collection = FakeCollection()
        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient(collection)  # type: ignore[assignment]
        try:
            result = chroma_rag_module.ingest_knowledge_documents(
                user_id="user-rag-governance",
                knowledge_base_id="kb-rag-governance",
                documents=[
                    {
                        "text": "RAG governance should never persist raw source secrets.",
                        "source": (
                            "handbook.md?api_key=raw-secret&access_token=raw-token"
                        ),
                        "document_id": "doc-rag-governance",
                        "metadata": {
                            "Authorization": "Bearer raw-secret",
                            "owner": "ops token=raw-token",
                            "url": "https://example.test/path?api_key=raw-secret",
                            "kind": "handbook",
                        },
                    }
                ],
                chunk_size=120,
                chunk_overlap=0,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["chunks_added"], 1)
        self.assertEqual(len(collection.metadatas), 1)
        metadata = collection.metadatas[0]
        serialized = json.dumps(metadata, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("handbook", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Authorization", serialized)

    def test_query_knowledge_base_redacts_sensitive_hit_metadata_before_response(
        self,
    ) -> None:
        class FakeCollection:
            def count(self) -> int:
                return 1

            def query(
                self,
                *,
                query_texts: list[str],
                n_results: int,
            ) -> dict[str, object]:
                return {
                    "ids": [["hit-1"]],
                    "documents": [["safe retrieval content"]],
                    "distances": [[0.1]],
                    "metadatas": [
                        [
                            {
                                "source": (
                                    "handbook.md?api_key=raw-secret&access_token=raw-token"
                                ),
                                "Authorization": "Bearer raw-secret",
                                "owner": "ops token=raw-token",
                                "kind": "handbook",
                            }
                        ]
                    ],
                }

        class FakeClient:
            def get_collection(self, *, name: str) -> FakeCollection:
                return FakeCollection()

        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient()  # type: ignore[assignment]
        try:
            result = chroma_rag_module.query_knowledge_base(
                user_id="user-rag-governance",
                knowledge_base_id="kb-rag-governance",
                query_text="retrieval content",
                top_k=1,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["hit_count"], 1)
        hits = result["hits"]
        self.assertIsInstance(hits, list)
        metadata = hits[0]["metadata"]
        serialized = json.dumps(metadata, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("handbook", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Authorization", serialized)
