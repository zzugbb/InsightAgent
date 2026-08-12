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

    def test_get_knowledge_base_status_canonicalizes_version_alias_metadata(
        self,
    ) -> None:
        class FakeCollection:
            def count(self) -> int:
                return 1

            def get(self, *, include: list[str], limit: int) -> dict[str, object]:
                return {
                    "metadatas": [
                        {
                            "source": "alias-guide.md",
                            "documentId": "doc-alias",
                            "documentVersion": "sha256:cccccccccccccccc",
                            "contentHash": "d" * 64,
                        }
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
                user_id="user-rag-version-alias",
                knowledge_base_id="kb-rag-version-alias",
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["unique_document_count"], 1)
        self.assertEqual(
            result["document_versions"],
            [
                {
                    "document_version": "sha256:cccccccccccccccc",
                    "content_hash": "d" * 64,
                    "source": "alias-guide.md",
                    "document_id": "doc-alias",
                    "chunk_count": 1,
                }
            ],
        )

    def test_get_knowledge_base_status_redacts_sensitive_chroma_error(
        self,
    ) -> None:
        original_http_client = chroma_rag_module._http_client

        def fail_http_client() -> object:
            raise RuntimeError(
                "chroma connect failed api_key=raw-secret Bearer raw-token"
            )

        chroma_rag_module._http_client = fail_http_client  # type: ignore[assignment]
        try:
            result = chroma_rag_module.get_knowledge_base_status(
                user_id="user-rag-error",
                knowledge_base_id="kb-rag-error",
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
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

    def test_list_knowledge_bases_redacts_sensitive_chroma_error(self) -> None:
        original_http_client = chroma_rag_module._http_client

        def fail_http_client() -> object:
            raise RuntimeError(
                "list failed access_token=raw-token Bearer raw-secret"
            )

        chroma_rag_module._http_client = fail_http_client  # type: ignore[assignment]
        try:
            result = chroma_rag_module.list_knowledge_bases(
                user_id="user-rag-list-error",
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_list_knowledge_bases_redacts_legacy_sensitive_collection_suffix(
        self,
    ) -> None:
        user_id = "user-rag-legacy-collection"
        prefix = chroma_rag_module._rag_collection_prefix(user_id)
        raw_collection_name = f"{prefix}team-api_key-raw-secret-token-raw-token"

        class FakeCollection:
            def count(self) -> int:
                return 0

        class FakeClient:
            def __init__(self) -> None:
                self.requested_collection_names: list[str] = []

            def heartbeat(self) -> None:
                return None

            def list_collections(self) -> list[dict[str, str]]:
                return [{"name": raw_collection_name}]

            def get_collection(self, *, name: str) -> FakeCollection:
                self.requested_collection_names.append(name)
                return FakeCollection()

        client = FakeClient()
        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: client  # type: ignore[assignment]
        try:
            result = chroma_rag_module.list_knowledge_bases(user_id=user_id)
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(client.requested_collection_names, [raw_collection_name])
        self.assertEqual(result["knowledge_base_count"], 1)
        row = result["knowledge_bases"][0]
        self.assertEqual(row["knowledge_base_id"], "team-redacted")
        self.assertEqual(row["collection"], f"{prefix}team-redacted")
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

    def test_list_knowledge_bases_with_shared_hides_private_shared_prefix_shadow(
        self,
    ) -> None:
        user_id = "user-rag-shared-boundary"
        private_kb = chroma_rag_module.rag_collection_name(user_id, "private-kb")
        private_shared_shadow = chroma_rag_module.rag_collection_name(
            user_id,
            "shared-shadow",
        )
        real_shared_kb = chroma_rag_module.rag_collection_name(
            chroma_rag_module.SHARED_RAG_SCOPE_USER_ID,
            "shared-canonical",
        )

        class FakeCollection:
            def count(self) -> int:
                return 0

        class FakeClient:
            def heartbeat(self) -> None:
                return None

            def list_collections(self) -> list[dict[str, str]]:
                return [
                    {"name": private_kb},
                    {"name": private_shared_shadow},
                    {"name": real_shared_kb},
                ]

            def get_collection(self, *, name: str) -> FakeCollection:
                return FakeCollection()

        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: FakeClient()  # type: ignore[assignment]
        try:
            result = chroma_rag_module.list_knowledge_bases_with_shared(
                user_id=user_id,
                include_shared=True,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        kb_ids = [
            str(row.get("knowledge_base_id") or "")
            for row in result["knowledge_bases"]
        ]
        self.assertEqual(kb_ids, ["private-kb", "shared-canonical"])
        self.assertNotIn("shared-shadow", kb_ids)

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

    def test_ingest_knowledge_documents_redacts_sensitive_knowledge_base_id(
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
                self.collection_name = ""

            def get_or_create_collection(self, *, name: str) -> FakeCollection:
                self.collection_name = name
                return self.collection

        collection = FakeCollection()
        client = FakeClient(collection)
        original_http_client = chroma_rag_module._http_client
        chroma_rag_module._http_client = lambda: client  # type: ignore[assignment]
        try:
            result = chroma_rag_module.ingest_knowledge_documents(
                user_id="user-rag-kb-id-governance",
                knowledge_base_id="team?api_key=raw-secret&token=raw-token",
                documents=[
                    {
                        "text": "Sensitive knowledge base IDs must be safe.",
                        "source": "handbook.md",
                        "document_id": "doc-rag-kb-id",
                    }
                ],
                chunk_size=120,
                chunk_overlap=0,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["knowledge_base_id"], "team-redacted-redacted")
        self.assertIn("team-redacted-redacted", result["collection"])
        self.assertEqual(client.collection_name, result["collection"])
        self.assertEqual(
            collection.metadatas[0]["knowledge_base_id"],
            result["knowledge_base_id"],
        )
        serialized = json.dumps(
            {
                "result": result,
                "metadatas": collection.metadatas,
                "collection_name": client.collection_name,
            },
            ensure_ascii=False,
        )
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

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

    def test_ingest_knowledge_documents_rejects_user_metadata_reserved_overrides(
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
                user_id="user-rag-reserved-metadata",
                knowledge_base_id="kb-rag-reserved-metadata",
                documents=[
                    {
                        "text": "Reserved RAG metadata must stay canonical." * 4,
                        "source": "canonical.md",
                        "document_id": "canonical-doc",
                        "metadata": {
                            "source": "evil.md?api_key=raw-secret",
                            "document_id": "evil-doc",
                            "knowledge_base_id": "evil-kb",
                            "document_version": "sha256:ffffffffffffffff",
                            "content_hash": "e" * 64,
                            "chunk_index": "999",
                            "chunk_total": "999",
                            "kind": "handbook",
                        },
                    }
                ],
                chunk_size=120,
                chunk_overlap=0,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["chunks_added"], len(collection.metadatas))
        self.assertGreater(len(collection.metadatas), 1)
        versions = {
            str(meta.get("document_version") or "") for meta in collection.metadatas
        }
        hashes = {
            str(meta.get("content_hash") or "") for meta in collection.metadatas
        }
        self.assertEqual(len(versions), 1)
        self.assertEqual(len(hashes), 1)
        self.assertNotEqual(versions, {"sha256:ffffffffffffffff"})
        self.assertNotEqual(hashes, {"e" * 64})
        for index, metadata in enumerate(collection.metadatas, start=1):
            self.assertEqual(metadata["knowledge_base_id"], "kb-rag-reserved-metadata")
            self.assertEqual(metadata["source"], "canonical.md")
            self.assertEqual(metadata["document_id"], "canonical-doc")
            self.assertEqual(metadata["chunk_index"], index)
            self.assertEqual(metadata["chunk_total"], len(collection.metadatas))
            self.assertEqual(metadata["kind"], "handbook")
        serialized = json.dumps(collection.metadatas, ensure_ascii=False)
        self.assertNotIn("evil", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("api_key", serialized)

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

    def test_query_knowledge_base_filters_invalid_version_metadata_before_response(
        self,
    ) -> None:
        class FakeCollection:
            def count(self) -> int:
                return 2

            def query(
                self,
                *,
                query_texts: list[str],
                n_results: int,
            ) -> dict[str, object]:
                return {
                    "ids": [["hit-safe", "hit-poisoned"]],
                    "documents": [["safe version content", "poisoned version content"]],
                    "distances": [[0.1, 0.2]],
                    "metadatas": [
                        [
                            {
                                "source": "safe.md",
                                "document_id": "doc-safe",
                                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                                "content_hash": "b" * 64,
                            },
                            {
                                "source": "poisoned.md?api_key=raw-secret",
                                "document_id": "doc-poisoned token=raw-token",
                                "document_version": "Bearer raw-secret",
                                "content_hash": "token=raw-token",
                            },
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
                user_id="user-rag-query-version",
                knowledge_base_id="kb-rag-query-version",
                query_text="version content",
                top_k=2,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(result["hit_count"], 2)
        hits = result["hits"]
        self.assertIsInstance(hits, list)
        self.assertEqual(
            hits[0]["metadata"],
            {
                "source": "safe.md",
                "document_id": "doc-safe",
                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                "content_hash": "b" * 64,
            },
        )
        poisoned_metadata = hits[1]["metadata"]
        self.assertEqual(poisoned_metadata["source"], "poisoned.md?[redacted]")
        self.assertEqual(poisoned_metadata["document_id"], "doc-poisoned [redacted]")
        self.assertNotIn("document_version", poisoned_metadata)
        self.assertNotIn("content_hash", poisoned_metadata)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_post_rag_query_redacts_sensitive_service_error_detail(self) -> None:
        original_query = rag_routes_module.query_knowledge_base

        def fail_query(**_kwargs: object) -> object:
            raise RuntimeError(
                "query failed api_key=raw-secret Bearer raw-token"
            )

        rag_routes_module.query_knowledge_base = fail_query  # type: ignore[attr-defined]
        try:
            with self.assertRaises(rag_routes_module.HTTPException) as ctx:
                rag_routes_module.post_rag_query(
                    payload=rag_routes_module.RagQueryRequest(
                        query="hello",
                        knowledge_base_id="kb-route-error",
                    ),
                    current_user={"id": "user-rag-route-error"},
                )
        finally:
            rag_routes_module.query_knowledge_base = original_query  # type: ignore[attr-defined]

        self.assertEqual(ctx.exception.status_code, 503)
        detail = str(ctx.exception.detail)
        self.assertIn("[redacted]", detail)
        self.assertNotIn("raw-secret", detail)
        self.assertNotIn("raw-token", detail)
        self.assertNotIn("api_key", detail)
        self.assertNotIn("Bearer", detail)

    def test_query_knowledge_base_canonicalizes_safe_version_metadata_aliases(
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
                    "ids": [["hit-alias"]],
                    "documents": [["safe alias content"]],
                    "distances": [[0.1]],
                    "metadatas": [
                        [
                            {
                                "source": "alias.md",
                                "documentId": "doc-alias",
                                "documentVersion": "sha256:cccccccccccccccc",
                                "contentHash": "d" * 64,
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
                user_id="user-rag-query-version-alias",
                knowledge_base_id="kb-rag-query-version-alias",
                query_text="alias content",
                top_k=1,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[assignment]

        self.assertEqual(
            result["hits"][0]["metadata"],
            {
                "source": "alias.md",
                "document_id": "doc-alias",
                "document_version": "sha256:cccccccccccccccc",
                "content_hash": "d" * 64,
            },
        )
