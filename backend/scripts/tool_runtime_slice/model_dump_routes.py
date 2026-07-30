from __future__ import annotations

from .context import *


class ModelDumpRoutesMixin:
    def test_execute_tool_plan_item_service_actions_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-direct-service-action-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-direct-service-action-http-json-output",
            "step": raw_step,
        }
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=[
                    {
                        "kind": "trace_write",
                        "trace_step": raw_step,
                        "trace_event": trace_event,
                        "persist_force": True,
                    },
                    {
                        "kind": "emit_state",
                        "event": "state",
                        "data": {"trace_step": raw_step, "trace_event": trace_event},
                    },
                ],
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        serialized = json.dumps(
            {
                "items": items,
                "trace_steps": trace_steps,
                "tool_observations": tool_observations,
                "complete_calls": complete_calls,
                "failure_calls": failure_calls,
            },
            ensure_ascii=False,
        )
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)
        self.assertEqual(persist_forces, [True])

    def test_execute_tool_plan_item_service_actions_keeps_return_shape(self) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
                "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                },
                "persist_force": True,
            },
            {
                "kind": "complete_task",
                "kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
            },
            {
                "kind": "record_failure_event",
                "kwargs": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "fatal",
                    "detail": {"step_id": "step-1", "retry_count": 1},
                },
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": {"task_id": "task-1", "phase": "error"},
            },
            {
                "kind": "return",
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        self.assertEqual([item["kind"] for item in items], ["event", "event", "result"])
        self.assertEqual([item["event"] for item in items[:2]], ["trace", "state"])
        self.assertEqual(items[-1]["result"], {"seq_cursor": 3, "should_return": True})
        self.assertEqual([step["id"] for step in trace_steps], ["existing-1", "step-1"])
        self.assertEqual(tool_observations, [])
        self.assertEqual(persist_forces, [True])
        self.assertEqual(complete_calls, [service_actions[1]["kwargs"]])
        self.assertEqual(failure_calls, [service_actions[2]["kwargs"]])

    def test_normalize_query_metadatas_accepts_model_items(self) -> None:
        class ResponseReadyMetadata:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chroma_memory_module._normalize_query_metadatas(  # type: ignore[attr-defined]
            [
                (
                    ResponseReadyMetadata(
                        {"task_id": "task-1", "kind": "task_summary"}
                    ),
                    None,
                )
            ],
            [["memory-1", "memory-2"]],
        )

        self.assertEqual(
            payload,
            [[{"task_id": "task-1", "kind": "task_summary"}, {}]],
        )

    def test_query_session_memory_coerces_model_metadata_items(self) -> None:
        original_http_client = chroma_memory_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyMetadata:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class FakeCollection:
            def count(self) -> int:
                return 2

            def query(self, **_kwargs):
                return {
                    "ids": [["memory-1", "memory-2"]],
                    "documents": [["alpha", "beta"]],
                    "distances": [[0.12, 0.34]],
                    "metadatas": [
                        (
                            ResponseReadyMetadata(
                                {"task_id": "task-1", "kind": "task_summary"}
                            ),
                            ResponseReadyMetadata(
                                {"task_id": "task-2", "kind": "task_summary"}
                            ),
                        )
                    ],
                }

        class FakeClient:
            def get_collection(self, *, name: str):
                self.last_name = name
                return FakeCollection()

        fake_client = FakeClient()
        try:
            chroma_memory_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_memory_module.query_session_memory(
                "session-memory-model-meta",
                "memory query",
                n_results=4,
            )
        finally:
            chroma_memory_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(
            payload["metadatas"],
            [
                [
                    {"task_id": "task-1", "kind": "task_summary"},
                    {"task_id": "task-2", "kind": "task_summary"},
                ]
            ],
        )
        self.assertEqual(payload["documents"], [["alpha", "beta"]])
        self.assertEqual(payload["ids"], [["memory-1", "memory-2"]])

    def test_query_knowledge_base_coerces_model_metadata_items(self) -> None:
        original_http_client = chroma_rag_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyMetadata:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class FakeCollection:
            def count(self) -> int:
                return 2

            def query(self, **_kwargs):
                return {
                    "ids": [["chunk-1", "chunk-2"]],
                    "documents": [["alpha", "beta"]],
                    "distances": [[0.12, 0.34]],
                    "metadatas": [
                        (
                            ResponseReadyMetadata(
                                {"source": "doc-a", "document_id": "doc-1"}
                            ),
                            ResponseReadyMetadata(
                                {"source": "doc-b", "document_id": "doc-2"}
                            ),
                        )
                    ],
                }

        class FakeClient:
            def get_collection(self, *, name: str):
                self.last_name = name
                return FakeCollection()

        fake_client = FakeClient()
        try:
            chroma_rag_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_rag_module.query_knowledge_base(
                user_id="user-rag-model-meta",
                knowledge_base_id="demo",
                query_text="rag query",
                top_k=4,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(payload["knowledge_base_id"], "demo")
        self.assertEqual(payload["hit_count"], 2)
        self.assertEqual(
            payload["hits"],
            [
                {
                    "id": "chunk-1",
                    "content": "alpha",
                    "distance": 0.12,
                    "metadata": {"source": "doc-a", "document_id": "doc-1"},
                },
                {
                    "id": "chunk-2",
                    "content": "beta",
                    "distance": 0.34,
                    "metadata": {"source": "doc-b", "document_id": "doc-2"},
                },
            ],
        )

    def test_query_session_memory_accepts_model_dump_query_payload(self) -> None:
        original_http_client = chroma_memory_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyQueryPayload:
            def model_dump(self):
                return {
                    "ids": [["memory-1"]],
                    "documents": [["alpha"]],
                    "distances": [[0.12]],
                    "metadatas": [[{"task_id": "task-1", "kind": "task_summary"}]],
                }

        class FakeCollection:
            def count(self) -> int:
                return 1

            def query(self, **_kwargs):
                return ResponseReadyQueryPayload()

        class FakeClient:
            def get_collection(self, *, name: str):
                self.last_name = name
                return FakeCollection()

        fake_client = FakeClient()
        try:
            chroma_memory_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_memory_module.query_session_memory(
                "session-memory-model-root",
                "memory query",
                n_results=4,
            )
        finally:
            chroma_memory_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(payload["ids"], [["memory-1"]])
        self.assertEqual(payload["documents"], [["alpha"]])
        self.assertEqual(payload["distances"], [[0.12]])
        self.assertEqual(
            payload["metadatas"],
            [[{"task_id": "task-1", "kind": "task_summary"}]],
        )

    def test_query_knowledge_base_accepts_model_dump_query_payload(self) -> None:
        original_http_client = chroma_rag_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyQueryPayload:
            def model_dump(self):
                return {
                    "ids": [["chunk-1"]],
                    "documents": [["alpha"]],
                    "distances": [[0.12]],
                    "metadatas": [[{"source": "doc-a", "document_id": "doc-1"}]],
                }

        class FakeCollection:
            def count(self) -> int:
                return 1

            def query(self, **_kwargs):
                return ResponseReadyQueryPayload()

        class FakeClient:
            def get_collection(self, *, name: str):
                self.last_name = name
                return FakeCollection()

        fake_client = FakeClient()
        try:
            chroma_rag_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_rag_module.query_knowledge_base(
                user_id="user-rag-model-root",
                knowledge_base_id="demo",
                query_text="rag query",
                top_k=4,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(payload["knowledge_base_id"], "demo")
        self.assertEqual(payload["hit_count"], 1)
        self.assertEqual(
            payload["hits"],
            [
                {
                    "id": "chunk-1",
                    "content": "alpha",
                    "distance": 0.12,
                    "metadata": {"source": "doc-a", "document_id": "doc-1"},
                }
            ],
        )

    def test_ingest_knowledge_documents_accepts_model_document_rows(self) -> None:
        original_http_client = chroma_rag_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyDocumentRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class FakeCollection:
            def __init__(self):
                self.add_calls: list[dict[str, object]] = []

            def add(self, **kwargs):
                self.add_calls.append(kwargs)

            def count(self) -> int:
                return 2

        class FakeClient:
            def __init__(self):
                self.collection = FakeCollection()

            def get_or_create_collection(self, *, name: str):
                self.last_name = name
                return self.collection

        fake_client = FakeClient()
        try:
            chroma_rag_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_rag_module.ingest_knowledge_documents(
                user_id="user-rag-model-doc",
                knowledge_base_id="demo",
                documents=[
                    ResponseReadyDocumentRow(
                        {
                            "text": "alpha beta gamma",
                            "source": "typed-source",
                            "document_id": "doc-1",
                            "metadata": {"topic": "plans"},
                        }
                    )
                ],
                chunk_size=50,
                chunk_overlap=10,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(payload["knowledge_base_id"], "demo")
        self.assertEqual(payload["documents_ingested"], 1)
        self.assertEqual(payload["chunks_added"], 1)
        self.assertEqual(len(fake_client.collection.add_calls), 1)
        self.assertEqual(
            fake_client.collection.add_calls[0]["documents"],
            ["alpha beta gamma"],
        )
        self.assertEqual(
            fake_client.collection.add_calls[0]["metadatas"],
            [
                {
                    "knowledge_base_id": "demo",
                    "source": "typed-source",
                    "document_id": "doc-1",
                    "chunk_index": 1,
                    "chunk_total": 1,
                    "topic": "plans",
                }
            ],
        )

    def test_ingest_knowledge_documents_accepts_model_metadata_rows(self) -> None:
        original_http_client = chroma_rag_module._http_client  # type: ignore[attr-defined]

        class ResponseReadyMetadata:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class FakeCollection:
            def __init__(self):
                self.add_calls: list[dict[str, object]] = []

            def add(self, **kwargs):
                self.add_calls.append(kwargs)

            def count(self) -> int:
                return 2

        class FakeClient:
            def __init__(self):
                self.collection = FakeCollection()

            def get_or_create_collection(self, *, name: str):
                self.last_name = name
                return self.collection

        fake_client = FakeClient()
        try:
            chroma_rag_module._http_client = lambda: fake_client  # type: ignore[attr-defined]
            payload = chroma_rag_module.ingest_knowledge_documents(
                user_id="user-rag-model-meta-row",
                knowledge_base_id="demo",
                documents=[
                    {
                        "text": "alpha beta gamma",
                        "source": "typed-source",
                        "document_id": "doc-1",
                        "metadata": ResponseReadyMetadata({"topic": "plans"}),
                    }
                ],
                chunk_size=50,
                chunk_overlap=10,
            )
        finally:
            chroma_rag_module._http_client = original_http_client  # type: ignore[attr-defined]

        self.assertEqual(payload["documents_ingested"], 1)
        self.assertEqual(
            fake_client.collection.add_calls[0]["metadatas"],
            [
                {
                    "knowledge_base_id": "demo",
                    "source": "typed-source",
                    "document_id": "doc-1",
                    "chunk_index": 1,
                    "chunk_total": 1,
                    "topic": "plans",
                }
            ],
        )

    def test_get_rag_knowledge_bases_accepts_model_dump_payload_and_rows(self) -> None:
        original_list_helper = rag_routes_module.list_knowledge_bases_with_shared

        class ResponseReadyRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "knowledge_bases": [
                        ResponseReadyRow(
                            {
                                "knowledge_base_id": "demo",
                                "collection": "kb_demo",
                                "document_count": 3,
                            }
                        )
                    ],
                    "knowledge_base_count": 1,
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "error": None,
                }

        try:
            rag_routes_module.list_knowledge_bases_with_shared = (  # type: ignore[attr-defined]
                lambda **_kwargs: ResponseReadyPayload()
            )
            payload = rag_routes_module.get_rag_knowledge_bases(
                current_user={"id": "user-rag-route"},
            )
        finally:
            rag_routes_module.list_knowledge_bases_with_shared = original_list_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.knowledge_base_count, 1)
        self.assertEqual(payload.knowledge_bases[0].knowledge_base_id, "demo")
        self.assertEqual(payload.knowledge_bases[0].document_count, 3)

    def test_post_rag_query_accepts_model_dump_payload_and_hits(self) -> None:
        original_query_helper = rag_routes_module.query_knowledge_base

        class ResponseReadyHit:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "knowledge_base_id": "demo",
                    "collection": "kb_demo",
                    "hits": [
                        ResponseReadyHit(
                            {
                                "id": "chunk-1",
                                "content": "alpha",
                                "distance": 0.12,
                                "metadata": {"source": "doc-a"},
                            }
                        )
                    ],
                    "hit_count": 1,
                }

        try:
            rag_routes_module.query_knowledge_base = (  # type: ignore[attr-defined]
                lambda **_kwargs: ResponseReadyPayload()
            )
            payload = rag_routes_module.post_rag_query(
                payload=rag_routes_module.RagQueryRequest(query="demo", knowledge_base_id="demo", top_k=3),
                current_user={"id": "user-rag-route"},
            )
        finally:
            rag_routes_module.query_knowledge_base = original_query_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.knowledge_base_id, "demo")
        self.assertEqual(payload.hit_count, 1)
        self.assertEqual(payload.hits[0].id, "chunk-1")
        self.assertEqual(payload.hits[0].metadata, {"source": "doc-a"})

    def test_post_rag_clear_accepts_model_dump_payload_for_audit_and_response(
        self,
    ) -> None:
        original_clear_helper = rag_routes_module.clear_knowledge_base
        original_audit_helper = rag_routes_module.safe_record_audit_event

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "knowledge_base_id": "shared-demo",
                    "collection": "kb_shared_demo",
                    "existed": True,
                    "deleted_chunks": 5,
                    "document_count": 0,
                }

        audit_calls: list[dict[str, object]] = []
        try:
            rag_routes_module.clear_knowledge_base = (  # type: ignore[attr-defined]
                lambda **_kwargs: ResponseReadyPayload()
            )
            rag_routes_module.safe_record_audit_event = lambda **kwargs: audit_calls.append(kwargs)  # type: ignore[assignment]
            payload = rag_routes_module.post_rag_clear_knowledge_base(
                "shared-demo",
                current_user={"id": "user-rag-route", "role": "admin"},
            )
        finally:
            rag_routes_module.clear_knowledge_base = original_clear_helper  # type: ignore[attr-defined]
            rag_routes_module.safe_record_audit_event = original_audit_helper  # type: ignore[assignment]

        self.assertEqual(payload.knowledge_base_id, "shared-demo")
        self.assertTrue(payload.existed)
        self.assertEqual(payload.deleted_chunks, 5)
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(audit_calls[0]["detail"]["knowledge_base_id"], "shared-demo")
        self.assertEqual(audit_calls[0]["detail"]["deleted_chunks"], 5)

    def test_list_knowledge_bases_with_shared_coerces_typed_roots_and_rows(
        self,
    ) -> None:
        original_list_helper = chroma_rag_module.list_knowledge_bases

        class ResponseReadyRow:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        class ResponseReadyPayload:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        def fake_list_knowledge_bases(*, user_id: str):
            if user_id == chroma_rag_module.SHARED_RAG_SCOPE_USER_ID:  # type: ignore[attr-defined]
                return ResponseReadyPayload(
                    {
                        "knowledge_bases": [
                            ResponseReadyRow(
                                {
                                    "knowledge_base_id": "shared-demo",
                                    "collection": "kb_shared_demo",
                                    "document_count": 2,
                                }
                            )
                        ],
                        "knowledge_base_count": 1,
                        "chroma_url": "http://127.0.0.1:8001",
                        "chroma_reachable": True,
                        "error": None,
                    }
                )
            return ResponseReadyPayload(
                {
                    "knowledge_bases": [
                        ResponseReadyRow(
                            {
                                "knowledge_base_id": "demo",
                                "collection": "kb_demo",
                                "document_count": 3,
                            }
                        )
                    ],
                    "knowledge_base_count": 1,
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "error": None,
                }
            )

        try:
            chroma_rag_module.list_knowledge_bases = fake_list_knowledge_bases  # type: ignore[assignment]
            payload = chroma_rag_module.list_knowledge_bases_with_shared(
                user_id="user-rag-service",
                include_shared=True,
            )
        finally:
            chroma_rag_module.list_knowledge_bases = original_list_helper  # type: ignore[assignment]

        self.assertEqual(payload["knowledge_base_count"], 2)
        self.assertEqual(
            payload["knowledge_bases"],
            [
                {
                    "knowledge_base_id": "demo",
                    "collection": "kb_demo",
                    "document_count": 3,
                },
                {
                    "knowledge_base_id": "shared-demo",
                    "collection": "kb_shared_demo",
                    "document_count": 2,
                },
            ],
        )

    def test_list_knowledge_bases_with_shared_coerces_typed_root_without_shared(
        self,
    ) -> None:
        original_list_helper = chroma_rag_module.list_knowledge_bases

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "knowledge_bases": [],
                    "knowledge_base_count": 0,
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "error": None,
                }

        try:
            chroma_rag_module.list_knowledge_bases = lambda **_kwargs: ResponseReadyPayload()  # type: ignore[assignment]
            payload = chroma_rag_module.list_knowledge_bases_with_shared(
                user_id="user-rag-service",
                include_shared=False,
            )
        finally:
            chroma_rag_module.list_knowledge_bases = original_list_helper  # type: ignore[assignment]

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["knowledge_base_count"], 0)
        self.assertEqual(payload["knowledge_bases"], [])

    def test_get_session_memory_status_route_accepts_model_dump_payload(self) -> None:
        original_get_session = session_routes_module.get_session
        original_status_helper = session_routes_module.get_session_memory_status

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "collection": "memory_session-1",
                    "chroma_url": "http://127.0.0.1:8001",
                    "chroma_reachable": True,
                    "collection_exists": True,
                    "document_count": 4,
                    "error": None,
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "id": "session-1"
            }
            session_routes_module.get_session_memory_status = (  # type: ignore[assignment]
                lambda _session_id: ResponseReadyPayload()
            )
            payload = session_routes_module.get_session_memory_status_route(
                "session-1",
                current_user={"id": "user-1"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.get_session_memory_status = original_status_helper  # type: ignore[assignment]

        self.assertEqual(payload.collection, "memory_session-1")
        self.assertTrue(payload.collection_exists)
        self.assertEqual(payload.document_count, 4)

    def test_get_session_usage_summary_route_accepts_model_dump_payload(self) -> None:
        original_get_session = session_routes_module.get_session
        original_usage_helper = session_routes_module.get_session_usage_summary

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "tasks_total": 4,
                    "tasks_with_usage": 3,
                    "source_tasks_provider": 2,
                    "source_tasks_estimated": 1,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 40,
                    "completion_tokens": 60,
                    "total_tokens": 100,
                    "cost_estimate": 0.5,
                    "avg_total_tokens": 25.0,
                    "avg_cost_estimate": 0.125,
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "id": "session-usage-1"
            }
            session_routes_module.get_session_usage_summary = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = session_routes_module.get_session_usage_summary_route(
                "session-usage-1",
                current_user={"id": "user-1"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.get_session_usage_summary = original_usage_helper  # type: ignore[assignment]

        self.assertEqual(payload.tasks_total, 4)
        self.assertEqual(payload.total_tokens, 100)
        self.assertEqual(payload.avg_cost_estimate, 0.125)

    def test_post_session_memory_add_accepts_model_dump_payload(self) -> None:
        original_get_session = session_routes_module.get_session
        original_add_helper = session_routes_module.add_session_memory_text

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "added_id": "memory-1",
                    "document_count": 3,
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "id": "session-1"
            }
            session_routes_module.add_session_memory_text = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = session_routes_module.post_session_memory_add(
                "session-1",
                payload=session_routes_module.MemoryAddRequest(
                    text="remember this",
                    metadata={"topic": "plans"},
                ),
                current_user={"id": "user-1"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.add_session_memory_text = original_add_helper  # type: ignore[assignment]

        self.assertEqual(payload.added_id, "memory-1")
        self.assertEqual(payload.document_count, 3)

    def test_post_session_memory_query_accepts_model_dump_payload(self) -> None:
        original_get_session = session_routes_module.get_session
        original_query_helper = session_routes_module.query_session_memory

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "ids": [["memory-1"]],
                    "documents": [["alpha"]],
                    "distances": [[0.12]],
                    "metadatas": [[{"task_id": "task-1"}]],
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "id": "session-1"
            }
            session_routes_module.query_session_memory = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = session_routes_module.post_session_memory_query(
                "session-1",
                payload=session_routes_module.MemoryQueryRequest(
                    text="find memory",
                    n_results=4,
                ),
                current_user={"id": "user-1"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.query_session_memory = original_query_helper  # type: ignore[assignment]

        self.assertEqual(payload.ids, [["memory-1"]])
        self.assertEqual(payload.documents, [["alpha"]])
        self.assertEqual(payload.metadatas, [[{"task_id": "task-1"}]])

    def test_create_task_entry_accepts_model_dump_response_summary(self) -> None:
        original_ensure_session = task_routes_module.ensure_session
        original_create_task = task_routes_module.create_task
        original_create_message = task_routes_module.create_message
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_create_summary_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_create_response_summary",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "task_id": "task-create-model-dump",
                    "session_id": "session-create-model-dump",
                    "status": "pending",
                    "status_normalized": "pending",
                    "status_label": "Pending",
                    "status_rank": 1,
                }

        try:
            task_routes_module.ensure_session = (
                lambda **_kwargs: "session-create-model-dump"
            )
            task_routes_module.create_task = lambda **_kwargs: "task-create-model-dump"
            task_routes_module.create_message = lambda **_kwargs: None
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.chat_persistence_service.get_task_create_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: ResponseReadyPayload()
            )
            payload = task_routes_module.create_task_entry(
                task_routes_module.TaskCreateRequest(
                    user_input="create model dump",
                    session_id=None,
                ),
                current_user={"id": "user-create-model-dump"},
            )
        finally:
            task_routes_module.ensure_session = original_ensure_session
            task_routes_module.create_task = original_create_task
            task_routes_module.create_message = original_create_message
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            if original_create_summary_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_create_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_create_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_create_response_summary = original_create_summary_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-create-model-dump")
        self.assertEqual(payload.session_id, "session-create-model-dump")
        self.assertEqual(payload.status, "pending")

    def test_cancel_task_accepts_model_dump_response_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_update_task_status = task_routes_module.update_task_status
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_cancel_summary_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_cancel_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "task_id": "task-cancel-model-dump",
                    "previous_status": "running",
                    "status": "cancelled",
                    "status_normalized": "cancelled",
                    "status_label": "Cancelled",
                    "status_rank": 4,
                    "already_terminal": False,
                }

        task_reads = [
            {
                "id": "task-cancel-model-dump",
                "session_id": "session-cancel-model-dump",
                "status": "running",
            },
            {
                "id": "task-cancel-model-dump",
                "session_id": "session-cancel-model-dump",
                "status": "cancelled",
            },
        ]
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: dict(  # type: ignore[assignment]
                task_reads.pop(0)
            )
            task_routes_module.update_task_status = lambda **_kwargs: None
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = task_routes_module.cancel_task(
                "task-cancel-model-dump",
                current_user={"id": "user-cancel-model-dump"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.update_task_status = original_update_task_status
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            if original_cancel_summary_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_cancel_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_cancel_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = original_cancel_summary_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-cancel-model-dump")
        self.assertEqual(payload.status, "cancelled")
        self.assertEqual(payload.previous_status, "running")
        self.assertFalse(payload.already_terminal)

    def test_get_tasks_usage_summary_route_accepts_model_dump_payload(self) -> None:
        original_usage_helper = task_routes_module.get_tasks_usage_summary

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "tasks_total": 3,
                    "tasks_with_usage": 2,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 1,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.25,
                    "avg_total_tokens": 25.0,
                    "avg_cost_estimate": 0.125,
                }

        try:
            task_routes_module.get_tasks_usage_summary = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = task_routes_module.get_tasks_usage_summary_route(
                session_id=None,
                current_user={"id": "user-usage-summary-model-dump"},
            )
        finally:
            task_routes_module.get_tasks_usage_summary = original_usage_helper  # type: ignore[assignment]

        self.assertEqual(payload.tasks_total, 3)
        self.assertEqual(payload.total_tokens, 50)
        self.assertEqual(payload.avg_cost_estimate, 0.125)

    def test_get_tasks_usage_dashboard_route_accepts_model_dump_response_summary(self) -> None:
        original_dashboard_loader = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 1,
                        "source_tasks_provider": 1,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost_estimate": 0.12,
                        "avg_total_tokens": 30.0,
                        "avg_cost_estimate": 0.12,
                    },
                    "trend": [],
                    "by_session": [],
                    "top_tasks": [],
                }

        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "ignored": True
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda _payload: ResponseReadyPayload()
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                current_user={"id": "user-usage-dashboard-model-dump"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_dashboard_loader
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.window_days, 14)
        self.assertEqual(payload.summary.tasks_total, 1)
        self.assertEqual(payload.summary.total_tokens, 30)

    def test_get_tasks_usage_dashboard_route_normalizes_model_dump_response_summary_governance_with_provider_source_context(
        self,
    ) -> None:
        original_dashboard_loader = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 1,
                        "source_tasks_provider": 1,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost_estimate": 0.12,
                        "avg_total_tokens": 30.0,
                        "avg_cost_estimate": 0.12,
                    },
                    "trend": [],
                    "by_session": [
                        {
                            "session_id": "session-usage-route-source",
                            "session_title": "Usage Route Source",
                            "tasks_with_usage": 1,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-07-02T10:00:00",
                            "governance": {
                                "profiles": ["calculator_only"],
                                "provider_sources": ["calculator_suite"],
                                "allowed_tool_names": ["calc_eval"],
                                "allowed_tool_labels": ["calc_eval"],
                            },
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-route-source",
                            "session_id": "session-usage-route-source",
                            "session_title": "Usage Route Source",
                            "prompt_excerpt": "usage route source",
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "created_at": "2026-07-02T10:00:00",
                            "updated_at": "2026-07-02T10:01:00",
                            "source_kind": "provider",
                            "governance": {
                                "profile": "calculator_only",
                                "provider_source": "calculator_suite",
                                "allowed_tool_names": ["calc_eval"],
                                "allowed_tool_labels": ["calc_eval"],
                            },
                        }
                    ],
                }

        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "ignored": True
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda _payload: ResponseReadyPayload()
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                current_user={"id": "user-usage-dashboard-source-model-dump"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_dashboard_loader
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_tasks_usage_dashboard_route_normalizes_dict_response_summary_with_model_dump_governance(
        self,
    ) -> None:
        original_dashboard_loader = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "ignored": True
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda _payload: {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 1,
                        "source_tasks_provider": 1,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost_estimate": 0.12,
                        "avg_total_tokens": 30.0,
                        "avg_cost_estimate": 0.12,
                    },
                    "trend": [],
                    "by_session": [
                        {
                            "session_id": "session-usage-route-mixed",
                            "session_title": "Usage Route Mixed",
                            "tasks_with_usage": 1,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-07-02T10:00:00",
                            "governance": session_governance,
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-route-mixed",
                            "session_id": "session-usage-route-mixed",
                            "session_title": "Usage Route Mixed",
                            "prompt_excerpt": "usage route mixed",
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "created_at": "2026-07-02T10:00:00",
                            "updated_at": "2026-07-02T10:01:00",
                            "source_kind": "provider",
                            "governance": task_governance,
                        }
                    ],
                }
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                current_user={"id": "user-usage-dashboard-mixed-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_dashboard_loader
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_task_detail_accepts_model_dump_response_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "id": "task-detail-model-dump",
                    "session_id": "session-detail-model-dump",
                    "prompt": "detail model dump",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T10:00:00",
                    "updated_at": "2026-07-02T10:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": None,
                }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-detail-model-dump"
            }
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: ResponseReadyPayload()
            )
            payload = task_routes_module.get_task_detail(
                "task-detail-model-dump",
                current_user={"id": "user-task-detail-model-dump"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.id, "task-detail-model-dump")
        self.assertEqual(payload.status, "completed")
        self.assertEqual(payload.prompt, "detail model dump")

    def test_get_task_detail_normalizes_model_dump_response_summary_governance_with_provider_source_context(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "id": "task-detail-source-model-dump",
                    "session_id": "session-detail-source-model-dump",
                    "prompt": "detail source model dump",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T10:00:00",
                    "updated_at": "2026-07-02T10:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": {
                        "profile": "calculator_only",
                        "provider_source": "calculator_suite",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-detail-source-model-dump"
            }
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: ResponseReadyPayload()
            )
            payload = task_routes_module.get_task_detail(
                "task-detail-source-model-dump",
                current_user={"id": "user-task-detail-source-model-dump"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_task_detail_normalizes_dict_response_summary_with_model_dump_governance(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyGovernance:
            def model_dump(self):
                return {
                    "profile": "calculator_only",
                    "provider_source": "calculator_suite",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["calc_eval"],
                }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-detail-mixed-governance"
            }
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "id": "task-detail-mixed-governance",
                    "session_id": "session-detail-mixed-governance",
                    "prompt": "detail mixed governance",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T10:00:00",
                    "updated_at": "2026-07-02T10:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": ResponseReadyGovernance(),
                }
            )
            payload = task_routes_module.get_task_detail(
                "task-detail-mixed-governance",
                current_user={"id": "user-task-detail-mixed-governance"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_tasks_accepts_model_dump_item_summaries(self) -> None:
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def __init__(self, task_id: str) -> None:
                self.task_id = task_id

            def model_dump(self):
                return {
                    "id": self.task_id,
                    "session_id": "session-list-model-dump",
                    "prompt": f"prompt::{self.task_id}",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T11:00:00",
                    "updated_at": "2026-07-02T11:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": None,
                }

        try:
            task_routes_module.list_tasks = lambda **_kwargs: [  # type: ignore[assignment]
                {"id": "task-list-model-dump-1"},
                {"id": "task-list-model-dump-2"},
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 2  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task: ResponseReadyPayload(str(task.get("id")))
            )
            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id=None,
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-task-list-model-dump"},
            )
        finally:
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual([item.id for item in payload.items], ["task-list-model-dump-1", "task-list-model-dump-2"])
        self.assertEqual(payload.total, 2)
        self.assertFalse(payload.has_more)

    def test_get_tasks_normalizes_model_dump_item_summary_governance_with_provider_source_context(
        self,
    ) -> None:
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "id": "task-list-source-model-dump",
                    "session_id": "session-list-source-model-dump",
                    "prompt": "prompt::task-list-source-model-dump",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T11:00:00",
                    "updated_at": "2026-07-02T11:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": {
                        "profile": "calculator_only",
                        "provider_source": "calculator_suite",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                }

        try:
            task_routes_module.list_tasks = lambda **_kwargs: [  # type: ignore[assignment]
                {"id": "task-list-source-model-dump"},
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: ResponseReadyPayload()
            )
            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id=None,
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-task-list-source-model-dump"},
            )
        finally:
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.items[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_tasks_normalizes_dict_item_summary_with_model_dump_governance(
        self,
    ) -> None:
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class ResponseReadyGovernance:
            def model_dump(self):
                return {
                    "profile": "calculator_only",
                    "provider_source": "calculator_suite",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["calc_eval"],
                }

        try:
            task_routes_module.list_tasks = lambda **_kwargs: [  # type: ignore[assignment]
                {"id": "task-list-mixed-governance"},
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "id": "task-list-mixed-governance",
                    "session_id": "session-list-mixed-governance",
                    "prompt": "prompt::task-list-mixed-governance",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T11:00:00",
                    "updated_at": "2026-07-02T11:01:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": ResponseReadyGovernance(),
                }
            )
            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id=None,
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-task-list-mixed-governance"},
            )
        finally:
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.items[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_get_task_trace_detail_accepts_model_dump_response_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_trace_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "steps": [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id="trace-model-dump-step",
                            type="thought",
                            content="trace model dump",
                            seq=1,
                        )
                    ],
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 2,
                }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-model-dump",
                "session_id": "session-trace-model-dump",
                "status": "completed",
                "trace_json": "trace-model-dump",
            }
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: ResponseReadyPayload()
            )
            payload = task_routes_module.get_task_trace_detail(
                "task-trace-model-dump",
                current_user={"id": "user-trace-model-dump"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_trace_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-trace-model-dump")
        self.assertEqual([step.id for step in payload.steps], ["trace-model-dump-step"])
        self.assertEqual(payload.status, "completed")

    def test_get_task_trace_detail_backfills_file_backed_real_search_result_summary(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        step = {
            "id": "step-file-backed-provider-search-trace",
            "seq": 12,
            "type": "action",
            "content": "Tool done: Provider Search access_token=hidden",
            "meta": {
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": [
                        "documents_total",
                        "knowledge_base_id",
                        "source",
                        "profile",
                    ],
                    "effective_result_output_keys": [
                        "documents_total",
                        "knowledge_base_id",
                        "request_id",
                        "source",
                        "profile",
                    ],
                    "output_preview": {
                        "documents_total": 2,
                        "knowledge_base_id": "provider-kb",
                        "source": "search_suite",
                        "profile": "retrieval_only",
                        "access_token": "secret-token",
                    },
                    "output": {
                        "documents_total": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-search-2",
                        "source": "search_suite",
                        "profile": "retrieval_only",
                        "access_token": "secret-token",
                    },
                }
            },
        }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-file-backed-search-trace",
                "session_id": "session-file-backed-search-trace",
                "status": "completed",
                "trace_json": json.dumps([step]),
            }
            payload = task_routes_module.get_task_trace_detail(
                "task-file-backed-search-trace",
                current_user={"id": "user-file-backed-search-trace"},
            )
        finally:
            task_routes_module.get_task = original_get_task

        self.assertEqual(payload.task_id, "task-file-backed-search-trace")
        self.assertEqual(payload.status, "completed")
        self.assertEqual(len(payload.steps), 1)
        trace_step = payload.steps[0]
        self.assertIn(
            "Retrieved 2 documents from provider-kb (request id req-search-2).",
            trace_step.content,
        )
        self.assertIsNotNone(trace_step.meta)
        assert trace_step.meta is not None
        self.assertIsInstance(trace_step.meta.tool, dict)
        tool_meta = trace_step.meta.tool
        assert tool_meta is not None
        self.assertEqual(
            tool_meta["result_summary"],
            "Retrieved 2 documents from provider-kb (request id req-search-2).",
        )
        self.assertEqual(
            tool_meta["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )
        self.assertEqual(
            tool_meta["output"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-search-2",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )
        serialized = json.dumps(trace_step.model_dump(exclude_none=True))
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_task_trace_delta_detail_accepts_model_dump_response_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_delta_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_response_summary_from_task",
            None,
        )

        class ResponseReadyPayload:
            def model_dump(self):
                return {
                    "steps": [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id="trace-delta-model-dump-step",
                            type="thought",
                            content="trace delta model dump",
                            seq=3,
                        )
                    ],
                    "next_cursor": 3,
                    "has_more": False,
                    "lag_seq": 1,
                    "dropped": False,
                }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-delta-model-dump",
                "session_id": "session-trace-delta-model-dump",
                "status": "completed",
                "trace_json": "trace-delta-model-dump",
            }
            task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: ResponseReadyPayload()
            )
            payload = task_routes_module.get_task_trace_delta_detail(
                "task-trace-delta-model-dump",
                after_seq=2,
                limit=40,
                current_user={"id": "user-trace-delta-model-dump"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_delta_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = original_delta_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-trace-delta-model-dump")
        self.assertEqual([step.id for step in payload.steps], ["trace-delta-model-dump-step"])
        self.assertEqual(payload.next_cursor, 3)
        self.assertFalse(payload.has_more)

    def test_get_task_trace_delta_detail_backfills_file_backed_real_calc_result_summary(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        step = {
            "id": "step-file-backed-provider-math-delta",
            "seq": 28,
            "type": "action",
            "content": "Tool done: Provider Calculator token=hidden",
            "meta": {
                "tool": {
                    "name": "provider_math",
                    "label": "Provider Calculator",
                    "kind": "provider_calc",
                    "semantic_kind": "provider_math",
                    "semantic_family": "local_calculator",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": [
                        "expression",
                        "result",
                        "source",
                        "profile",
                    ],
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
                        "api_key": "secret-token",
                    },
                    "output": {
                        "expression": "8/4",
                        "result": 2,
                        "request_id": "req-calc-1",
                        "source": "calculator_suite",
                        "profile": "calculator_only",
                        "api_key": "secret-token",
                    },
                }
            },
        }

        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-file-backed-calc-delta",
                "session_id": "session-file-backed-calc-delta",
                "status": "completed",
                "trace_json": json.dumps([step]),
            }
            payload = task_routes_module.get_task_trace_delta_detail(
                "task-file-backed-calc-delta",
                after_seq=0,
                limit=40,
                current_user={"id": "user-file-backed-calc-delta"},
            )
        finally:
            task_routes_module.get_task = original_get_task

        self.assertEqual(payload.task_id, "task-file-backed-calc-delta")
        self.assertEqual(payload.next_cursor, 28)
        self.assertFalse(payload.has_more)
        self.assertEqual(len(payload.steps), 1)
        delta_step = payload.steps[0]
        self.assertIn("Calculated 8/4 = 2 (request id req-calc-1).", delta_step.content)
        self.assertIsNotNone(delta_step.meta)
        assert delta_step.meta is not None
        self.assertIsInstance(delta_step.meta.tool, dict)
        tool_meta = delta_step.meta.tool
        assert tool_meta is not None
        self.assertEqual(
            tool_meta["result_summary"],
            "Calculated 8/4 = 2 (request id req-calc-1).",
        )
        self.assertEqual(
            tool_meta["output"],
            {
                "expression": "8/4",
                "result": 2,
                "request_id": "req-calc-1",
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )
        serialized = json.dumps(delta_step.model_dump(exclude_none=True))
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_register_accepts_model_dump_user_and_issued_payload(self) -> None:
        original_create_user = auth_routes_module.create_user
        original_issue_auth_tokens = auth_routes_module.issue_auth_tokens
        original_safe_audit = auth_routes_module._safe_record_audit_event

        class UserPayload:
            def model_dump(self):
                return {
                    "id": "user-auth-model-dump",
                    "email": "typed@example.com",
                    "display_name": "Typed User",
                    "role": "user",
                    "created_at": "2026-07-02T12:00:00",
                    "updated_at": "2026-07-02T12:00:00",
                }

        class IssuedPayload:
            def model_dump(self):
                return {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "session_id": "session-auth-model-dump",
                    "user": UserPayload(),
                }

        try:
            auth_routes_module.create_user = lambda **_kwargs: UserPayload()  # type: ignore[assignment]
            auth_routes_module.issue_auth_tokens = lambda **_kwargs: IssuedPayload()  # type: ignore[assignment]
            auth_routes_module._safe_record_audit_event = lambda **_kwargs: None  # type: ignore[assignment]
            request = SimpleNamespace(client=None, headers={})
            payload = auth_routes_module.register(
                auth_routes_module.RegisterRequest(
                    email="typed@example.com",
                    password="password123",
                    display_name="Typed User",
                ),
                request=request,
            )
        finally:
            auth_routes_module.create_user = original_create_user  # type: ignore[assignment]
            auth_routes_module.issue_auth_tokens = original_issue_auth_tokens  # type: ignore[assignment]
            auth_routes_module._safe_record_audit_event = original_safe_audit  # type: ignore[assignment]

        self.assertEqual(payload.session_id, "session-auth-model-dump")
        self.assertEqual(payload.user.id, "user-auth-model-dump")
        self.assertEqual(payload.user.email, "typed@example.com")

    def test_refresh_accepts_model_dump_issued_payload(self) -> None:
        original_refresh_auth_tokens = auth_routes_module.refresh_auth_tokens
        original_safe_audit = auth_routes_module._safe_record_audit_event

        class UserPayload:
            def model_dump(self):
                return {
                    "id": "user-refresh-model-dump",
                    "email": "refresh@example.com",
                    "display_name": "Refresh User",
                    "role": "user",
                    "created_at": "2026-07-02T12:10:00",
                    "updated_at": "2026-07-02T12:10:00",
                }

        class IssuedPayload:
            def model_dump(self):
                return {
                    "access_token": "refresh-access-token",
                    "refresh_token": "refresh-refresh-token",
                    "session_id": "session-refresh-model-dump",
                    "user": UserPayload(),
                }

        try:
            auth_routes_module.refresh_auth_tokens = (  # type: ignore[assignment]
                lambda **_kwargs: IssuedPayload()
            )
            auth_routes_module._safe_record_audit_event = lambda **_kwargs: None  # type: ignore[assignment]
            request = SimpleNamespace(client=None, headers={})
            payload = auth_routes_module.refresh(
                auth_routes_module.RefreshRequest(
                    refresh_token="x" * 32,
                ),
                request=request,
            )
        finally:
            auth_routes_module.refresh_auth_tokens = original_refresh_auth_tokens  # type: ignore[assignment]
            auth_routes_module._safe_record_audit_event = original_safe_audit  # type: ignore[assignment]

        self.assertEqual(payload.session_id, "session-refresh-model-dump")
        self.assertEqual(payload.user.id, "user-refresh-model-dump")

    def test_get_auth_sessions_accepts_model_dump_rows(self) -> None:
        original_list_auth_sessions = auth_routes_module.list_auth_sessions

        class SessionRowPayload:
            def __init__(self, session_id: str) -> None:
                self.session_id = session_id

            def model_dump(self):
                return {
                    "id": self.session_id,
                    "active": True,
                    "created_at": "2026-07-02T12:20:00",
                    "updated_at": "2026-07-02T12:20:00",
                    "expires_at": "2026-07-03T12:20:00",
                    "last_used_at": None,
                    "revoked_at": None,
                    "user_agent": None,
                    "ip_address": None,
                }

        try:
            auth_routes_module.list_auth_sessions = lambda **_kwargs: [  # type: ignore[assignment]
                SessionRowPayload("session-auth-row-1"),
                SessionRowPayload("session-auth-row-2"),
            ]
            payload = auth_routes_module.get_auth_sessions(
                current_user={"id": "user-auth-list"},
            )
        finally:
            auth_routes_module.list_auth_sessions = original_list_auth_sessions  # type: ignore[assignment]

        self.assertEqual([item.id for item in payload.items], ["session-auth-row-1", "session-auth-row-2"])

    def test_get_users_accepts_model_dump_rows(self) -> None:
        original_list_users = auth_routes_module.list_users

        class UserRowPayload:
            def __init__(self, user_id: str, email: str) -> None:
                self.user_id = user_id
                self.email = email

            def model_dump(self):
                return {
                    "id": self.user_id,
                    "email": self.email,
                    "display_name": None,
                    "role": "user",
                    "created_at": "2026-07-02T12:30:00",
                    "updated_at": "2026-07-02T12:30:00",
                }

        try:
            auth_routes_module.list_users = lambda **_kwargs: (  # type: ignore[assignment]
                [
                    UserRowPayload("user-row-1", "user1@example.com"),
                    UserRowPayload("user-row-2", "user2@example.com"),
                ],
                2,
            )
            payload = auth_routes_module.get_users(
                limit=20,
                offset=0,
                _current_admin={"id": "admin-1"},
            )
        finally:
            auth_routes_module.list_users = original_list_users  # type: ignore[assignment]

        self.assertEqual([item.id for item in payload.items], ["user-row-1", "user-row-2"])
        self.assertEqual(payload.total, 2)
        self.assertFalse(payload.has_more)

    def test_get_audit_logs_accepts_model_dump_rows(self) -> None:
        original_list_audit_logs = audit_routes_module.list_audit_logs
        original_count_audit_logs = audit_routes_module.count_audit_logs

        class AuditRowPayload:
            def __init__(self, row_id: str, task_id: str) -> None:
                self.row_id = row_id
                self.task_id = task_id

            def model_dump(self):
                return {
                    "id": self.row_id,
                    "event_type": "task_cancel",
                    "event_detail_json": json.dumps(
                        {
                            "session_id": "session-audit-model-dump",
                            "task_id": self.task_id,
                        }
                    ),
                    "created_at": "2026-07-02T12:40:00",
                }

        try:
            audit_routes_module.list_audit_logs = lambda **_kwargs: [  # type: ignore[assignment]
                AuditRowPayload("audit-row-1", "task-audit-1"),
                AuditRowPayload("audit-row-2", "task-audit-2"),
            ]
            audit_routes_module.count_audit_logs = lambda **_kwargs: 2  # type: ignore[assignment]
            payload = audit_routes_module.get_audit_logs(
                limit=20,
                offset=0,
                event_type=None,
                session_id=None,
                task_id=None,
                start_at=None,
                end_at=None,
                current_user={"id": "user-audit-model-dump"},
            )
        finally:
            audit_routes_module.list_audit_logs = original_list_audit_logs  # type: ignore[assignment]
            audit_routes_module.count_audit_logs = original_count_audit_logs  # type: ignore[assignment]

        self.assertEqual([item.id for item in payload.items], ["audit-row-1", "audit-row-2"])
        self.assertEqual(payload.items[0].task_id, "task-audit-1")
        self.assertEqual(payload.total, 2)
        self.assertFalse(payload.has_more)

    def test_record_audit_event_redacts_http_json_event_detail_before_insert(self) -> None:
        original_get_db_connection = audit_service_module.get_db_connection
        execute_calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeConnection:
            def execute(self, sql: str, params: tuple[object, ...]):
                execute_calls.append((sql, params))

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        raw_detail: dict[str, object] = {
            "session_id": "session-audit-insert",
            "task_id": "task-audit-insert",
            "diagnostic": (
                "GET failed response_path=$.data.access_token "
                "callback https://provider.example/cb?access_token=secret-token"
                "#client_secret=hidden Bearer secret-token"
            ),
            "raw_body": {
                "access_token": "secret-token",
                "request_id": "Bearer secret-token",
            },
        }

        try:
            audit_service_module.get_db_connection = lambda: FakeContextManager()  # type: ignore[assignment]
            audit_service_module.record_audit_event(
                user_id="user-audit-insert",
                event_type="task_failed",
                detail=raw_detail,
            )
        finally:
            audit_service_module.get_db_connection = original_get_db_connection  # type: ignore[assignment]

        self.assertEqual(len(execute_calls), 1)
        detail_json = execute_calls[0][1][3]
        self.assertIsInstance(detail_json, str)
        inserted_detail = json.loads(str(detail_json))
        self.assertEqual(inserted_detail["session_id"], "session-audit-insert")
        self.assertEqual(inserted_detail["task_id"], "task-audit-insert")
        self.assertIn("response_path=$.data.[redacted]", str(detail_json))
        self.assertNotIn("response_path=$.data.access_token", str(detail_json))
        self.assertNotIn("access_token", str(detail_json))
        self.assertNotIn("client_secret", str(detail_json))
        self.assertNotIn("Bearer", str(detail_json))
        self.assertNotIn("secret-token", str(detail_json))

    def test_get_audit_logs_redacts_http_json_event_detail_diagnostics(self) -> None:
        original_list_audit_logs = audit_routes_module.list_audit_logs
        original_count_audit_logs = audit_routes_module.count_audit_logs
        raw_detail = {
            "session_id": "session-audit-redact",
            "task_id": "task-audit-redact",
            "provider": "http_json",
            "diagnostic": (
                "GET failed response_path=$.data.access_token "
                "callback https://provider.example/cb?access_token=secret-token"
                "#client_secret=hidden Bearer secret-token"
            ),
            "nested": {
                "message": (
                    "upstream query_params.access_token "
                    "json_body.client_secret Bearer secret-token"
                ),
                "raw_body": {
                    "access_token": "secret-token",
                    "request_id": "Bearer secret-token",
                },
            },
        }

        try:
            audit_routes_module.list_audit_logs = lambda **_kwargs: [  # type: ignore[assignment]
                {
                    "id": "audit-redact-1",
                    "event_type": "task_failed",
                    "event_detail_json": json.dumps(raw_detail),
                    "created_at": "2026-07-02T12:45:00",
                }
            ]
            audit_routes_module.count_audit_logs = lambda **_kwargs: 1  # type: ignore[assignment]
            payload = audit_routes_module.get_audit_logs(
                limit=20,
                offset=0,
                event_type=None,
                session_id=None,
                task_id=None,
                start_at=None,
                end_at=None,
                current_user={"id": "user-audit-redact"},
            )
        finally:
            audit_routes_module.list_audit_logs = original_list_audit_logs  # type: ignore[assignment]
            audit_routes_module.count_audit_logs = original_count_audit_logs  # type: ignore[assignment]

        self.assertEqual(payload.items[0].session_id, "session-audit-redact")
        self.assertEqual(payload.items[0].task_id, "task-audit-redact")
        serialized = json.dumps(
            payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
            ensure_ascii=False,
        )
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertIn("provider", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("json_body.client_secret", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_post_session_accepts_model_dump_row(self) -> None:
        original_create_session_record = session_routes_module.create_session_record

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-create-model-dump",
                    "title": "Created Session",
                    "created_at": "2026-07-02T13:00:00",
                    "updated_at": "2026-07-02T13:00:00",
                }

        try:
            session_routes_module.create_session_record = (  # type: ignore[assignment]
                lambda **_kwargs: SessionRowPayload()
            )
            payload = session_routes_module.post_session(
                payload=session_routes_module.CreateSessionRequest(title="Created Session"),
                current_user={"id": "user-session-create"},
            )
        finally:
            session_routes_module.create_session_record = original_create_session_record  # type: ignore[assignment]

        self.assertEqual(payload.id, "session-create-model-dump")
        self.assertEqual(payload.title, "Created Session")

    def test_get_sessions_accepts_model_dump_rows(self) -> None:
        original_list_sessions = session_routes_module.list_sessions
        original_count_sessions = session_routes_module.count_sessions

        class SessionRowPayload:
            def __init__(self, session_id: str) -> None:
                self.session_id = session_id

            def model_dump(self):
                return {
                    "id": self.session_id,
                    "title": f"title::{self.session_id}",
                    "created_at": "2026-07-02T13:10:00",
                    "updated_at": "2026-07-02T13:10:00",
                }

        try:
            session_routes_module.list_sessions = lambda **_kwargs: [  # type: ignore[assignment]
                SessionRowPayload("session-list-1"),
                SessionRowPayload("session-list-2"),
            ]
            session_routes_module.count_sessions = lambda **_kwargs: 2  # type: ignore[assignment]
            payload = session_routes_module.get_sessions(
                limit=20,
                offset=0,
                current_user={"id": "user-session-list"},
            )
        finally:
            session_routes_module.list_sessions = original_list_sessions  # type: ignore[assignment]
            session_routes_module.count_sessions = original_count_sessions  # type: ignore[assignment]

        self.assertEqual([item.id for item in payload.items], ["session-list-1", "session-list-2"])
        self.assertEqual(payload.total, 2)
        self.assertFalse(payload.has_more)

    def test_patch_session_accepts_model_dump_row(self) -> None:
        original_update_session_title = session_routes_module.update_session_title

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-patch-model-dump",
                    "title": "Patched Session",
                    "created_at": "2026-07-02T13:20:00",
                    "updated_at": "2026-07-02T13:21:00",
                }

        try:
            session_routes_module.update_session_title = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: SessionRowPayload()
            )
            payload = session_routes_module.patch_session(
                "session-patch-model-dump",
                payload=session_routes_module.UpdateSessionRequest(title="Patched Session"),
                current_user={"id": "user-session-patch"},
            )
        finally:
            session_routes_module.update_session_title = original_update_session_title  # type: ignore[assignment]

        self.assertEqual(payload.id, "session-patch-model-dump")
        self.assertEqual(payload.title, "Patched Session")

    def test_get_session_detail_accepts_model_dump_row(self) -> None:
        original_get_session = session_routes_module.get_session

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-detail-model-dump",
                    "title": "Detail Session",
                    "created_at": "2026-07-02T13:30:00",
                    "updated_at": "2026-07-02T13:30:00",
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: SessionRowPayload()  # type: ignore[assignment]
            payload = session_routes_module.get_session_detail(
                "session-detail-model-dump",
                current_user={"id": "user-session-detail"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]

        self.assertEqual(payload.id, "session-detail-model-dump")
        self.assertEqual(payload.title, "Detail Session")

    def test_get_session_messages_detail_accepts_model_dump_rows(self) -> None:
        original_get_session = session_routes_module.get_session
        original_get_session_messages = session_routes_module.get_session_messages

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-messages-model-dump",
                    "title": "Messages Session",
                    "created_at": "2026-07-02T13:40:00",
                    "updated_at": "2026-07-02T13:40:00",
                }

        class MessageRowPayload:
            def __init__(self, message_id: str, role: str) -> None:
                self.message_id = message_id
                self.role = role

            def model_dump(self):
                return {
                    "id": self.message_id,
                    "session_id": "session-messages-model-dump",
                    "task_id": None,
                    "role": self.role,
                    "content": f"content::{self.message_id}",
                    "created_at": "2026-07-02T13:41:00",
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: SessionRowPayload()  # type: ignore[assignment]
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: [  # type: ignore[assignment]
                MessageRowPayload("message-1", "user"),
                MessageRowPayload("message-2", "assistant"),
            ]
            payload = session_routes_module.get_session_messages_detail(
                "session-messages-model-dump",
                current_user={"id": "user-session-messages"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]

        self.assertEqual(payload.session.id, "session-messages-model-dump")
        self.assertEqual([item.id for item in payload.messages], ["message-1", "message-2"])

    def test_get_session_messages_detail_redacts_http_json_message_content(self) -> None:
        original_get_session = session_routes_module.get_session
        original_get_session_messages = session_routes_module.get_session_messages

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "id": "session-messages-redact",
                "title": "Messages Redact",
                "created_at": "2026-07-02T13:42:00",
                "updated_at": "2026-07-02T13:42:00",
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: [  # type: ignore[assignment]
                {
                    "id": "message-redact-1",
                    "session_id": "session-messages-redact",
                    "task_id": "task-message-redact",
                    "role": "assistant",
                    "content": (
                        "Upstream failed response_path=$.data.access_token "
                        "callback https://provider.example/cb?access_token=secret-token"
                        "#client_secret=hidden Bearer secret-token"
                    ),
                    "created_at": "2026-07-02T13:43:00",
                }
            ]
            payload = session_routes_module.get_session_messages_detail(
                "session-messages-redact",
                current_user={"id": "user-session-messages-redact"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]

        serialized = json.dumps(
            payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
            ensure_ascii=False,
        )
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertEqual(payload.messages[0].id, "message-redact-1")

    def test_build_session_export_payload_accepts_model_dump_session_row(self) -> None:
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-export-model-dump",
                    "title": "Export Session",
                    "created_at": "2026-07-02T14:00:00",
                    "updated_at": "2026-07-02T14:00:00",
                }

        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 0,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "governance": None,
                    "stats": {
                        "task_count": 0,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "messages": [],
                    "tasks": [],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                SessionRowPayload(),
                "user-session-export-model-dump",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]
            session_routes_module.get_session_tasks = original_get_session_tasks  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.session.id, "session-export-model-dump")
        self.assertEqual(payload.stats.task_count, 0)

    def test_build_session_export_payload_accepts_model_dump_export_summary(
        self,
    ) -> None:
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )

        class ExportSummaryPayload:
            def model_dump(self):
                return {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["suite_a"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 2,
                        "rag_hit_count": 1,
                    },
                    "messages": [],
                    "tasks": [
                        {
                            "id": "task-session-export-model",
                            "prompt": "session export payload model",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-07-03T10:20:00",
                            "updated_at": "2026-07-03T10:21:00",
                            "usage": None,
                            "trace_step_count": 2,
                            "rag_hit_count": 1,
                            "trace_preview": [],
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "suite_a",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                }

        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: ExportSummaryPayload()
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-summary-model",
                    "title": "Session Export Summary Model",
                    "created_at": "2026-07-03T10:20:00",
                    "updated_at": "2026-07-03T10:21:00",
                },
                "user-session-export-summary-model",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]
            session_routes_module.get_session_tasks = original_get_session_tasks  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.stats.trace_step_count, 2)
        self.assertEqual(payload.tasks[0].id, "task-session-export-model")
        self.assertEqual(payload.governance.profiles, ["planning_only"])

    def test_build_session_export_payload_normalizes_model_dump_export_summary_governance_with_provider_source_context(
        self,
    ) -> None:
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )

        class ExportSummaryPayload:
            def model_dump(self):
                return {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "governance": {
                        "profiles": ["calculator_only"],
                        "provider_sources": ["calculator_suite"],
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 2,
                        "rag_hit_count": 1,
                    },
                    "messages": [],
                    "tasks": [
                        {
                            "id": "task-session-export-source-model",
                            "prompt": "session export source model",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-07-03T10:20:00",
                            "updated_at": "2026-07-03T10:21:00",
                            "usage": None,
                            "trace_step_count": 2,
                            "rag_hit_count": 1,
                            "trace_preview": [],
                            "governance": {
                                "profile": "calculator_only",
                                "provider_source": "calculator_suite",
                                "allowed_tool_names": ["calc_eval"],
                                "allowed_tool_labels": ["calc_eval"],
                            },
                        }
                    ],
                }

        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: ExportSummaryPayload()
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-source-summary-model",
                    "title": "Session Export Source Summary Model",
                    "created_at": "2026-07-03T10:20:00",
                    "updated_at": "2026-07-03T10:21:00",
                },
                "user-session-export-source-summary-model",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]
            session_routes_module.get_session_tasks = original_get_session_tasks  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Calculator Suite"],
        )
        self.assertEqual(
            payload.tasks[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_build_session_export_payload_normalizes_dict_export_summary_with_model_dump_governance(
        self,
    ) -> None:
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )

        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "governance": session_governance,
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 2,
                        "rag_hit_count": 1,
                    },
                    "messages": [],
                    "tasks": [
                        {
                            "id": "task-session-export-mixed-governance",
                            "prompt": "session export mixed governance",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-07-03T10:20:00",
                            "updated_at": "2026-07-03T10:21:00",
                            "usage": None,
                            "trace_step_count": 2,
                            "rag_hit_count": 1,
                            "trace_preview": [],
                            "governance": task_governance,
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-mixed-governance",
                    "title": "Session Export Mixed Governance",
                    "created_at": "2026-07-03T10:20:00",
                    "updated_at": "2026-07-03T10:21:00",
                },
                "user-session-export-mixed-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]
            session_routes_module.get_session_tasks = original_get_session_tasks  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Calculator Suite"],
        )
        self.assertEqual(
            payload.tasks[0].governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_build_session_export_payload_normalizes_dict_export_summary_with_model_dump_nested_rows(
        self,
    ) -> None:
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )

        class ResponseReadyMessage:
            def model_dump(self):
                return {
                    "id": "message-session-export-mixed-row",
                    "task_id": "task-session-export-mixed-row",
                    "role": "assistant",
                    "content": "mixed nested message",
                    "created_at": "2026-07-03T10:22:00",
                }

        class ResponseReadyPreviewStep:
            def model_dump(self):
                return {
                    "id": "step-session-export-mixed-row",
                    "seq": 7,
                    "type": "observation",
                    "title": "Tool observation",
                    "content_excerpt": "mixed nested trace preview",
                }

        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {  # type: ignore[assignment]
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "governance": None,
                    "stats": {
                        "task_count": 1,
                        "message_count": 1,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "messages": [ResponseReadyMessage()],
                    "tasks": [
                        {
                            "id": "task-session-export-mixed-row",
                            "prompt": "session export mixed row",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-07-03T10:20:00",
                            "updated_at": "2026-07-03T10:21:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [ResponseReadyPreviewStep()],
                            "governance": None,
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-mixed-row",
                    "title": "Session Export Mixed Row",
                    "created_at": "2026-07-03T10:20:00",
                    "updated_at": "2026-07-03T10:21:00",
                },
                "user-session-export-mixed-row",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary  # type: ignore[assignment]
            session_routes_module.get_session_messages = original_get_session_messages  # type: ignore[assignment]
            session_routes_module.get_session_tasks = original_get_session_tasks  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.messages[0].id, "message-session-export-mixed-row")
        self.assertEqual(
            payload.tasks[0].trace_preview[0].content_excerpt,
            "mixed nested trace preview",
        )

    def test_export_session_json_accepts_model_dump_session_row_for_filename_and_payload(self) -> None:
        original_get_session = session_routes_module.get_session
        original_build_payload = getattr(
            session_routes_module,
            "_build_session_export_payload",
            None,
        )

        class SessionRowPayload:
            def model_dump(self):
                return {
                    "id": "session-export-route-model-dump",
                    "title": "Route Export Session",
                    "created_at": "2026-07-02T14:10:00",
                    "updated_at": "2026-07-02T14:10:00",
                }

        try:
            session_routes_module.get_session = lambda *_args, **_kwargs: SessionRowPayload()  # type: ignore[assignment]
            session_routes_module._build_session_export_payload = (  # type: ignore[attr-defined]
                lambda session, _user_id: session_routes_module.SessionExportJsonResponse(
                    version="1.0",
                    exported_at="2026-07-02T14:10:01",
                    session=session_routes_module.SessionResponse(**session),
                    usage_summary=session_routes_module.SessionUsageSummaryResponse(
                        tasks_total=0,
                        tasks_with_usage=0,
                        source_tasks_provider=0,
                        source_tasks_estimated=0,
                        source_tasks_mixed=0,
                        source_tasks_legacy=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        cost_estimate=0.0,
                        avg_total_tokens=None,
                        avg_cost_estimate=None,
                    ),
                    governance=None,
                    stats=session_routes_module.SessionExportStats(
                        task_count=0,
                        message_count=0,
                        trace_step_count=0,
                        rag_hit_count=0,
                    ),
                    messages=[],
                    tasks=[],
                )
            )
            response = SimpleNamespace(headers={})
            payload = session_routes_module.export_session_json(
                "session-export-route-model-dump",
                response=response,
                download=True,
                current_user={"id": "user-session-export-route"},
            )
        finally:
            session_routes_module.get_session = original_get_session  # type: ignore[assignment]
            if original_build_payload is not None:
                session_routes_module._build_session_export_payload = original_build_payload  # type: ignore[attr-defined]

        self.assertEqual(payload.session.id, "session-export-route-model-dump")
        self.assertIn("session-export-route-model-dump", response.headers["Content-Disposition"])

    def test_build_task_export_payload_accepts_model_dump_task_row(self) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-export-model-dump",
                    "session_id": "session-export-model-dump",
                    "prompt": "export model dump",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T14:20:00",
                    "updated_at": "2026-07-02T14:20:00",
                }

        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: {
                    "task": {
                        "id": "task-export-model-dump",
                        "session_id": "session-export-model-dump",
                        "prompt": "export model dump",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-02T14:20:00",
                        "updated_at": "2026-07-02T14:20:00",
                        "governance": None,
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                TaskRowPayload(),
                "user-task-export-model-dump",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task.id, "task-export-model-dump")
        self.assertEqual(payload.trace.step_count, 0)

    def test_build_task_export_payload_backfills_file_backed_real_calc_trace_result_summary(
        self,
    ) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        step = {
            "id": "step-file-backed-provider-math-export",
            "seq": 8,
            "type": "action",
            "content": "Tool done: Provider Calculator token=hidden",
            "meta": {
                "tool": {
                    "name": "provider_math",
                    "label": "Provider Calculator",
                    "kind": "provider_calc",
                    "semantic_kind": "provider_math",
                    "semantic_family": "local_calculator",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": [
                        "expression",
                        "result",
                        "source",
                        "profile",
                    ],
                    "effective_result_output_keys": [
                        "expression",
                        "result",
                        "request_id",
                        "source",
                        "profile",
                    ],
                    "output": {
                        "expression": "8/4",
                        "result": 2,
                        "request_id": "req-calc-1",
                        "source": "calculator_suite",
                        "profile": "calculator_only",
                        "client_secret": "secret-token",
                    },
                }
            },
        }

        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "task-file-backed-calc-export",
                    "session_id": "session-file-backed-calc-export",
                    "prompt": "calculate 8/4",
                    "status": "completed",
                    "created_at": "2026-07-03T11:00:00",
                    "updated_at": "2026-07-03T11:01:00",
                    "trace_json": json.dumps([step]),
                },
                "user-file-backed-calc-export",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages  # type: ignore[assignment]

        self.assertEqual(payload.task.id, "task-file-backed-calc-export")
        self.assertEqual(payload.trace.step_count, 1)
        export_step = payload.trace.steps[0]
        self.assertIn("Calculated 8/4 = 2 (request id req-calc-1).", export_step.content)
        self.assertIsNotNone(export_step.meta)
        assert export_step.meta is not None
        self.assertIsInstance(export_step.meta.tool, dict)
        tool_meta = export_step.meta.tool
        assert tool_meta is not None
        self.assertEqual(
            tool_meta["result_summary"],
            "Calculated 8/4 = 2 (request id req-calc-1).",
        )
        self.assertEqual(
            tool_meta["output"],
            {
                "expression": "8/4",
                "result": 2,
                "request_id": "req-calc-1",
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )
        serialized = json.dumps(export_step.model_dump(exclude_none=True))
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_task_export_payload_accepts_model_dump_export_summary(
        self,
    ) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )

        class ExportSummaryPayload:
            def model_dump(self):
                return {
                    "task": {
                        "id": "task-export-summary-model",
                        "session_id": "session-export-summary-model",
                        "prompt": "task export summary model",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-03T10:30:00",
                        "updated_at": "2026-07-03T10:31:00",
                    },
                    "usage": {"prompt_tokens": 5},
                    "messages": [],
                    "trace": {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_a",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                        "step_count": 2,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-1"],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }

        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: ExportSummaryPayload()
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "task-export-summary-model",
                    "session_id": "session-export-summary-model",
                    "prompt": "task export summary model",
                    "status": "completed",
                    "created_at": "2026-07-03T10:30:00",
                    "updated_at": "2026-07-03T10:31:00",
                },
                "user-task-export-summary-model",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task.id, "task-export-summary-model")
        self.assertEqual(payload.trace.step_count, 2)
        self.assertEqual(payload.trace.governance.profile, "planning_only")

    def test_build_task_export_payload_normalizes_model_dump_export_summary_governance_with_provider_source_context(
        self,
    ) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )

        class ExportSummaryPayload:
            def model_dump(self):
                return {
                    "task": {
                        "id": "task-export-source-summary-model",
                        "session_id": "session-export-source-summary-model",
                        "prompt": "task export source summary model",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-03T10:30:00",
                        "updated_at": "2026-07-03T10:31:00",
                    },
                    "usage": {"prompt_tokens": 5},
                    "messages": [],
                    "trace": {
                        "governance": {
                            "profile": "calculator_only",
                            "provider_source": "calculator_suite",
                            "allowed_tool_names": ["calc_eval"],
                            "allowed_tool_labels": ["calc_eval"],
                        },
                        "step_count": 2,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-1"],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }

        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: ExportSummaryPayload()
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "task-export-source-summary-model",
                    "session_id": "session-export-source-summary-model",
                    "prompt": "task export source summary model",
                    "status": "completed",
                    "created_at": "2026-07-03T10:30:00",
                    "updated_at": "2026-07-03T10:31:00",
                },
                "user-task-export-source-summary-model",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload.trace.governance.allowed_tool_labels,
            ["Calculator Suite"],
        )

    def test_build_task_export_payload_normalizes_dict_export_summary_with_model_dump_nested_rows(
        self,
    ) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )

        class ResponseReadyMessage:
            def model_dump(self):
                return {
                    "id": "message-task-export-mixed-row",
                    "role": "assistant",
                    "content": "mixed nested task message",
                    "created_at": "2026-07-03T10:32:00",
                }

        class ResponseReadyRagChunk:
            def model_dump(self):
                return {
                    "step_id": "step-task-export-mixed-row",
                    "knowledge_base_id": "kb-mixed-row",
                    "content": "mixed nested rag chunk",
                }

        class ResponseReadyTraceStep:
            def model_dump(self):
                return {
                    "id": "step-task-export-mixed-row",
                    "type": "observation",
                    "content": "mixed nested trace step",
                    "seq": 3,
                }

        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: {
                    "task": {
                        "id": "task-export-mixed-row",
                        "session_id": "session-export-mixed-row",
                        "prompt": "task export mixed row",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-03T10:30:00",
                        "updated_at": "2026-07-03T10:31:00",
                    },
                    "usage": {"prompt_tokens": 5},
                    "messages": [ResponseReadyMessage()],
                    "trace": {
                        "governance": None,
                        "step_count": 1,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-mixed-row"],
                        "rag_chunks": [ResponseReadyRagChunk()],
                        "steps": [ResponseReadyTraceStep()],
                    },
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "task-export-mixed-row",
                    "session_id": "session-export-mixed-row",
                    "prompt": "task export mixed row",
                    "status": "completed",
                    "created_at": "2026-07-03T10:30:00",
                    "updated_at": "2026-07-03T10:31:00",
                },
                "user-task-export-mixed-row",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.messages[0].id, "message-task-export-mixed-row")
        self.assertEqual(payload.trace.rag_chunks[0].content, "mixed nested rag chunk")
        self.assertEqual(payload.trace.steps[0].id, "step-task-export-mixed-row")

    def test_export_task_json_accepts_model_dump_task_row_for_filename_and_payload(self) -> None:
        original_get_task = task_routes_module.get_task
        original_build_payload = getattr(task_routes_module, "_build_task_export_payload", None)

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-export-route-model-dump",
                    "session_id": "session-export-route-model-dump",
                    "prompt": "export route model dump",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T14:30:00",
                    "updated_at": "2026-07-02T14:30:00",
                }

        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: TaskRowPayload()  # type: ignore[assignment]
            task_routes_module._build_task_export_payload = (  # type: ignore[attr-defined]
                lambda task, _user_id: task_routes_module.TaskExportJsonResponse(
                    version="1.0",
                    exported_at="2026-07-02T14:30:01",
                    task=task_routes_module.TaskExportTask(
                        id=task["id"],
                        session_id=task["session_id"],
                        prompt=task["prompt"],
                        status=task["status"],
                        status_normalized=task["status_normalized"],
                        status_label=task["status_label"],
                        status_rank=task["status_rank"],
                        created_at=task["created_at"],
                        updated_at=task["updated_at"],
                        governance=None,
                    ),
                    usage=None,
                    messages=[],
                    trace=task_routes_module.TaskExportTrace(
                        governance=None,
                        step_count=0,
                        rag_hit_count=0,
                        rag_knowledge_base_ids=[],
                        rag_chunks=[],
                        steps=[],
                    ),
                )
            )
            response = SimpleNamespace(headers={})
            payload = task_routes_module.export_task_json(
                "task-export-route-model-dump",
                response=response,
                download=True,
                current_user={"id": "user-task-export-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            if original_build_payload is not None:
                task_routes_module._build_task_export_payload = original_build_payload  # type: ignore[attr-defined]

        self.assertEqual(payload.task.id, "task-export-route-model-dump")
        self.assertIn("task-export-route-model-dump", response.headers["Content-Disposition"])

    def test_get_task_detail_accepts_model_dump_task_row_input(self) -> None:
        original_get_task = task_routes_module.get_task
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-detail-row-model-dump",
                    "session_id": "session-detail-row-model-dump",
                    "prompt": "detail row model dump",
                    "status": "completed",
                }

        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: TaskRowPayload()  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task: {
                    "id": str(task["id"]),
                    "session_id": str(task["session_id"]),
                    "prompt": str(task["prompt"]),
                    "status": str(task["status"]),
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                    "created_at": "2026-07-02T15:00:00",
                    "updated_at": "2026-07-02T15:00:00",
                    "usage": None,
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": None,
                }
            )
            payload = task_routes_module.get_task_detail(
                "task-detail-row-model-dump",
                current_user={"id": "user-task-detail-row"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.id, "task-detail-row-model-dump")
        self.assertEqual(payload.prompt, "detail row model dump")

    def test_get_task_trace_detail_accepts_model_dump_task_row_input(self) -> None:
        original_get_task = task_routes_module.get_task
        original_trace_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_response_summary_from_task",
            None,
        )

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-trace-row-model-dump",
                    "status": "completed",
                }

        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: TaskRowPayload()  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task: {
                    "steps": [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id=f"trace::{task['id']}",
                            type="thought",
                            content="trace row model dump",
                            seq=1,
                        )
                    ],
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                }
            )
            payload = task_routes_module.get_task_trace_detail(
                "task-trace-row-model-dump",
                current_user={"id": "user-task-trace-row"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            if original_trace_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-trace-row-model-dump")
        self.assertEqual([step.id for step in payload.steps], ["trace::task-trace-row-model-dump"])

    def test_get_task_trace_delta_detail_accepts_model_dump_task_row_input(self) -> None:
        original_get_task = task_routes_module.get_task
        original_delta_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_response_summary_from_task",
            None,
        )

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-trace-delta-row-model-dump",
                    "status": "completed",
                }

        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: TaskRowPayload()  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, **_kwargs: {
                    "steps": [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id=f"delta::{task['id']}",
                            type="thought",
                            content="delta row model dump",
                            seq=2,
                        )
                    ],
                    "next_cursor": 2,
                    "has_more": False,
                    "lag_seq": 0,
                    "dropped": False,
                }
            )
            payload = task_routes_module.get_task_trace_delta_detail(
                "task-trace-delta-row-model-dump",
                after_seq=0,
                limit=40,
                current_user={"id": "user-task-trace-delta-row"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            if original_delta_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = original_delta_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-trace-delta-row-model-dump")
        self.assertEqual([step.id for step in payload.steps], ["delta::task-trace-delta-row-model-dump"])

    def test_cancel_task_accepts_model_dump_task_row_input(self) -> None:
        original_get_task = task_routes_module.get_task
        original_update_task_status = task_routes_module.update_task_status
        original_safe_record_audit_event = task_routes_module.safe_record_audit_event
        original_cancel_summary_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_cancel_response_summary_from_task",
            None,
        )

        class TaskRowPayload:
            def __init__(self, status: str) -> None:
                self.status = status

            def model_dump(self):
                return {
                    "id": "task-cancel-row-model-dump",
                    "session_id": "session-cancel-row-model-dump",
                    "status": self.status,
                }

        task_reads = [TaskRowPayload("running"), TaskRowPayload("cancelled")]
        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: task_reads.pop(0)  # type: ignore[assignment]
            task_routes_module.update_task_status = lambda **_kwargs: None
            task_routes_module.safe_record_audit_event = lambda **_kwargs: None
            task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda task, previous_status, already_terminal: {
                    "task_id": str(task["id"]),
                    "previous_status": previous_status,
                    "status": str(task["status"]),
                    "status_normalized": "cancelled",
                    "status_label": "Cancelled",
                    "status_rank": 4,
                    "already_terminal": already_terminal,
                }
            )
            payload = task_routes_module.cancel_task(
                "task-cancel-row-model-dump",
                current_user={"id": "user-task-cancel-row"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            task_routes_module.update_task_status = original_update_task_status
            task_routes_module.safe_record_audit_event = original_safe_record_audit_event
            if original_cancel_summary_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_cancel_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_cancel_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_cancel_response_summary_from_task = original_cancel_summary_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.task_id, "task-cancel-row-model-dump")
        self.assertEqual(payload.status, "cancelled")

    def test_stream_running_task_reconnect_accepts_model_dump_task_rows(self) -> None:
        original_get_task = task_routes_module.get_task
        original_get_goal_settings = task_routes_module.get_settings
        original_delta_snapshot_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        original_usage_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_usage_from_task",
            None,
        )

        class TaskRowPayload:
            def __init__(self, status: str) -> None:
                self.status = status

            def model_dump(self):
                return {
                    "id": "task-stream-row-model-dump",
                    "session_id": "session-stream-row-model-dump",
                    "status": self.status,
                }

        task_reads = [TaskRowPayload("running"), TaskRowPayload("completed")]

        async def collect() -> list[str]:
            events: list[str] = []
            async for event in task_routes_module.stream_running_task_reconnect(
                "task-stream-row-model-dump",
                user_id="user-task-stream-row",
                after_seq=0,
            ):
                events.append(event)
                if len(events) >= 2:
                    break
            return events

        try:
            task_routes_module.get_settings = lambda: SimpleNamespace(  # type: ignore[assignment]
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.1,
                stream_reconnect_heartbeat_interval_sec=60.0,
            )
            task_routes_module.get_task = lambda *_args, **_kwargs: task_reads.pop(0)  # type: ignore[assignment]
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda task, **_kwargs: ([], 0, False, 0, f"latest::{task['id']}")
            )
            task_routes_module.chat_persistence_service.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda task: {"task_id": task["id"]}
            )
            events = asyncio.run(collect())
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            task_routes_module.get_settings = original_get_goal_settings  # type: ignore[assignment]
            if original_delta_snapshot_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_helper  # type: ignore[attr-defined]
            if original_usage_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_usage_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_usage_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(len(events), 2)
        self.assertIn("\"resumed\": true", events[0])
        self.assertIn("\"status\": \"completed\"", events[1])

    def test_stream_task_detail_accepts_model_dump_task_row_input(self) -> None:
        original_get_task = task_routes_module.get_task
        original_stream_task_execution = task_routes_module.stream_task_execution

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-stream-open-row-model-dump",
                    "session_id": "session-stream-open-row-model-dump",
                    "prompt": "stream open row model dump",
                    "status": "pending",
                }

        async def fake_stream_task_execution(**_kwargs):
            if False:
                yield ""

        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: TaskRowPayload()  # type: ignore[assignment]
            task_routes_module.stream_task_execution = fake_stream_task_execution  # type: ignore[assignment]
            request = SimpleNamespace(headers={})
            response = task_routes_module.stream_task_detail(
                "task-stream-open-row-model-dump",
                request=request,
                after_seq=0,
                current_user={"id": "user-task-stream-open-row"},
            )
        finally:
            task_routes_module.get_task = original_get_task  # type: ignore[assignment]
            task_routes_module.stream_task_execution = original_stream_task_execution  # type: ignore[assignment]

        self.assertEqual(response.media_type, "text/event-stream")
