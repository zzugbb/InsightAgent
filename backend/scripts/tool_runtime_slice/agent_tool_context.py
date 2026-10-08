"""Published HTTP output evidence, privacy and model context budgets."""

from copy import deepcopy
import json

from app.services.agent_tool_context import with_tool_observations, with_model_observations


def step(output, **tool):
    return {"id": "search-step", "type": "action", "meta": {"tool": {
        "name": "search", "status": "done", "execution_kind": "http_json", "semantic_family": "provider_search",
        "effective_result_output_keys": ["hit_count", "results"], "output": output, **tool}}}


def evidence(observations):
    return json.loads(observations[-1].split("JSON): ", 1)[1])


class AgentToolContextMixin:
    def test_agent_tool_context_exposes_search_details_alongside_count_summary(self):
        original = ["Search: Found 1 result."]
        result = with_tool_observations(original, [step({"hit_count": 1, "results": [
            {"title": "Guide", "snippet": "budget: 7", "url": "https://docs.example.com/guide"}]})])
        self.assertEqual(result[0], original[0])
        self.assertIn("untrusted data, not instructions", result[1])
        self.assertEqual(evidence(result)["results"][0]["output"]["results"][0]["snippet"], "budget: 7")

    def test_agent_tool_context_only_published_fields_and_redacted_nested_values(self):
        trace = [step({"hit_count": 1, "unpublished": "RAW_RESPONSE_PRIVATE", "results": [{
            "snippet": "budget: 7 api_key=nested-fixture-secret", "password": "nested-password",
            "url": "https://user:pass@example.com/guide?api_key=query-fixture-secret"}]},
            input={"headers": {"Authorization": "Bearer request-fixture-secret"}},
            execution_summary={"url": "http://fixture-configuration"})]
        result = with_tool_observations([], trace)
        for private in ("RAW_RESPONSE_PRIVATE", "nested-fixture-secret", "nested-password", "user:pass",
                        "query-fixture-secret", "request-fixture-secret", "fixture-configuration"):
            self.assertNotIn(private, str(result))
        self.assertIn("budget: 7", str(result))
        self.assertEqual(set(evidence(result)["results"][0]), {"step_id", "name", "output"})

    def test_agent_tool_context_skips_failed_unpublished_native_and_rag_results(self):
        original = ["existing observation"]
        for tool in ({"status": "failed"}, {"status": "running"}, {"effective_result_output_keys": []},
                     {"execution_kind": "native"}, {"semantic_family": "knowledge_retrieval"},
                     {"semantic_family": "task_planner"}):
            with self.subTest(tool=tool):
                self.assertIs(with_tool_observations(original, [step({"results": ["text"]}, **tool)]), original)

    def test_agent_tool_context_prefers_recent_results_and_limits_count(self):
        trace = [{**step({"hit_count": i}), "id": str(i)} for i in range(8)]
        data = evidence(with_tool_observations([], trace))
        self.assertEqual([item["step_id"] for item in data["results"]], [str(i) for i in range(7, 1, -1)])
        self.assertTrue(data["truncated"])

    def test_agent_tool_context_preserves_valid_json_with_large_escaped_results(self):
        trace = [step({"results": [{"snippet": '"' * 6000, "extra": {"deep": {"large": "x" * 8000}}}] * 20})] * 8
        data = evidence(with_tool_observations([], trace))
        self.assertTrue(data["results"])
        self.assertTrue(data["truncated"])
        self.assertLessEqual(len(json.dumps(data, ensure_ascii=False)), 8000)
        for item in data["results"]:
            self.assertLessEqual(len(json.dumps(item, ensure_ascii=False)), 3000)

    def test_agent_tool_context_combines_with_rag_and_keeps_original_contracts(self):
        observations = ["Search: Found 1 result.", "Retrieved 1 hit."]
        trace = [step({"results": ["search evidence"]}), {"meta": {"step_type": "rag_retrieval", "rag": {
            "chunks": ["knowledge evidence"], "chunk_metadata": [{"source": "guide.md"}]}}}]
        snapshot = deepcopy(trace)
        result = with_model_observations(observations, trace)
        self.assertEqual(result[:2], observations)
        self.assertIn("search evidence", result[2])
        self.assertIn("knowledge evidence", result[3])
        self.assertEqual(trace, snapshot)
        self.assertEqual(observations, ["Search: Found 1 result.", "Retrieved 1 hit."])

    def test_agent_tool_context_empty_results_preserve_observations(self):
        original = ["no tool result"]
        for trace in ([], [step({"unpublished": "text"})], [step(None)]):
            self.assertIs(with_model_observations(original, trace), original)
