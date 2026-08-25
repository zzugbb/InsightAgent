from __future__ import annotations

from .context import *


class RagRouteGovernanceMixin:
    def test_rag_route_value_error_details_are_redacted(self) -> None:
        original_ingest = rag_routes_module.ingest_knowledge_documents
        original_query = rag_routes_module.query_knowledge_base
        original_clear = rag_routes_module.clear_knowledge_base
        original_delete = rag_routes_module.delete_knowledge_base
        original_document_delete = rag_routes_module.delete_knowledge_base_document

        def fail_with_sensitive_value_error(**_kwargs: object) -> object:
            raise ValueError(
                "invalid rag request api_key=raw-secret Bearer raw-token"
            )

        rag_routes_module.ingest_knowledge_documents = fail_with_sensitive_value_error  # type: ignore[attr-defined]
        rag_routes_module.query_knowledge_base = fail_with_sensitive_value_error  # type: ignore[attr-defined]
        rag_routes_module.clear_knowledge_base = fail_with_sensitive_value_error  # type: ignore[attr-defined]
        rag_routes_module.delete_knowledge_base = fail_with_sensitive_value_error  # type: ignore[attr-defined]
        rag_routes_module.delete_knowledge_base_document = fail_with_sensitive_value_error  # type: ignore[attr-defined]
        try:
            route_calls = [
                lambda: rag_routes_module.post_rag_ingest(
                    payload=rag_routes_module.RagIngestRequest(
                        knowledge_base_id="kb-route-value-error",
                        documents=[
                            rag_routes_module.RagDocumentInput(text="safe"),
                        ],
                    ),
                    current_user={"id": "user-rag-route-value-error"},
                ),
                lambda: rag_routes_module.post_rag_query(
                    payload=rag_routes_module.RagQueryRequest(
                        query="safe",
                        knowledge_base_id="kb-route-value-error",
                    ),
                    current_user={"id": "user-rag-route-value-error"},
                ),
                lambda: rag_routes_module.post_rag_clear_knowledge_base(
                    knowledge_base_id="kb-route-value-error",
                    current_user={"id": "user-rag-route-value-error"},
                ),
                lambda: rag_routes_module.delete_rag_knowledge_base(
                    knowledge_base_id="kb-route-value-error",
                    current_user={"id": "user-rag-route-value-error"},
                ),
                lambda: rag_routes_module.delete_rag_knowledge_base_document(
                    knowledge_base_id="kb-route-value-error",
                    source="api-docs",
                    document_id="release-notes",
                    current_user={"id": "user-rag-route-value-error"},
                ),
            ]
            details: list[str] = []
            for call in route_calls:
                with self.assertRaises(rag_routes_module.HTTPException) as ctx:
                    call()
                self.assertEqual(ctx.exception.status_code, 400)
                details.append(str(ctx.exception.detail))
        finally:
            rag_routes_module.ingest_knowledge_documents = original_ingest  # type: ignore[attr-defined]
            rag_routes_module.query_knowledge_base = original_query  # type: ignore[attr-defined]
            rag_routes_module.clear_knowledge_base = original_clear  # type: ignore[attr-defined]
            rag_routes_module.delete_knowledge_base = original_delete  # type: ignore[attr-defined]
            rag_routes_module.delete_knowledge_base_document = original_document_delete  # type: ignore[attr-defined]

        serialized = json.dumps(details, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_post_rag_ingest_redacts_sensitive_service_identifiers_for_response_and_audit(
        self,
    ) -> None:
        original_ingest = rag_routes_module.ingest_knowledge_documents
        original_audit = rag_routes_module.safe_record_audit_event
        audit_calls: list[dict[str, object]] = []

        try:
            rag_routes_module.ingest_knowledge_documents = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_base_id": "team-api_key-raw-secret-token-raw-token",
                    "collection": "kb_abc123_team-api_key-raw-secret-token-raw-token",
                    "documents_ingested": 1,
                    "chunks_added": 1,
                    "document_count": 1,
                    "chunk_size": 120,
                    "chunk_overlap": 0,
                }
            )
            rag_routes_module.safe_record_audit_event = (  # type: ignore[assignment]
                lambda **kwargs: audit_calls.append(kwargs)
            )
            payload = rag_routes_module.post_rag_ingest(
                payload=rag_routes_module.RagIngestRequest(
                    knowledge_base_id="team-safe",
                    documents=[
                        rag_routes_module.RagDocumentInput(
                            text="Route RAG identifiers must be safe.",
                        )
                    ],
                    chunk_size=120,
                    chunk_overlap=0,
                ),
                current_user={"id": "user-rag-route-governance"},
            )
        finally:
            rag_routes_module.ingest_knowledge_documents = original_ingest  # type: ignore[attr-defined]
            rag_routes_module.safe_record_audit_event = original_audit  # type: ignore[assignment]

        self.assertEqual(payload.knowledge_base_id, "team-redacted")
        self.assertEqual(payload.collection, "kb_abc123_team-redacted")
        self.assertEqual(len(audit_calls), 1)
        audit_detail = audit_calls[0]["detail"]
        self.assertEqual(audit_detail["knowledge_base_id"], "team-redacted")
        self.assertEqual(audit_detail["collection"], "kb_abc123_team-redacted")
        serialized = json.dumps(
            {"payload": payload.model_dump(), "audit": audit_calls},
            ensure_ascii=False,
        )
        self.assertIn("redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

    def test_delete_rag_knowledge_base_document_audits_safe_source_document(
        self,
    ) -> None:
        original_document_delete = rag_routes_module.delete_knowledge_base_document
        original_audit = rag_routes_module.safe_record_audit_event
        audit_calls: list[dict[str, object]] = []

        try:
            rag_routes_module.delete_knowledge_base_document = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_base_id": "team-api_key-raw-secret-token-raw-token",
                    "collection": "kb_abc123_team-api_key-raw-secret-token-raw-token",
                    "source": "handbook.md?api_key=raw-secret",
                    "document_id": "doc-1 token=raw-token",
                    "existed": True,
                    "deleted_chunks": 2,
                    "document_count": 1,
                }
            )
            rag_routes_module.safe_record_audit_event = (  # type: ignore[assignment]
                lambda **kwargs: audit_calls.append(kwargs)
            )
            payload = rag_routes_module.delete_rag_knowledge_base_document(
                knowledge_base_id="team-safe",
                source="handbook.md",
                document_id="doc-1",
                current_user={"id": "user-rag-document-delete"},
            )
        finally:
            rag_routes_module.delete_knowledge_base_document = original_document_delete  # type: ignore[attr-defined]
            rag_routes_module.safe_record_audit_event = original_audit  # type: ignore[assignment]

        self.assertEqual(payload.knowledge_base_id, "team-redacted")
        self.assertEqual(payload.collection, "kb_abc123_team-redacted")
        self.assertEqual(payload.source, "handbook.md?[redacted]")
        self.assertEqual(payload.document_id, "doc-1 [redacted]")
        self.assertEqual(payload.deleted_chunks, 2)
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(audit_calls[0]["event_type"], "rag_document_delete")
        audit_detail = audit_calls[0]["detail"]
        self.assertEqual(audit_detail["source"], "handbook.md?[redacted]")
        self.assertEqual(audit_detail["document_id"], "doc-1 [redacted]")
        serialized = json.dumps(
            {"payload": payload.model_dump(), "audit": audit_calls},
            ensure_ascii=False,
        )
        self.assertIn("redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

    def test_post_rag_query_redacts_sensitive_service_identifiers_for_response(
        self,
    ) -> None:
        original_query = rag_routes_module.query_knowledge_base

        try:
            rag_routes_module.query_knowledge_base = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_base_id": "team-api_key-raw-secret-token-raw-token",
                    "collection": "kb_abc123_team-api_key-raw-secret-token-raw-token",
                    "hits": [{"id": "chunk-1", "content": "safe", "metadata": {}}],
                    "hit_count": 1,
                }
            )
            payload = rag_routes_module.post_rag_query(
                payload=rag_routes_module.RagQueryRequest(
                    query="safe",
                    knowledge_base_id="team-safe",
                    top_k=1,
                ),
                current_user={"id": "user-rag-route-governance"},
            )
        finally:
            rag_routes_module.query_knowledge_base = original_query  # type: ignore[attr-defined]

        self.assertEqual(payload.knowledge_base_id, "team-redacted")
        self.assertEqual(payload.collection, "kb_abc123_team-redacted")
        serialized = json.dumps(payload.model_dump(), ensure_ascii=False)
        self.assertIn("redacted", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)

    def test_rag_route_document_version_source_fields_are_redacted(self) -> None:
        original_status = rag_routes_module.get_knowledge_base_status
        original_list = rag_routes_module.list_knowledge_bases_with_shared

        sensitive_document_versions = [
            {
                "document_version": "sha256:aaaaaaaaaaaaaaaa",
                "content_hash": "b" * 64,
                "source": "handbook.md?api_key=raw-secret",
                "document_id": "doc-1 token=raw-token",
                "chunk_count": 2,
            }
        ]

        try:
            rag_routes_module.get_knowledge_base_status = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_base_id": "team-api_key-raw-secret-token-raw-token",
                    "collection": "kb_abc123_team-api_key-raw-secret-token-raw-token",
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "collection_exists": True,
                    "document_count": 2,
                    "unique_document_count": 1,
                    "document_versions": sensitive_document_versions,
                    "error": None,
                }
            )
            rag_routes_module.list_knowledge_bases_with_shared = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "knowledge_bases": [
                        {
                            "knowledge_base_id": (
                                "team-api_key-raw-secret-token-raw-token"
                            ),
                            "collection": (
                                "kb_abc123_team-api_key-raw-secret-token-raw-token"
                            ),
                            "document_count": 2,
                            "unique_document_count": 1,
                            "document_versions": sensitive_document_versions,
                        }
                    ],
                    "knowledge_base_count": 1,
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "error": None,
                }
            )

            status_payload = rag_routes_module.get_rag_status(
                knowledge_base_id="team-safe",
                current_user={"id": "user-rag-route-source"},
            )
            list_payload = rag_routes_module.get_rag_knowledge_bases(
                current_user={"id": "user-rag-route-source"},
            )
        finally:
            rag_routes_module.get_knowledge_base_status = original_status  # type: ignore[attr-defined]
            rag_routes_module.list_knowledge_bases_with_shared = original_list  # type: ignore[attr-defined]

        self.assertEqual(
            status_payload.document_versions[0].source,
            "handbook.md?[redacted]",
        )
        self.assertEqual(
            status_payload.document_versions[0].document_id,
            "doc-1 [redacted]",
        )
        self.assertEqual(
            list_payload.knowledge_bases[0].document_versions[0].source,
            "handbook.md?[redacted]",
        )
        self.assertEqual(
            list_payload.knowledge_bases[0].document_versions[0].document_id,
            "doc-1 [redacted]",
        )
        serialized = json.dumps(
            {
                "status": status_payload.model_dump(),
                "list": list_payload.model_dump(),
            },
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("raw-token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("token=", serialized)
