"""Exercise current task contracts inside the disposable production/mock image stack."""

from uuid import uuid4


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def check_task_contracts(base, token, *, request_json, request_text, read_stream, wait_until):
    """Never accepts provider credentials; the caller owns a disposable mock backend."""
    def api(path, payload=None):
        return request_json(base + path, payload=payload, token=token)

    job_input = {
        "idempotency_key": str(uuid4()), "knowledge_base_id": "default",
        "documents": [{"text": "Pilot fixture: a blue telescope is located on a mountain.", "source": "pilot-fixture"}],
    }
    job = api("/api/rag/ingest-jobs", job_input)
    require(api("/api/rag/ingest-jobs", job_input)["id"] == job["id"], "pilot_ingest_idempotency_failed")

    def imported():
        current = api(f"/api/rag/ingest-jobs/{job['id']}")
        require(current.get("status") not in {"failed", "cancelled"}, "pilot_ingest_failed")
        return current if current.get("status") == "completed" else None

    completed_job = wait_until("background import", imported, timeout=45)
    require(completed_job is not None and completed_job.get("progress") == {
        "documents_processed": 1, "chunks_written": 1, "chunk_total": 1,
    }, "pilot_ingest_progress_failed")
    recall = api("/api/rag/query", {"knowledge_base_id": "default", "query": "blue telescope", "top_k": 3})
    require(recall.get("hit_count") == 1 and "blue telescope" in recall["hits"][0]["content"], "pilot_rag_readback_failed")

    source = api("/api/tasks", {"user_input": "rag blue telescope [calc:2+3]"})
    source_id = source["task_id"]

    def run(task_id):
        events = read_stream(base + f"/api/tasks/{task_id}/stream", token)
        require(any(event == "done" for event, _ in events), "pilot_task_done_missing")
        require(not any(event == "error" for event, _ in events), "pilot_task_stream_failed")
        task = api(f"/api/tasks/{task_id}")
        require(task.get("status_normalized") == "completed", "pilot_task_not_completed")
        steps = api(f"/api/tasks/{task_id}/trace")["steps"]
        require(bool(steps), "pilot_task_trace_missing")
        ids, seqs = [step["id"] for step in steps], [step["seq"] for step in steps]
        require(len(set(ids)) == len(ids) and seqs == sorted(set(seqs)), "pilot_trace_cursor_failed")
        delta = api(f"/api/tasks/{task_id}/trace/delta?after_seq=0&limit=100")["steps"]
        require([(step["id"], step["seq"]) for step in delta] == list(zip(ids, seqs)), "pilot_trace_delta_failed")
        exported = api(f"/api/tasks/{task_id}/export/json")
        require(exported.get("version") == "1.0", "pilot_export_version_failed")
        require([(step["id"], step["seq"]) for step in exported["trace"]["steps"]] == list(zip(ids, seqs)), "pilot_export_trace_failed")
        require(bool(request_text(base + f"/api/tasks/{task_id}/export/markdown", token)), "pilot_markdown_export_missing")
        return task, steps, exported

    _, source_steps, before = run(source_id)
    source_tools = {step.get("meta", {}).get("tool", {}).get("name"): step for step in source_steps if step["type"] == "action"}
    require(set(source_tools) == {"task_plan", "task_retrieve", "calc_eval"}, "pilot_builtin_tools_missing")
    require(source_tools["calc_eval"]["meta"]["tool"]["output_preview"].get("result") == 5, "pilot_calculator_failed")
    require(source_tools["task_retrieve"]["meta"]["tool"]["output_preview"].get("hit_count") == 1, "pilot_task_retrieval_failed")
    require(any(step["meta"].get("step_type") == "rag_retrieval" for step in source_steps), "pilot_rag_trace_missing")
    selected = next((item for item in api(f"/api/tasks/{source_id}/checkpoints")["items"] if item["tool_name"] == "calc_eval"), None)
    require(selected is not None and selected["reused_steps"] == 2, "pilot_checkpoint_unavailable")
    branch_input = {"idempotency_key": str(uuid4()), "checkpoint_step_id": selected["step_id"]}
    branch = api(f"/api/tasks/{source_id}/reruns", branch_input)
    retry = api(f"/api/tasks/{source_id}/reruns", branch_input)
    require(branch["task_id"] == retry["task_id"] and branch["session_id"] != source["session_id"], "pilot_checkpoint_branch_failed")
    _, branch_steps, _ = run(branch["task_id"])
    reused = [step for step in branch_steps if step.get("meta", {}).get("checkpoint_reused")]
    reused_tools = {step["meta"]["tool"]["name"] for step in reused if step["type"] == "action"}
    fresh_tools = [step["meta"]["tool"]["name"] for step in branch_steps if step["type"] == "action" and not step["meta"].get("checkpoint_reused")]
    require(reused_tools == {"task_plan", "task_retrieve"} and fresh_tools == ["calc_eval"], "pilot_checkpoint_prefix_failed")
    require(all(step["meta"].get("tokens", 0) == 0 and step["meta"].get("cost_estimate") == 0 for step in reused), "pilot_checkpoint_usage_failed")
    require(not set(step["id"] for step in source_steps) & set(step["id"] for step in branch_steps), "pilot_checkpoint_trace_identity_failed")
    after = api(f"/api/tasks/{source_id}/export/json")
    require(all(after[field] == before[field] for field in ("task", "trace", "messages")), "pilot_checkpoint_source_changed")

    cancelled = api(f"/api/tasks/{source_id}/reruns", {"idempotency_key": str(uuid4())})
    api(f"/api/tasks/{cancelled['task_id']}/cancel", {})
    events = read_stream(base + f"/api/tasks/{cancelled['task_id']}/stream", token)
    require(not any(event == "done" for event, _ in events), "pilot_cancelled_task_restarted")
    require(api(f"/api/tasks/{cancelled['task_id']}").get("status_normalized") == "cancelled", "pilot_task_cancel_failed")
    lineage = api(f"/api/tasks/{source_id}/reruns")
    require(lineage.get("total") == 2, "pilot_branch_lineage_failed")
    require(api(f"/api/tasks/{branch['task_id']}/reruns").get("parent_task_id") == source_id, "pilot_branch_parent_failed")
    return {"background_imports": 1, "rag_hits": 1, "completed_tasks": 2,
            "checkpoint_reused_tools": 2, "cancelled_tasks": 1, "export_version": "1.0"}
