#!/usr/bin/env python3
"""Static checks for business RAG acceptance toolkit (no Docker)."""

import json
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from business_rag_acceptance_runner import (  # noqa: E402
    SYNTHETIC_FIXTURE,
    build_report,
    compare_tool_claims,
    final_answer_text,
    load_materials,
    load_questions,
    run_auto_checks,
    evaluate_question,
    trace_tool_names,
    write_report,
    summarize_usage,
    sha256_prefix,
)


class BusinessRagAcceptanceStaticTests(unittest.TestCase):
    def test_fixture_loads(self):
        materials = load_materials(SYNTHETIC_FIXTURE / "materials")
        spec = load_questions(SYNTHETIC_FIXTURE / "questions.json")
        self.assertGreaterEqual(len(materials), 1)
        self.assertGreaterEqual(len(spec["questions"]), 2)

    def test_final_answer_text_reads_trace_final_answer_step(self):
        steps = [
            {"type": "action", "content": "retrieve", "meta": {"step_type": "rag_retrieval"}},
            {
                "type": "observation",
                "content": "检索结果显示预算为 7，加倍后为 14。",
                "meta": {"step_type": "final_answer"},
            },
        ]
        self.assertIn("14", final_answer_text(steps))

    def test_auto_checks_and_report_shape(self):
        answer = "资料中未记载上线日期。"
        tools = {"task_retrieve"}
        checks = [
            {"kind": "answer_not_documented"},
            {"kind": "citation_source", "source": "star-sail-guide.md"},
        ]
        results = run_auto_checks(checks, answer=answer, tools=tools, sources={"star-sail-guide.md"})
        results.append(compare_tool_claims(answer, tools))
        self.assertTrue(all(item.status == "pass" for item in results))
        report = build_report(
            mode="static",
            kb_id="kb",
            materials_fingerprint=sha256_prefix("x"),
            question_results=[],
            status_label="待外部验收（静态自测）",
        )
        self.assertEqual(report["schema_version"], 1)
        self.assertIn("summary", report)

    def test_failed_task_cannot_pass_no_tool_checks(self):
        result = evaluate_question({"id": "failed"}, task_id="t", steps=[], task={"status": "failed"})
        self.assertEqual(result.verdict, "auto_fail")

    def test_completed_task_without_answer_cannot_pass(self):
        result = evaluate_question({"id": "empty"}, task_id="t", steps=[], task={"status": "completed"})
        self.assertEqual(result.verdict, "auto_fail")

    def test_only_successful_current_actions_count_as_executed(self):
        steps = [
            {"type": "action", "meta": {"tool": {"name": "calc_eval", "status": "failed"}}},
            {"type": "action", "meta": {"tool": {"name": "planned", "status": "running"}}},
            {"type": "action", "meta": {"tool": {"name": "reused", "status": "done"}, "checkpoint_reused": True}},
            {"type": "thought", "meta": {"tool": {"name": "requested", "status": "done"}}},
            {"type": "action", "meta": {"step_type": "rag_retrieval", "tool": {"name": "task_retrieve", "status": "done"}}},
        ]
        self.assertEqual(trace_tool_names(steps), {"task_retrieve"})

    def test_negated_calculator_statement_is_not_a_claim(self):
        for answer in ["没有调用计算工具，14 是自行推算。", "计算工具未调用。", "未使用 Python 计算。", "本轮计算工具未实际执行。", "不能声称 Calculator 已调用。"]:
            with self.subTest(answer=answer):
                self.assertEqual(compare_tool_claims(answer, set()).status, "pass")

    def test_requested_tool_execution_explicitly_unfinished_is_not_a_claim(self):
        answer = '用户要求的“实际调用计算工具”**仍未完成**。'
        self.assertEqual(compare_tool_claims(answer, set()).status, "pass")

    def test_positive_claim_after_negation_is_still_rejected(self):
        answer = "没有调用 Python，但使用计算工具验证了结果。"
        self.assertEqual(compare_tool_claims(answer, set()).status, "fail")

    def test_ambiguous_tool_mention_requires_review(self):
        steps = [{"type": "observation", "content": "计算工具可用于复核。", "meta": {"step_type": "final_answer"}}]
        result = evaluate_question({"id": "mention"}, task_id="t", steps=steps, task={"status": "completed"})
        self.assertEqual(result.verdict, "manual_review")

    def test_report_creates_missing_parent_directories(self):
        with tempfile.TemporaryDirectory() as root:
            report = build_report(mode="static", kb_id="kb", materials_fingerprint="hash", question_results=[], status_label="pending")
            md = Path(root) / "md" / "report.md"
            js = Path(root) / "json" / "report.json"
            write_report(report, md, js)
            self.assertTrue(md.exists())
            self.assertEqual(json.loads(js.read_text())["summary"]["total"], 0)

    def test_usage_reads_flat_runtime_payload(self):
        payload = {"overall_total_tokens": 120.0, "prompt_tokens": 30, "completion_tokens": 10,
                   "planning_prompt_tokens": 60, "planning_completion_tokens": 20}
        result = summarize_usage({"usage_json": json.dumps(payload)})
        self.assertEqual(result, {"known": True, "total_tokens": 120, "planning_tokens": 80, "final_tokens": 40})

    def test_usage_partial_fields_remain_unknown(self):
        payload = {"planning_prompt_tokens": 20, "planning_completion_tokens": 10,
                   "provider_total_tokens": 50, "overall_total_tokens": None}
        self.assertFalse(summarize_usage({"usage_json": payload})["known"])

    def test_invalid_usage_numbers_remain_unknown(self):
        for total in [True, -1, "secret", float("inf")]:
            self.assertFalse(summarize_usage({"usage_json": {"overall_total_tokens": total}})["known"])

    def test_historical_tool_claim_requires_review_for_current_task(self):
        self.assertEqual(compare_tool_claims("上一轮已由 calc_eval 执行，本轮自行推算。", set()).status, "review")

    def test_conditional_tool_mention_is_not_rejected(self):
        self.assertEqual(compare_tool_claims("建议使用计算工具验证。", set()).status, "review")

    def test_failed_tool_attempt_does_not_pass_not_executed_check(self):
        steps = [
            {"type": "action", "meta": {"tool": {"name": "calc_eval", "status": "failed"}}},
            {"type": "observation", "meta": {"step_type": "final_answer"}, "content": "工具失败。"},
        ]
        spec = {"id": "attempt", "checks": {"auto": [{"kind": "tool_not_executed", "tool": "calc_eval"}]}}
        result = evaluate_question(spec, task_id="t", steps=steps, task={"status": "completed"})
        self.assertEqual(result.verdict, "auto_fail")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BusinessRagAcceptanceStaticTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("business_rag_acceptance static tests passed")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
