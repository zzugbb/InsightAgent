#!/usr/bin/env python3
"""Core conversation/RAG/conditional flows: real PostgreSQL/Chroma with a local provider."""

import json
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, calc
from app.providers.base import ProviderResponse, ProviderUsage
from app.providers.mock_provider import MockLLMProvider
from app.services import chat_persistence_service as persistence, tool_runtime as runtime
from app.services.conversation_context import load_conversation_context
from app.services import chroma_rag_service as rag_service


class ContextProvider(MockLLMProvider):
    def __init__(self, mode="conversation"):
        super().__init__(provider="offline-core-fixture")
        self.mode, self.planning_prompts, self.final_prompts = mode, [], []

    def generate(self, prompt):
        self.planning_prompts.append(prompt)
        tools = []
        if self.mode == "invalid":
            return ProviderResponse("invalid plan", self.model, self.provider)
        if self.mode == "rag":
            if "Completed tool observations (JSON):\n" not in prompt:
                tools = [{"name": "task_retrieve", "input": {"query": "budget", "knowledge_base_id": "manuals"}}]
            else:
                observations = json.loads(prompt.split("Completed tool observations (JSON):\n", 1)[1])
                if not any('"result"' in text for text in observations):
                    tools = [calc("7*2" if "budget: 7" in " ".join(observations) else "5*2")]
        return ProviderResponse(json.dumps({"tools": tools}), self.model, self.provider, ProviderUsage(10, 2, 12))

    def stream_generate(self, prompt):
        self.final_prompts.append(prompt)
        yield "blue telescope" if "blue telescope" in prompt else "fixture answer"


class AgentCoreScenariosPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    client = AgentFeedbackPostgresTests.client
    steps = AgentFeedbackPostgresTests.steps
    task = AgentFeedbackPostgresTests.task

    def create(self, client, prompt, session=None):
        response = client.post("/api/tasks", json={"session_id": session or self.session, "user_input": prompt})
        self.assertEqual(response.status_code, 200)
        return response.json()["task_id"]

    def execute(self, client, task):
        response = client.get(f"/api/tasks/{task}/stream")
        self.assertIn("event: done", response.text)
        return self.steps(client, task)

    def test_follow_up_context_reaches_planning_and_answer_without_rewriting_messages(self):
        provider = ContextProvider()
        with self.client(provider) as client:
            first = self.create(client, "Our project is the blue telescope.")
            self.execute(client, first)
            second = self.create(client, "What is our project?")
            steps = self.execute(client, second)
            self.assertIn("blue telescope", provider.planning_prompts[-1])
            self.assertIn("blue telescope", provider.final_prompts[-1])
            self.assertEqual(steps[-1]["content"], "blue telescope")
            self.assertEqual(steps[0]["meta"]["conversation_context"]["turn_count"], 1)
            self.assertEqual(persistence.get_task(second, "owner")["prompt"], "What is our project?")
            messages = persistence.get_task_messages(second, "owner")
            self.assertEqual(messages[0]["content"], "What is our project?")
            serialized = json.dumps(steps)
            self.assertNotIn("Our project is the blue telescope.", serialized)
            delta = client.get(f"/api/tasks/{second}/trace/delta?after_seq=0&limit=100").json()["steps"]
            exported = client.get(f"/api/tasks/{second}/export/json").json()["trace"]["steps"]
            self.assertEqual(delta, steps)
            self.assertEqual(exported, steps)

    def test_history_scope_requires_owned_task_and_session(self):
        provider = ContextProvider()
        with self.client(provider) as client:
            first = self.create(client, "blue telescope")
            self.execute(client, first)
            second = self.create(client, "follow up")
            context = load_conversation_context(task_id=second, session_id=self.session, user_id="owner")
            self.assertEqual(context.summary["turn_count"], 1)
            other_session = persistence.ensure_session("another", "owner")
            for session, owner in [(self.session, "other"), (other_session, "owner")]:
                self.assertEqual(load_conversation_context(task_id=second, session_id=session, user_id=owner).messages, [])
            fresh = self.create(client, "new session", other_session)
            self.assertEqual(load_conversation_context(task_id=fresh, session_id=other_session, user_id="owner").messages, [])

    def test_queued_turn_excludes_preceding_answer_finished_after_its_creation(self):
        provider = ContextProvider()
        with self.client(provider) as client:
            first = self.create(client, "blue telescope")
            queued = self.create(client, "already queued")
            self.execute(client, first)
            self.execute(client, queued)
            self.assertNotIn("Prior conversation (JSON", provider.final_prompts[-1])
            next_task = self.create(client, "now both are complete")
            self.assertEqual(load_conversation_context(task_id=next_task, session_id=self.session, user_id="owner").summary["turn_count"], 2)

    def test_failed_and_incomplete_turns_are_not_conversation_pairs(self):
        provider = ContextProvider()
        with self.client(provider) as client:
            for status in ("failed", "cancelled", "running", "completed"):
                task = persistence.create_task(self.session, "exclude", "owner", status=status)
                persistence.create_message(self.session, "owner", "user", "exclude", task)
                if status != "completed":
                    persistence.create_message(self.session, "owner", "assistant", "incomplete answer", task)
            current = self.create(client, "current")
            self.assertEqual(load_conversation_context(task_id=current, session_id=self.session, user_id="owner").messages, [])

    def test_invalid_planning_does_not_replay_a_historical_calculation(self):
        provider = ContextProvider("invalid")
        with self.client(provider) as client:
            prior = self.create(client, "blue telescope [calc:2+3]")
            self.execute(client, prior)
            current = self.create(client, "Summarize our prior conversation")
            steps = self.execute(client, current)
            self.assertIn("[calc:2+3]", provider.planning_prompts[-1])
            self.assertFalse(any((step["meta"].get("tool") or {}).get("name") == "calc_eval" for step in steps))
            self.assertIn("blue telescope", provider.final_prompts[-1])

    def test_rag_provenance_and_both_observation_driven_branches_survive_exports(self):
        for budget, expression in ((7, "7*2"), (5, "5*2")):
            with self.subTest(budget=budget):
                provider = ContextProvider("rag")
                hit = {"id": "chunk-1", "content": f"budget: {budget}", "distance": 0.1,
                       "metadata": {"source": "guide.md", "document_id": "guide.md",
                                    "document_version": "sha256:" + "a" * 32, "content_hash": "a" * 64}}
                with self.client(provider) as client, patch.object(runtime, "query_knowledge_base", return_value={
                    "hits": [hit], "hit_count": 1, "knowledge_base_id": "manuals", "collection": "kb_fixture_manuals",
                }) as query:
                    task = self.create(client, "Retrieve budget and double it", persistence.ensure_session("rag scenario", "owner"))
                    steps = self.execute(client, task)
                    self.assertEqual(query.call_args.kwargs["user_id"], "owner")
                    self.assertEqual(query.call_args.kwargs["knowledge_base_id"], "manuals")
                    actions = [(step["meta"].get("tool") or {}) for step in steps if step["type"] == "action"]
                    self.assertEqual([tool["input"]["expression"] for tool in actions if tool.get("name") == "calc_eval"], [expression])
                    rag = next(step["meta"]["rag"] for step in steps if step["meta"].get("step_type") == "rag_retrieval")
                    self.assertEqual(rag["chunk_metadata"][0], hit["metadata"])
                    self.assertIn("guide.md", provider.final_prompts[-1])
                    self.assertIn(hit["metadata"]["document_version"], provider.final_prompts[-1])
                    exported = client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"]
                    self.assertEqual(exported, steps)
                    self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
                    self.assertIn("guide.md", client.get(f"/api/tasks/{task}/export/markdown").text)

    def test_database_selection_preserves_only_six_recent_completed_pairs(self):
        provider = ContextProvider()
        with self.client(provider) as client:
            for i in range(8):
                prior = persistence.create_task(self.session, f"turn {i}", "owner", status="success")
                persistence.create_message(self.session, "owner", "user", f"turn {i}", prior)
                persistence.create_message(self.session, "owner", "assistant", f"answer {i}", prior)
                persistence.create_message(self.session, "other", "assistant", "foreign content", prior)
            current = self.create(client, "follow up")
            context = load_conversation_context(task_id=current, session_id=self.session, user_id="owner")
            self.assertEqual(context.summary["turn_count"], 6)
            self.assertTrue(context.truncated)
            self.assertEqual([message["content"] for message in context.messages[::2]], [f"turn {i}" for i in range(2, 8)])
            self.assertNotIn("foreign content", context.serialized)

    def test_canonical_mock_keeps_its_existing_demo_and_does_not_load_history(self):
        with self.client(MockLLMProvider()) as client, patch("app.services.chat_execution_service.load_conversation_context") as history:
            task = self.create(client, "plain request")
            self.execute(client, task)
            history.assert_not_called()

    def test_real_chroma_retrieval_drives_next_action_and_final_source_evidence(self):
        rag_service.ingest_knowledge_documents(user_id="owner", knowledge_base_id="manuals",
            documents=[{"text": "budget: 7", "source": "guide.md", "document_id": "guide.md"}], chunk_size=500, chunk_overlap=80)
        provider = ContextProvider("rag")
        with self.client(provider) as client, patch.object(runtime, "query_knowledge_base", wraps=rag_service.query_knowledge_base):
            task = self.create(client, "Retrieve budget and double it")
            steps = self.execute(client, task)
            actions = [step["meta"]["tool"] for step in steps if step["type"] == "action"]
            self.assertEqual([tool["input"]["expression"] for tool in actions if tool["name"] == "calc_eval"], ["7*2"])
            evidence = next(step["meta"]["rag"] for step in steps if step["meta"].get("step_type") == "rag_retrieval")
            metadata = evidence["chunk_metadata"][0]
            self.assertEqual(metadata["source"], "guide.md")
            self.assertRegex(metadata["document_version"], r"^sha256:[a-f0-9]{16}$")
            self.assertIn(metadata["document_version"], provider.final_prompts[-1])
            self.assertIn("budget: 7", provider.final_prompts[-1])
            self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
        rag_service._http_client().delete_collection(rag_service.rag_collection_name("owner", "manuals"))


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(AgentCoreScenariosPostgresTests, with_chroma=True))
