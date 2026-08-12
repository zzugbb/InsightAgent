from __future__ import annotations

from .context import *


class RagRouteGovernanceMixin:
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
