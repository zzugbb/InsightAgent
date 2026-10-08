"""Whole-task usage in summaries, trends, ranks and source filters."""

from datetime import datetime
import json
from unittest.mock import MagicMock, patch

from app.services import chat_persistence_service as persistence


class TaskUsageAccountingMixin:
    def usage_accounting_report(self, payloads, *, source_filter=None):
        today = datetime.now().isoformat()
        rows = [{"id": f"task-{index}", "session_id": f"session-{index}", "session_title": "fixture",
                 "prompt": "fixture", "status": "completed", "trace_json": "[]",
                 "created_at": today, "updated_at": today, "usage_json": json.dumps(payload)}
                for index, payload in enumerate(payloads)]
        connection = MagicMock()
        connection.__enter__.return_value.execute.return_value.fetchall.return_value = rows
        with patch.object(persistence, "get_db_connection", return_value=connection):
            return (persistence.get_tasks_usage_summary("owner"),
                    persistence.get_tasks_usage_dashboard("owner", window_days=1, source_filter=source_filter))

    def test_usage_accounting_includes_planning_in_all_aggregate_views(self):
        payload = {"prompt_tokens": 30, "completion_tokens": 5, "cost_estimate": 0.04,
                   "planning_prompt_tokens": 30, "planning_completion_tokens": 6, "planning_cost_estimate": 0.05,
                   "overall_prompt_tokens": 60, "overall_completion_tokens": 11, "overall_cost_estimate": 0.09}
        summary, report = self.usage_accounting_report([payload])
        self.assertEqual(summary["total_tokens"], 71)
        self.assertAlmostEqual(summary["cost_estimate"], 0.09)
        self.assertEqual(report["summary"], summary)
        for view in (report["trend"], report["by_session"], report["top_tasks"]):
            self.assertEqual(view[0]["total_tokens"], 71)
            self.assertAlmostEqual(view[0]["cost_estimate"], 0.09)
        self.assertEqual(summary["avg_total_tokens"], 71)

    def test_usage_accounting_overall_values_are_not_double_counted(self):
        summary, _ = self.usage_accounting_report([{
            "prompt_tokens": 3, "completion_tokens": 2, "planning_prompt_tokens": 4,
            "overall_prompt_tokens": "7", "overall_completion_tokens": 0,
            "cost_estimate": 1, "planning_cost_estimate": 2, "overall_cost_estimate": 0,
        }])
        self.assertEqual(summary["prompt_tokens"], 7)
        self.assertEqual(summary["completion_tokens"], 0)
        self.assertEqual(summary["cost_estimate"], 0)

    def test_usage_accounting_missing_overall_fields_sum_known_stages(self):
        summary, _ = self.usage_accounting_report([{
            "prompt_tokens": "10", "completion_tokens": 2, "cost_estimate": "0.1",
            "planning_prompt_tokens": 5, "planning_completion_tokens": "3", "planning_cost_estimate": "0.2",
            "overall_prompt_tokens": 15,
        }])
        self.assertEqual((summary["prompt_tokens"], summary["completion_tokens"]), (15, 5))
        self.assertAlmostEqual(summary["cost_estimate"], 0.3)

    def test_usage_accounting_invalid_overall_values_fall_back_to_stages(self):
        for invalid in (None, "", "bad", True, -1, float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                summary, _ = self.usage_accounting_report([{
                    "prompt_tokens": 3, "planning_prompt_tokens": 4, "overall_prompt_tokens": invalid,
                }])
                self.assertEqual(summary["total_tokens"], 7)

    def test_usage_accounting_legacy_values_keep_existing_totals_and_ranking(self):
        summary, report = self.usage_accounting_report([
            {"prompt_tokens": 10, "completion_tokens": 4, "cost_estimate": 0.1},
            {"prompt_tokens": 2, "completion_tokens": 1, "planning_prompt_tokens": 20, "planning_completion_tokens": 3},
        ])
        self.assertEqual(summary["total_tokens"], 40)
        self.assertEqual([row["task_id"] for row in report["top_tasks"]], ["task-1", "task-0"])
        self.assertEqual([row["session_id"] for row in report["by_session"]], ["session-1", "session-0"])

    def test_usage_accounting_sources_include_planning_for_mixed_filter(self):
        summary, report = self.usage_accounting_report([{
            "prompt_tokens": 10, "completion_tokens": 2, "usage_source": "provider",
            "planning_prompt_tokens": 3, "planning_completion_tokens": 1, "planning_usage_source": "estimated",
        }], source_filter="mixed")
        self.assertEqual(summary["source_tasks_mixed"], 1)
        self.assertEqual(report["summary"]["source_tasks_mixed"], 1)
        self.assertEqual(report["top_tasks"][0]["source_kind"], "mixed")
        self.assertEqual(report["trend"][0]["source_tasks_mixed"], 1)

    def test_usage_accounting_planning_only_values_keep_missing_fields_unknown(self):
        summary, report = self.usage_accounting_report([{
            "planning_prompt_tokens": 4, "planning_cost_estimate": 0.03, "planning_usage_source": "provider",
        }])
        self.assertEqual(summary["total_tokens"], 4)
        self.assertEqual(summary["source_tasks_provider"], 1)
        self.assertEqual(report["summary"], summary)

    def test_usage_accounting_invalid_stage_values_do_not_poison_json_response(self):
        summary, report = self.usage_accounting_report([{
            "prompt_tokens": True, "completion_tokens": "NaN", "cost_estimate": "Infinity",
            "planning_prompt_tokens": -1,
        }])
        self.assertEqual(summary["total_tokens"], 0)
        self.assertIsNone(summary["avg_total_tokens"])
        self.assertIsNone(summary["avg_cost_estimate"])
        json.dumps(report, allow_nan=False)
