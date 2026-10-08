#!/usr/bin/env python3
"""Business RAG acceptance toolkit: import user materials, run question set, emit low-sensitivity report.

Self-test uses isolated PostgreSQL/Chroma and a local provider fixture (no remote model).
API mode targets a running backend with bearer token; only creates/cleans its own knowledge base prefix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unittest
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(BACKEND_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

SYNTHETIC_FIXTURE = REPO_ROOT / "scripts/fixtures/business_rag_acceptance/synthetic"
KB_PREFIX = "acceptance-toolkit-"

REDACT_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    out = value
    for pattern in REDACT_PATTERNS:
        out = pattern.sub("[redacted]", out)
    return out


def sha256_prefix(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_questions(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "questions" not in payload:
        raise ValueError("questions file must contain 'questions' array")
    return payload


def load_materials(materials_dir: Path) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for file_path in sorted(materials_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".md", ".txt", ".markdown"}:
            continue
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        rel = file_path.relative_to(materials_dir).as_posix()
        documents.append({"text": text, "source": rel, "document_id": rel})
    if not documents:
        raise ValueError(f"no ingestible documents under {materials_dir}")
    return documents


@dataclass
class CheckResult:
    kind: str
    status: str
    detail: str


@dataclass
class QuestionResult:
    question_id: str
    task_id: str | None
    task_status: str | None
    auto_checks: list[CheckResult] = field(default_factory=list)
    manual_notes: list[str] = field(default_factory=list)
    usage_summary: dict[str, Any] = field(default_factory=dict)
    answer_fingerprint: str | None = None

    @property
    def auto_pass(self) -> bool:
        return all(item.status == "pass" for item in self.auto_checks)

    @property
    def verdict(self) -> str:
        if not self.auto_pass:
            return "auto_fail"
        if self.manual_notes:
            return "manual_review"
        return "auto_pass"


def summarize_usage(task: dict[str, Any]) -> dict[str, Any]:
    raw = task.get("usage_json")
    if not raw:
        return {"known": False, "reason": "missing_usage_json"}
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return {"known": False, "reason": "invalid_usage_json"}
    overall = payload.get("overall") if isinstance(payload, dict) else None
    if isinstance(overall, dict) and overall.get("total_tokens") is not None:
        return {
            "known": True,
            "total_tokens": overall.get("total_tokens"),
            "planning_tokens": (payload.get("planning") or {}).get("total_tokens"),
            "final_tokens": (payload.get("final") or {}).get("total_tokens"),
        }
    return {"known": False, "reason": "partial_or_unknown_overall"}


def trace_tool_names(steps: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for step in steps:
        meta = step.get("meta") or {}
        tool = meta.get("tool")
        if isinstance(tool, dict) and tool.get("name"):
            names.add(str(tool["name"]))
        step_type = meta.get("step_type") or step.get("type")
        if step_type == "rag_retrieval":
            names.add("task_retrieve")
    return names


def trace_sources(steps: list[dict[str, Any]]) -> set[str]:
    sources: set[str] = set()
    for step in steps:
        meta = step.get("meta") or {}
        rag = meta.get("rag") or {}
        for item in rag.get("chunk_metadata") or []:
            if isinstance(item, dict) and item.get("source"):
                sources.add(str(item["source"]))
    return sources


def final_answer_text(steps: list[dict[str, Any]], task: dict[str, Any] | None = None) -> str:
    for step in reversed(steps):
        meta = step.get("meta") or {}
        if meta.get("step_type") == "final_answer":
            content = str(step.get("content") or "")
            if content:
                return content
        if step.get("type") == "message" and meta.get("role") == "assistant":
            return str(step.get("content") or "")
    if task:
        for key in ("result", "output", "answer"):
            value = task.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


NOT_DOCUMENTED_MARKERS = (
    "未记载",
    "没有记载",
    "未提及",
    "未找到",
    "资料中未",
    "没有提到",
    "无法从资料",
    "not documented",
    "not mentioned",
)


def run_auto_checks(
    checks: Iterable[dict[str, Any]],
    *,
    answer: str,
    tools: set[str],
    sources: set[str],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in checks:
        kind = str(check.get("kind") or "")
        if kind == "citation_source":
            expected = str(check.get("source") or "")
            ok = any(expected in source or source.endswith(expected) for source in sources)
            results.append(CheckResult(kind, "pass" if ok else "fail", f"expected source {expected}, saw {sorted(sources)}"))
        elif kind == "answer_contains":
            text = str(check.get("text") or "")
            ok = text in answer
            results.append(CheckResult(kind, "pass" if ok else "fail", f"expected substring hash {sha256_prefix(text)}"))
        elif kind == "answer_not_documented":
            ok = any(marker in answer for marker in NOT_DOCUMENTED_MARKERS)
            results.append(CheckResult(kind, "pass" if ok else "fail", "expected explicit not-documented wording"))
        elif kind == "tool_executed":
            tool = str(check.get("tool") or "")
            ok = tool in tools
            results.append(CheckResult(kind, "pass" if ok else "fail", f"expected tool {tool}, saw {sorted(tools)}"))
        elif kind == "tool_not_executed":
            tool = str(check.get("tool") or "")
            ok = tool not in tools
            results.append(CheckResult(kind, "pass" if ok else "fail", f"forbidden tool {tool}"))
        else:
            results.append(CheckResult(kind or "unknown", "fail", "unsupported auto check kind"))
    return results


def compare_tool_claims(answer: str, tools: set[str]) -> CheckResult:
    claims_calc = any(token in answer for token in ("计算工具", "Calculator", "calc_eval", "Python"))
    executed_calc = "calc_eval" in tools
    if claims_calc and not executed_calc:
        return CheckResult("tool_claim_vs_trace", "fail", "answer implies calculation tool but trace has no calc_eval")
    if claims_calc and executed_calc:
        return CheckResult("tool_claim_vs_trace", "pass", "calculation claim matches trace")
    return CheckResult("tool_claim_vs_trace", "pass", "no conflicting tool claim detected")


class BusinessRagAcceptanceRunner:
    def __init__(self, *, user_id: str = "owner", session_id: str | None = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid4())
        self.knowledge_base_id: str | None = None
        self.created_collections: list[tuple[str, str]] = []

    def ingest_materials(self, kb_id: str, documents: list[dict[str, str]]) -> None:
        from app.services import chroma_rag_service as rag_service

        self.knowledge_base_id = kb_id
        rag_service.ingest_knowledge_documents(
            user_id=self.user_id,
            knowledge_base_id=kb_id,
            documents=documents,
            chunk_size=400,
            chunk_overlap=40,
        )
        self.created_collections.append((self.user_id, kb_id))

    def cleanup(self) -> None:
        from app.services import chroma_rag_service as rag_service

        client = rag_service._http_client()
        for user_id, kb_id in self.created_collections:
            try:
                client.delete_collection(rag_service.rag_collection_name(user_id, kb_id))
            except Exception:
                pass
        self.created_collections.clear()

    def run_question(self, client: Any, provider: Any, prompt: str) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        response = client.post(
            "/api/tasks",
            json={"session_id": self.session_id, "user_input": prompt},
        )
        if response.status_code != 200:
            raise RuntimeError(f"create task failed: {response.status_code}")
        task_id = response.json()["task_id"]
        stream = client.get(f"/api/tasks/{task_id}/stream")
        if stream.status_code != 200 or "event: done" not in stream.text:
            raise RuntimeError(f"stream failed: {stream.status_code}")
        task = client.get(f"/api/tasks/{task_id}").json()
        steps = client.get(f"/api/tasks/{task_id}/trace").json().get("steps") or []
        return task_id, steps, task


def evaluate_question(
    spec: dict[str, Any],
    *,
    task_id: str,
    steps: list[dict[str, Any]],
    task: dict[str, Any],
) -> QuestionResult:
    answer = final_answer_text(steps, task)
    tools = trace_tool_names(steps)
    sources = trace_sources(steps)
    checks = spec.get("checks") or {}
    auto = run_auto_checks(checks.get("auto") or [], answer=answer, tools=tools, sources=sources)
    auto.append(compare_tool_claims(answer, tools))
    manual = [str(item) for item in (checks.get("manual") or [])]
    return QuestionResult(
        question_id=str(spec.get("id") or ""),
        task_id=task_id,
        task_status=str(task.get("status") or ""),
        auto_checks=auto,
        manual_notes=manual,
        usage_summary=summarize_usage(task),
        answer_fingerprint=sha256_prefix(answer) if answer else None,
    )


def build_report(
    *,
    mode: str,
    kb_id: str,
    materials_fingerprint: str,
    question_results: list[QuestionResult],
    status_label: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": mode,
        "external_acceptance_status": status_label,
        "knowledge_base_id": kb_id,
        "materials_fingerprint": materials_fingerprint,
        "summary": {
            "total": len(question_results),
            "auto_pass": sum(1 for item in question_results if item.verdict == "auto_pass"),
            "manual_review": sum(1 for item in question_results if item.verdict == "manual_review"),
            "auto_fail": sum(1 for item in question_results if item.verdict == "auto_fail"),
        },
        "questions": [
            {
                "id": item.question_id,
                "task_id": item.task_id,
                "task_status": item.task_status,
                "verdict": item.verdict,
                "usage": item.usage_summary,
                "answer_fingerprint": item.answer_fingerprint,
                "auto_checks": [{"kind": c.kind, "status": c.status, "detail": redact_text(c.detail)} for c in item.auto_checks],
                "manual_notes": item.manual_notes,
            }
            for item in question_results
        ],
    }


def write_report(report: dict[str, Any], output_md: Path, output_json: Path) -> None:
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Business RAG acceptance report",
        f"- generated_at: {report['generated_at']}",
        f"- mode: {report['mode']}",
        f"- external_acceptance_status: {report['external_acceptance_status']}",
        f"- knowledge_base_id: {report['knowledge_base_id']}",
        f"- materials_fingerprint: {report['materials_fingerprint']}",
        "",
        "## Summary",
        f"- total: {report['summary']['total']}",
        f"- auto_pass: {report['summary']['auto_pass']}",
        f"- manual_review: {report['summary']['manual_review']}",
        f"- auto_fail: {report['summary']['auto_fail']}",
        "",
        "## Questions",
    ]
    for item in report["questions"]:
        lines.append(f"### {item['id']} ({item['verdict']})")
        lines.append(f"- task_id: {item['task_id']}")
        lines.append(f"- task_status: {item['task_status']}")
        lines.append(f"- answer_fingerprint: {item['answer_fingerprint']}")
        lines.append(f"- usage: {json.dumps(item['usage'], ensure_ascii=False)}")
        for check in item["auto_checks"]:
            lines.append(f"- auto [{check['status']}] {check['kind']}: {check['detail']}")
        for note in item["manual_notes"]:
            lines.append(f"- manual: {note}")
        lines.append("")
    output_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


class SyntheticRagProvider:
    """Minimal planner that retrieves then calculates based on retrieved budget."""

    def __init__(self):
        from app.providers.mock_provider import MockLLMProvider
        from app.providers.base import ProviderResponse, ProviderUsage

        self._inner = MockLLMProvider(provider="business-rag-acceptance-fixture")
        self._ProviderResponse = ProviderResponse
        self._ProviderUsage = ProviderUsage
        self.planning_calls = 0

    @property
    def model(self):
        return self._inner.model

    @property
    def provider(self):
        return self._inner.provider

    def generate(self, prompt: str):
        self.planning_calls += 1
        if not prompt.startswith("You are the Task Planner for InsightAgent."):
            return self._inner.generate(prompt)
        tools: list[dict[str, Any]] = []
        if "Completed tool observations" not in prompt:
            kb = "acceptance-synthetic"
            if "[kb:" in prompt:
                kb = prompt.split("[kb:", 1)[1].split("]", 1)[0]
            tools = [{"name": "task_retrieve", "input": {"query": "budget", "knowledge_base_id": kb}}]
        else:
            observations = prompt.split("Completed tool observations (JSON):\n", 1)[1]
            has_budget = any(token in observations for token in ("budget: 7", "预算：7", "预算: 7"))
            if has_budget and "加倍" in prompt:
                tools = [{"name": "calc_eval", "input": {"expression": "7*2"}}]
        return self._ProviderResponse(
            json.dumps({"tools": tools}),
            self.model,
            self.provider,
            self._ProviderUsage(12, 3, 15),
        )

    def stream_generate(self, prompt: str):
        if "上线日期" in prompt or "launch" in prompt.lower():
            yield "资料中未记载上线日期，无法从当前知识库片段确认具体日期。"
            return
        if "14" in prompt or "加倍" in prompt:
            yield "检索结果显示预算为 7，加倍后为 14。"
            return
        yield "合成验收回答。"


@contextmanager
def isolated_client(provider):
    from unittest.mock import patch

    from app.api.deps import get_current_user
    from app.main import app
    from fastapi.testclient import TestClient

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: {"id": "owner", "role": "user"}
    try:
        with patch("app.services.chat_execution_service.get_llm_provider", return_value=provider), patch(
            "app.services.chat_execution_service.try_append_task_memory"
        ):
            yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def run_self_test() -> int:
    from task_postgres_fixture import run_isolated_postgres

    class SelfTestCase(unittest.TestCase):
        def test_synthetic_business_rag_acceptance(self):
            materials = load_materials(SYNTHETIC_FIXTURE / "materials")
            spec = load_questions(SYNTHETIC_FIXTURE / "questions.json")
            kb_id = spec.get("knowledge_base_id") or "acceptance-synthetic"
            runner = BusinessRagAcceptanceRunner()
            runner.ingest_materials(kb_id, materials)
            provider = SyntheticRagProvider()
            results: list[QuestionResult] = []
            try:
                with isolated_client(provider) as client:
                    for question in spec["questions"]:
                        prompt = str(question["prompt"])
                        if "[kb:" not in prompt:
                            prompt = f"{prompt} [kb:{kb_id}]"
                        task_id, steps, task = runner.run_question(client, provider, prompt)
                        results.append(evaluate_question(question, task_id=task_id, steps=steps, task=task))
            finally:
                runner.cleanup()
            fingerprint = sha256_prefix(json.dumps(materials, ensure_ascii=False, sort_keys=True))
            report = build_report(
                mode="self_test_fixture",
                kb_id=kb_id,
                materials_fingerprint=fingerprint,
                question_results=results,
                status_label="待外部验收（合成样本仅用于工具自测，不能代替真实业务资料）",
            )
            out_dir = Path("/tmp/insightagent-business-rag-acceptance-selftest")
            out_dir.mkdir(parents=True, exist_ok=True)
            write_report(report, out_dir / "report.md", out_dir / "report.json")
            self.assertGreaterEqual(report["summary"]["auto_pass"], 1)
            self.assertEqual(report["summary"]["auto_fail"], 0)

    return run_isolated_postgres(SelfTestCase, with_chroma=True)


def run_api_mode(args: argparse.Namespace) -> int:
    import httpx

    token = os.environ.get("INSIGHT_AGENT_ACCESS_TOKEN", "").strip()
    if not token:
        print("INSIGHT_AGENT_ACCESS_TOKEN is required for api mode", file=sys.stderr)
        return 2
    materials = load_materials(Path(args.materials_dir))
    spec = load_questions(Path(args.questions_file))
    kb_id = args.knowledge_base_id or f"{KB_PREFIX}{uuid4().hex[:10]}"
    headers = {"Authorization": f"Bearer {token}"}
    base = args.api_base_url.rstrip("/")
    documents_payload = {
        "knowledge_base_id": kb_id,
        "documents": materials,
        "chunk_size": 400,
        "chunk_overlap": 40,
    }
    with httpx.Client(base_url=base, headers=headers, timeout=120.0) as client:
        ingest = client.post("/api/rag/ingest", json=documents_payload)
        if ingest.status_code >= 400:
            print(f"ingest failed: {ingest.status_code}", file=sys.stderr)
            return 1
        session_id = str(uuid4())
        results: list[QuestionResult] = []
        for question in spec["questions"]:
            prompt = str(question["prompt"])
            if "[kb:" not in prompt:
                prompt = f"{prompt} [kb:{kb_id}]"
            created = client.post("/api/tasks", json={"session_id": session_id, "user_input": prompt})
            created.raise_for_status()
            task_id = created.json()["task_id"]
            stream = client.get(f"/api/tasks/{task_id}/stream")
            stream.raise_for_status()
            task = client.get(f"/api/tasks/{task_id}").json()
            steps = client.get(f"/api/tasks/{task_id}/trace").json().get("steps") or []
            results.append(evaluate_question(question, task_id=task_id, steps=steps, task=task))
        if args.cleanup:
            client.delete(f"/api/rag/knowledge-bases/{kb_id}")
    fingerprint = sha256_prefix(json.dumps(materials, ensure_ascii=False, sort_keys=True))
    report = build_report(
        mode="api",
        kb_id=kb_id,
        materials_fingerprint=fingerprint,
        question_results=results,
        status_label="待外部验收（缺真实业务资料复核与人工判断项）",
    )
    write_report(report, Path(args.output_md), Path(args.output_json))
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["auto_fail"] == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Business RAG acceptance toolkit")
    parser.add_argument("--self-test", action="store_true", help="Run isolated fixture self-test (Docker postgres/chroma)")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--materials-dir")
    parser.add_argument("--questions-file")
    parser.add_argument("--knowledge-base-id")
    parser.add_argument("--output-md", default="/tmp/insightagent-business-rag-acceptance/report.md")
    parser.add_argument("--output-json", default="/tmp/insightagent-business-rag-acceptance/report.json")
    parser.add_argument("--cleanup", action="store_true", help="Delete created knowledge base after api run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    if not args.materials_dir or not args.questions_file:
        print("--materials-dir and --questions-file are required unless --self-test", file=sys.stderr)
        return 2
    return run_api_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
