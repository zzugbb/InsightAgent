"""Explicit offline preparation only; never imported by the public application.

Creates dedicated synthetic sessions/KB, reads an existing saved GLM credential
in memory, and publishes only a field allowlist. No private session reads.
Run from the repository root with backend/.venv/bin/python.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/scripts")]
from app.db import get_db_connection
from app.api.routes.tasks import TaskCreateRequest, create_task_entry, get_task_detail, get_task_trace_detail
from app.api.routes.rag import RagIngestRequest, post_rag_ingest
from app.services import chat_persistence_service as persistence
from app.services.settings_service import get_stored_settings
from app.services.chat_execution_service import stream_task_execution
from app.services.task_rerun_service import create_task_rerun
from app.config import get_settings
from test_agent_feedback_postgres import ConditionalProvider

META_KEYS = {"step_type", "plan_node_id", "depends_on", "agent_round", "agent_decision",
             "agent_from_step_ids", "agent_stop_reason", "provider_finish_reason", "parallel_group_id", "model",
             "planning_provider_used", "planning_provider_attempted", "latency", "tokens",
             "prompt_tokens", "completion_tokens", "tool", "rag", "label", "error_event"}
TOOL_KEYS = {"name", "label", "input", "output_preview", "result_summary", "status", "error"}
RAG_KEYS = {"chunks", "knowledge_base_id", "chunk_metadata", "document_versions"}

def run():
    with get_db_connection() as db:
        rows = db.execute("SELECT user_id FROM user_settings WHERE mode = 'remote' AND model = 'glm-5.3' ORDER BY updated_at DESC").fetchall()
    assert len(rows) == 1, "saved_configuration_not_unique"
    user = {"id": rows[0]["user_id"], "role": "user"}
    settings = get_stored_settings(user["id"])
    assert settings.api_key and settings.base_url, "saved_configuration_incomplete"
    baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prepared = datetime.now(timezone.utc).isoformat()
    kb = "showcase-" + uuid4().hex[:12]
    # Dedicated process only: even rule fallback must never search an existing KB.
    get_settings().rag_default_knowledge_base_id = kb
    material = (ROOT / "showcase/data/materials/budget.md").read_text()
    dest = ROOT / "showcase/data/cases.json"
    assert not dest.exists() or "--resume" in sys.argv, "existing_records_require_explicit_review"
    report = json.loads(dest.read_text()) if "--resume" in sys.argv and dest.exists() else []
    assert all(r["id"] == "rag" for r in report), "finished_records_must_not_be_overwritten"
    if not any(r["id"]=="rag" for r in report):
        post_rag_ingest(RagIngestRequest(knowledge_base_id=kb,
            documents=[{"text": material, "source": "budget.md", "document_id": "budget.md"}]), current_user=user)

    def capture(key, title, prompt, source, *, parent=None, provider=None):
        if parent:
            branch = create_task_rerun(user_id=user["id"], parent_task_id=parent,
                user_input=prompt, idempotency_key=str(uuid4()))
            task_id, session_id = branch["task_id"], branch["session_id"]
        else:
            session = persistence.create_session_record("公开合成演示 · " + title, user["id"])
            task = create_task_entry(TaskCreateRequest(session_id=session["id"], user_input=prompt), current_user=user)
            task_id, session_id = task.task_id, task.session_id
        started = time.monotonic()
        print(json.dumps({"event": "capture_started", "case": key}), flush=True)
        with patch("app.services.chat_execution_service.get_llm_provider", return_value=provider) if provider else nullcontext():
            for _ in stream_task_execution(task_id=task_id, session_id=session_id, user_id=user["id"], prompt=prompt):
                pass
        detail = get_task_detail(task_id, current_user=user).model_dump(mode="json")
        steps = get_task_trace_detail(task_id, current_user=user).model_dump(mode="json")["steps"]
        raw = persistence.get_task(task_id, user["id"])
        usage = json.loads(raw["usage_json"]) if raw.get("usage_json") else {}
        ids = {step["id"]: f"{key}-{index+1}" for index, step in enumerate(steps)}
        public = []
        for step in steps:
            meta = {k:v for k,v in (step.get("meta") or {}).items() if k in META_KEYS and v is not None}
            if "tool" in meta:
                meta["tool"] = {k:v for k,v in meta["tool"].items() if k in TOOL_KEYS}
            if "rag" in meta:
                meta["rag"] = {k:v for k,v in meta["rag"].items() if k in RAG_KEYS}
                for field in ("chunk_metadata", "document_versions"):
                    if field in meta["rag"]:
                        meta["rag"][field] = [{k:v for k,v in item.items() if k in {"source", "document_version", "document_id", "content_hash"}} for item in meta["rag"][field]]
            if "agent_from_step_ids" in meta:
                meta["agent_from_step_ids"] = [ids[x] for x in meta["agent_from_step_ids"] if x in ids]
            public.append({"id":ids[step["id"]], "seq":step.get("seq"), "type":step["type"], "content":step["content"], "meta":meta})
        answer = next((s["content"] for s in reversed(public) if s["meta"].get("step_type") == "final_answer"), "")
        result = {"id":key, "title":title, "prompt":prompt, "source":source,
                  "model":settings.model if source == "real_model" else "offline-feedback-fixture",
                  "status":detail["status_normalized"], "answer":answer, "steps":public,
                  "elapsedSeconds":round(time.monotonic()-started, 3),
                  "usage":{k:usage.get(k) for k in ("planning_total_tokens", "total_tokens", "overall_total_tokens")} if source == "real_model" else None,
                  "preparedAt":prepared, "sourceCommit":baseline, "parentId":"failure" if parent else None}
        serialized = json.dumps(result, ensure_ascii=False)
        for value, alias in [(kb,"showcase-budget"), (user["id"],"demo-owner"), (task_id,key), (session_id,"demo-session")]:
            serialized = serialized.replace(value, alias)
        assert settings.api_key not in serialized
        assert settings.base_url not in serialized
        assert not re.search(r'sk-[A-Za-z0-9]{12,}|Bearer\s+\S+', serialized)
        result = json.loads(serialized)
        if key == "rag":
            chunks = [chunk for step in result["steps"] for chunk in (step["meta"].get("rag") or {}).get("chunk_metadata") or []]
            assert chunks and all(chunk.get("source")=="budget.md" for chunk in chunks), "unexpected_or_missing_document_source"
        report.append(result)
        dest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps({"event":"capture_finished", "case":key, "status":result["status"], "steps":len(public), "knownTokens":(result["usage"] or {}).get("overall_total_tokens")}), flush=True)
        return task_id, result

    rag = next((r for r in report if r["id"]=="rag"), None)
    if rag is None:
        _, rag = capture("rag", "知识检索与计算", f"[kb:{kb}] 请检索星帆实验的基础预算，并调用计算工具计算 7*2。方案 B 是基础预算的两倍。请引用 budget.md，简洁说明方案 B 预算。", "real_model")
    names = [s["meta"].get("tool",{}).get("name") for s in rag["steps"] if s["type"]=="action" and s["meta"].get("tool",{}).get("status")=="done"]
    assert rag["status"]=="completed" and "calc_eval" in names and "task_retrieve" in names, "rag_evidence_incomplete"
    assert any(s["meta"].get("rag", {}).get("chunk_metadata") for s in rag["steps"]), "rag_citations_missing"
    for step in rag["steps"]:
        for chunk in step["meta"].get("rag", {}).get("chunk_metadata") or []:
            assert chunk.get("source")=="budget.md", "unexpected_document_source"
    parent, failed = capture("failure", "原任务 · 受控失败", "先调用计算工具计算 2+3，再根据结果继续计算两倍。", "controlled_fixture", provider=ConditionalProvider(stop="error"))
    assert failed["status"]=="failed", "controlled_failure_missing"
    _, recovered = capture("recovery", "独立分支 · 明确输入", "请实际调用计算工具计算 (2+3)*2，并只用简短文字说明计算结果。", "real_model", parent=parent)
    assert recovered["status"]=="completed", "branch_not_completed"
    assert any(s["type"]=="action" and s["meta"].get("tool",{}).get("name")=="calc_eval" and s["meta"]["tool"].get("status")=="done" for s in recovered["steps"]), "branch_tool_missing"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"event":"public_records_ready", "runs":len(report), "sourceCommit":baseline}), flush=True)

if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        print(json.dumps({"event":"capture_failed", "errorType":type(error).__name__}), flush=True)
        raise SystemExit(1)
