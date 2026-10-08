"""Check Agent core through the candidate's real HTTP provider and public task APIs."""

import json
import re
from uuid import uuid4

from pilot_model_fixture import FIXTURE_KEY
from pilot_task_smoke import require


def check_agent_contracts(base, token, *, fixture_base, request_json, request_text, read_stream, wait_until):
    def api(path, payload=None, **kwargs):
        return request_json(base + path, payload=payload, token=token, **kwargs)

    def settings(model):
        updated = api("/api/settings", {"mode": "remote", "provider": "pilot-protocol-fixture",
            "model": model, "base_url": "http://model-fixture:8080/v1", "api_key": FIXTURE_KEY}, method="PUT")
        require(updated.get("mode") == "remote", "pilot_agent_remote_settings_failed")

    def run(prompt, *, model, session=None, completed=True, planning_tokens=12):
        settings(model)
        payload = {"user_input": prompt}
        if session:
            payload["session_id"] = session
        created = api("/api/tasks", payload)
        task_id = created["task_id"]
        events = read_stream(base + f"/api/tasks/{task_id}/stream", token)
        require(any(event == "done" for event, _ in events) == completed, "pilot_agent_terminal_event_failed")
        require(any(event == "error" for event, _ in events) != completed, "pilot_agent_error_event_failed")
        task = api(f"/api/tasks/{task_id}")
        require(task.get("status_normalized") == ("completed" if completed else "failed"), "pilot_agent_terminal_status_failed")
        steps = api(f"/api/tasks/{task_id}/trace")["steps"]
        require(bool(steps), "pilot_agent_trace_missing")
        ids, seqs = [step["id"] for step in steps], [step["seq"] for step in steps]
        require(len(ids) == len(set(ids)) and seqs == sorted(set(seqs)), "pilot_agent_trace_cursor_failed")
        delta = api(f"/api/tasks/{task_id}/trace/delta?after_seq=0&limit=100")["steps"]
        exported = api(f"/api/tasks/{task_id}/export/json")
        require(delta == steps == exported["trace"]["steps"], "pilot_agent_trace_export_failed")
        require(exported.get("version") == "1.0", "pilot_agent_export_version_failed")
        roles = [message["role"] for message in exported["messages"]]
        require(roles == (["user", "assistant"] if completed else ["user"]), "pilot_agent_messages_failed")
        require(exported["messages"][0]["content"] == prompt, "pilot_agent_prompt_rewritten")
        require(bool(request_text(base + f"/api/tasks/{task_id}/export/markdown", token)), "pilot_agent_markdown_missing")
        usage = json.loads(task["usage_json"])
        require(usage.get("planning_total_tokens") == planning_tokens, "pilot_agent_planning_usage_failed")
        require(usage.get("overall_total_tokens") == planning_tokens + (7 if completed else 0), "pilot_agent_overall_usage_failed")
        if completed:
            require(usage.get("total_tokens") == 7, "pilot_agent_final_usage_failed")
        else:
            require("completion_tokens" not in usage, "pilot_agent_failed_answer_usage_invented")
        return created, steps, exported, events

    seed, _, exported, _ = run("Record mission code: blue telescope.", model="pilot-seed")
    require(exported["messages"][-1]["content"] == "blue telescope", "pilot_agent_seed_answer_failed")
    versions = []
    for index, budget in enumerate((7, 5), 1):
        kb = f"pilot-budget-{budget}"
        job = api("/api/rag/ingest-jobs", {"idempotency_key": str(uuid4()), "knowledge_base_id": kb,
            "documents": [{"text": f"budget: {budget}", "source": "guide.md", "document_id": "guide.md"}]})

        def imported():
            current = api(f"/api/rag/ingest-jobs/{job['id']}")
            require(current.get("status") not in {"failed", "cancelled"}, "pilot_agent_ingest_failed")
            return current if current.get("status") == "completed" else None

        require(wait_until("agent knowledge import", imported, timeout=45) is not None, "pilot_agent_ingest_incomplete")
        _, steps, exported, _ = run("Use the earlier mission code. Retrieve the budget and double it.",
            model=kb, session=seed["session_id"], planning_tokens=36)
        require(steps[0]["meta"]["conversation_context"]["turn_count"] == index, "pilot_agent_history_count_failed")
        tools = [step["meta"]["tool"] for step in steps if step["type"] == "action"]
        business = [tool for tool in tools if tool["name"] != "task_plan"]
        require([tool["name"] for tool in business] == ["task_retrieve", "calc_eval"], "pilot_agent_feedback_tools_failed")
        require(business[0]["output_preview"].get("hit_count") == 1, "pilot_agent_retrieval_count_failed")
        require(business[1]["input"].get("expression") == f"{budget}*2" and
                business[1]["output_preview"].get("result") == budget * 2, "pilot_agent_conditional_result_failed")
        decisions = [step["meta"]["agent_decision"] for step in steps if "agent_decision" in step["meta"]]
        require(decisions == ["continue", "no_tools"], "pilot_agent_decision_order_failed")
        evidence = next(step["meta"]["rag"] for step in steps if step["meta"].get("step_type") == "rag_retrieval")
        metadata = evidence["chunk_metadata"][0]
        require(evidence["chunks"] == [f"budget: {budget}"] and metadata.get("source") == "guide.md", "pilot_agent_rag_body_failed")
        version = metadata.get("document_version", "")
        require(re.fullmatch(r"sha256:[a-f0-9]{16}", version) is not None, "pilot_agent_rag_version_failed")
        require(exported["messages"][-1]["content"] == f"blue telescope: {budget * 2}; guide.md {version}", "pilot_agent_answer_evidence_failed")
        require(steps[-1]["meta"].get("agent_stop_reason") == "no_tools", "pilot_agent_stop_reason_failed")
        versions.append(version)
    require(len(set(versions)) == 2, "pilot_agent_document_versions_failed")
    _, steps, exported, _ = run("Do you have any prior mission?", model="pilot-isolated")
    require(steps[0]["meta"]["conversation_context"]["turn_count"] == 0 and
            exported["messages"][-1]["content"] == "no prior mission", "pilot_agent_session_isolation_failed")
    run("Summarize the fixture.", model="pilot-empty-initial")
    for model, tokens, code in (("pilot-empty-feedback", 24, "remote_provider_empty_response"),
                                ("pilot-rate-feedback", 12, "remote_provider_rate_limited")):
        _, steps, _, events = run("Use one tool then decide.", model=model, completed=False, planning_tokens=tokens)
        require(sum((step["meta"].get("tool") or {}).get("name") == "calc_eval" for step in steps) == 1, "pilot_agent_failed_tools_replayed")
        require(any(event == "error" and data.get("code") == code for event, data in events), "pilot_agent_provider_error_lost")
    stats = request_json(fixture_base + "/health")
    expected = {model: {"planning": planning, "answer": answer} for model, planning, answer in (
        ("pilot-seed", 1, 1), ("pilot-budget-7", 3, 1), ("pilot-budget-5", 3, 1), ("pilot-isolated", 1, 1),
        ("pilot-empty-initial", 1, 1), ("pilot-empty-feedback", 2, 0), ("pilot-rate-feedback", 2, 0))}
    require(stats.get("invalid_requests") == 0 and stats.get("calls") == expected, "pilot_agent_protocol_calls_failed")
    return {"scope": "local_http_protocol_fixture", "completed_tasks": 5, "failed_tasks": 2,
            "rag_feedback_branches": 2, "planning_http_calls": 13, "answer_http_calls": 5,
            "history_and_session_isolation": True, "trace_delta_export_usage": True}
