#!/usr/bin/env python3
"""Static checks for business RAG acceptance toolkit (no Docker)."""

import json
import sys
import unittest
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


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BusinessRagAcceptanceStaticTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("business_rag_acceptance static tests passed")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
