from __future__ import annotations

from .context import *


class RagGovernanceMixin:
    def test_get_knowledge_base_status_summarizes_safe_document_versions(
        self,
    ) -> None:
        test_case = self

        class FakeCollection:
            def count(self) -> int:
                return 4

            def get(self, *, include: list[str], limit: int) -> dict[str, object]:
                test_case.assertEqual(include, ["metadatas"])
                test_case.assertEqual(limit, 4)
                return {
                    "metadatas": [
                        {
                            "source": "handbook.md?api_key=raw-secret",
                            "document_id": "doc-1",
                            "document_version": "sha256:1111111111111111",
                            "content_hash": "a" * 64,
                            "chunk_index": 1,
                        },
                        {
                            "source": "handbook.md?api_key=raw-secret",
                            "document_id": "doc-1",
                            "document_version": "sha256:1111111111111111",
                            "content_hash": "a" * 64,
                            "chunk_index": 2,
                        },
                        {
                            "source": "runbook.md?access_token=raw-token",
                            "document_id": "doc-2 token=raw-token",
                            "document_version": "sha256:2222222222222222",
                            "content_hash": "b" * 64,
                            "chunk_index": 1,
                        },
                        {
                            "source": "legacy.md",
                            "document_id": "legacy-doc",
                            "document_version": "Bearer raw-secret",
                            "content_hash": "token=raw-token",
                        },
                    ]
                }

        class FakeClient:
            def heartbeat(self) -> None:
                return None

            def get_collection(self, *, name: str) -> FakeCollection:
                return FakeCollection()

        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient()  # type: ignore[assignment]
        try:
            result = chroma_rag_module.get_knowledge_base_status(
                user_id="user-rag-version-summary",
                knowledge_base_id="kb-rag-version-summary",
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertTrue(result["collection_exists"])
        self.assertEqual(result["document_count"], 4)
        self.assertEqual(result["unique_document_count"], 2)
        versions = result["document_versions"]
        self.assertEqual(
            versions,
            [
                {
                    "document_version": "sha256:1111111111111111",
                    "content_hash": "a" * 64,
                    "source": "handbook.md?[redacted]",
                    "document_id": "doc-1",
                    "chunk_count": 2,
                },
                {
                    "document_version": "sha256:2222222222222222",
                    "content_hash": "b" * 64,
                    "source": "runbook.md?[redacted]",
                    "document_id": "doc-2 [redacted]",
                    "chunk_count": 1,
                },
            ],
        )
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_list_knowledge_bases_summarizes_safe_document_versions(
        self,
    ) -> None:
        test_case = self
        collection_name = chroma_rag_module.rag_collection_name(
            "user-rag-version-list",
            "kb-rag-version-list",
        )

        class FakeCollection:
            def count(self) -> int:
                return 2

            def get(self, *, include: list[str], limit: int) -> dict[str, object]:
                return {
                    "metadatas": [
                        {
                            "source": "handbook.md?api_key=raw-secret",
                            "document_id": "doc-1",
                            "document_version": "sha256:aaaaaaaaaaaaaaaa",
                            "content_hash": "c" * 64,
                        },
                        {
                            "source": "handbook.md?api_key=raw-secret",
                            "document_id": "doc-1",
                            "document_version": "sha256:aaaaaaaaaaaaaaaa",
                            "content_hash": "c" * 64,
                        },
                    ]
                }

        class FakeClient:
            def heartbeat(self) -> None:
                return None

            def list_collections(self) -> list[dict[str, str]]:
                return [{"name": collection_name}]

            def get_collection(self, *, name: str) -> FakeCollection:
                test_case.assertEqual(name, collection_name)
                return FakeCollection()

        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient()  # type: ignore[assignment]
        try:
            result = chroma_rag_module.list_knowledge_bases(
                user_id="user-rag-version-list",
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        rows = result["knowledge_bases"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["document_count"], 2)
        self.assertEqual(row["unique_document_count"], 1)
        self.assertEqual(
            row["document_versions"],
            [
                {
                    "document_version": "sha256:aaaaaaaaaaaaaaaa",
                    "content_hash": "c" * 64,
                    "source": "handbook.md?[redacted]",
                    "document_id": "doc-1",
                    "chunk_count": 2,
                }
            ],
        )
        serialized = json.dumps(row, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("api_key", serialized)

    def test_get_rag_status_route_exposes_document_version_summary(self) -> None:
        original_status_helper = rag_routes_module.get_knowledge_base_status

        try:
            rag_routes_module.get_knowledge_base_status = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_base_id": "demo",
                    "collection": "kb_demo",
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "collection_exists": True,
                    "document_count": 2,
                    "unique_document_count": 1,
                    "document_versions": [
                        {
                            "document_version": "sha256:aaaaaaaaaaaaaaaa",
                            "content_hash": "c" * 64,
                            "source": "handbook.md",
                            "document_id": "doc-1",
                            "chunk_count": 2,
                        }
                    ],
                    "error": None,
                }
            )
            payload = rag_routes_module.get_rag_status(
                knowledge_base_id="demo",
                current_user={"id": "user-rag-route"},
            )
        finally:
            rag_routes_module.get_knowledge_base_status = original_status_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.document_count, 2)
        self.assertEqual(payload.unique_document_count, 1)
        self.assertEqual(len(payload.document_versions), 1)
        self.assertEqual(
            payload.document_versions[0].document_version,
            "sha256:aaaaaaaaaaaaaaaa",
        )
        self.assertEqual(payload.document_versions[0].chunk_count, 2)

    def test_ingest_knowledge_documents_adds_stable_document_version_metadata(
        self,
    ) -> None:
        class FakeCollection:
            def __init__(self) -> None:
                self.calls: list[list[dict[str, object]]] = []

            def add(
                self,
                *,
                ids: list[str],
                documents: list[str],
                metadatas: list[dict[str, object]],
            ) -> None:
                self.calls.append(metadatas)

            def count(self) -> int:
                return sum(len(call) for call in self.calls)

        class FakeClient:
            def __init__(self, collection: FakeCollection) -> None:
                self.collection = collection

            def get_or_create_collection(self, *, name: str) -> FakeCollection:
                return self.collection

        collection = FakeCollection()
        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient(collection)  # type: ignore[assignment]
        try:
            for text in [
                "Stable RAG document version metadata keeps all chunks auditable."
                * 4,
                "Stable RAG document version metadata keeps all chunks auditable."
                * 4,
                "Changed RAG document version metadata must produce a new version.",
            ]:
                chroma_rag_module.ingest_knowledge_documents(
                    user_id="user-rag-version",
                    knowledge_base_id="kb-rag-version",
                    documents=[
                        {
                            "text": text,
                            "source": "handbook.md",
                            "document_id": "doc-rag-version",
                        }
                    ],
                    chunk_size=80,
                    chunk_overlap=10,
                )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(len(collection.calls), 3)
        first_call = collection.calls[0]
        repeat_call = collection.calls[1]
        changed_call = collection.calls[2]
        self.assertGreater(len(first_call), 1)

        first_versions = {
            str(meta.get("document_version") or "") for meta in first_call
        }
        first_hashes = {str(meta.get("content_hash") or "") for meta in first_call}
        repeat_versions = {
            str(meta.get("document_version") or "") for meta in repeat_call
        }
        changed_versions = {
            str(meta.get("document_version") or "") for meta in changed_call
        }

        self.assertEqual(len(first_versions), 1)
        self.assertEqual(len(first_hashes), 1)
        first_version = next(iter(first_versions))
        first_hash = next(iter(first_hashes))
        self.assertRegex(first_version, r"^sha256:[a-f0-9]{16}$")
        self.assertRegex(first_hash, r"^[a-f0-9]{64}$")
        self.assertEqual(first_versions, repeat_versions)
        self.assertNotEqual(first_versions, changed_versions)

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
