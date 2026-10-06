from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from app.api.routes.rag_ingest import RagIngestJobRequest
from app.config import Settings
from app.services import chroma_rag_service as rag
from app.services.rag_chunking import iter_text_chunks


class RagIngestBatchesMixin:
    def _rag_batch_fixture(self, **kwargs):
        client = MagicMock()
        client.get_max_batch_size.return_value = 2
        collection = client.get_or_create_collection.return_value
        collection.count.return_value = 5
        options = {"user_id": "fixture", "knowledge_base_id": "default", "chunk_size": 120,
                   "chunk_overlap": 0, "documents": [
                       {"text": "A" * 360, "document_id": "a", "metadata": {"chapter": "one"}},
                       {"text": "B" * 240, "document_id": "b"}], **kwargs}
        return client, collection, options

    def test_rag_ingest_batch_lazy_chunking_keeps_boundaries(self):
        for text, size, overlap, expected in [
            ("  ", 3, 0, []), ("abcdefg", 3, 1, ["abc", "cde", "efg"]),
            ("abc", 3, 2, ["abc"]), ("ab     cd", 3, 0, ["ab", "cd"]),
        ]:
            self.assertEqual(list(iter_text_chunks(text, chunk_size=size, chunk_overlap=overlap)), expected)

    def test_rag_ingest_batch_request_rejects_overlap_expansion(self):
        with self.assertRaises(ValidationError) as raised:
            RagIngestJobRequest(documents=[{"text": "a" * 6000}], chunk_size=120, chunk_overlap=119)
        self.assertIn("5000 chunks", str(raised.exception))

    def test_rag_ingest_batch_request_budget_is_aggregate_and_exact(self):
        request = RagIngestJobRequest(documents=[{"text": "a" * 2619}] * 2,
                                      chunk_size=120, chunk_overlap=119)
        self.assertEqual(len(request.documents), 2)  # 2500 chunks per document, total 5000.
        with self.assertRaises(ValidationError):
            RagIngestJobRequest(documents=[{"text": "a" * 2620}] * 2,
                                chunk_size=120, chunk_overlap=119)

    def test_rag_ingest_batch_legacy_ingest_keeps_single_add(self):
        client, collection, options = self._rag_batch_fixture()
        with patch.object(rag, "_http_client", return_value=client):
            result = rag.ingest_knowledge_documents(**options)
        collection.add.assert_called_once()
        client.get_max_batch_size.assert_not_called()
        self.assertEqual(result["chunks_added"], 5)

    def test_rag_ingest_batch_negotiates_server_limit_and_counts_confirmed_documents(self):
        client, collection, options = self._rag_batch_fixture()
        progress = []
        with patch.object(rag, "_http_client", return_value=client):
            result = rag.ingest_knowledge_documents(**options, chunk_batch_size=128, on_progress=progress.append)
        self.assertEqual([len(call.kwargs["ids"]) for call in collection.add.call_args_list], [2, 2, 1])
        self.assertEqual(progress, [
            {"documents_processed": 0, "chunks_written": 0, "chunk_total": 5},
            {"documents_processed": 0, "chunks_written": 2, "chunk_total": 5},
            {"documents_processed": 1, "chunks_written": 4, "chunk_total": 5},
            {"documents_processed": 2, "chunks_written": 5, "chunk_total": 5},
        ])
        self.assertEqual(result["documents_ingested"], 2)

    def test_rag_ingest_batch_preserves_metadata_and_unique_ids_across_batches(self):
        client, collection, options = self._rag_batch_fixture()
        with patch.object(rag, "_http_client", return_value=client):
            rag.ingest_knowledge_documents(**options, chunk_batch_size=2)
        ids = [item for call in collection.add.call_args_list for item in call.kwargs["ids"]]
        metadata = [item for call in collection.add.call_args_list for item in call.kwargs["metadatas"]]
        self.assertEqual(len(set(ids)), 5)
        self.assertEqual([item["chunk_index"] for item in metadata], [1, 2, 3, 1, 2])
        self.assertEqual([item["chunk_total"] for item in metadata], [3, 3, 3, 2, 2])
        self.assertEqual(len({item["document_version"] for item in metadata[:3]}), 1)
        self.assertEqual(metadata[2]["chapter"], "one")

    def test_rag_ingest_batch_failure_does_not_advance_unconfirmed_progress(self):
        client, collection, options = self._rag_batch_fixture()
        collection.add.side_effect = [None, RuntimeError("upstream private content")]
        progress = []
        with patch.object(rag, "_http_client", return_value=client), self.assertRaises(RuntimeError):
            rag.ingest_knowledge_documents(**options, chunk_batch_size=2, on_progress=progress.append)
        self.assertEqual(progress[-1]["chunks_written"], 2)
        self.assertEqual(collection.add.call_count, 2)

    def test_rag_ingest_batch_budget_stops_before_chroma_side_effects(self):
        client, _, options = self._rag_batch_fixture()
        with patch.object(rag, "_http_client", return_value=client) as connect, self.assertRaises(ValueError):
            rag.ingest_knowledge_documents(**options, chunk_batch_size=2, max_chunks=4)
        connect.assert_not_called()

    def test_rag_ingest_batch_permission_gate_runs_before_each_write(self):
        client, collection, options = self._rag_batch_fixture()
        gate = MagicMock(side_effect=[None, PermissionError()])
        with patch.object(rag, "_http_client", return_value=client), self.assertRaises(PermissionError):
            rag.ingest_knowledge_documents(**options, chunk_batch_size=2, before_batch=gate)
        collection.add.assert_called_once()

    def test_rag_ingest_batch_progress_persistence_failure_stops_further_writes(self):
        client, collection, options = self._rag_batch_fixture()
        progress = MagicMock(side_effect=[None, RuntimeError("database failure")])
        with patch.object(rag, "_http_client", return_value=client), self.assertRaises(RuntimeError):
            rag.ingest_knowledge_documents(**options, chunk_batch_size=2, on_progress=progress)
        collection.add.assert_called_once()

    def test_rag_ingest_batch_configuration_is_bounded(self):
        self.assertEqual(Settings(_env_file=None).rag_ingest_batch_size, 128)
        for value in [0, 513]:
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, RAG_INGEST_BATCH_SIZE=value)
