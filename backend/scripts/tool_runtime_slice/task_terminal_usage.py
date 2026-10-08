"""Unknown final consumption stays unknown in failed-task accounting."""

from app.providers.base import ProviderUsage
from app.services.task_terminal_usage import build_terminal_usage
from app.services.usage_accounting import task_usage_totals


class TaskTerminalUsageMixin:
    def terminal_usage(self, *, planning=None, final=None, provider=None):
        return build_terminal_usage(planning_usage=planning, final_usage=final,
                                    provider_usage=provider, prompt_price=0.001, completion_price=0.002)

    def test_task_terminal_usage_no_record_is_unknown(self):
        self.assertIsNone(self.terminal_usage())
        self.assertIsNone(self.terminal_usage(provider=ProviderUsage(-1, True, None)))

    def test_task_terminal_usage_planning_only_does_not_invent_final_consumption(self):
        result = self.terminal_usage(planning={"prompt_tokens": 10, "completion_tokens": 2,
                                              "total_tokens": 12, "cost_estimate": 0.000014,
                                              "usage_source": "provider"})
        self.assertNotIn("prompt_tokens", result)
        self.assertNotIn("completion_tokens", result)
        self.assertEqual(result["overall_total_tokens"], 12)
        self.assertEqual(task_usage_totals(result), (10, 2, 0.000014))

    def test_task_terminal_usage_partial_provider_fields_stay_partial(self):
        result = self.terminal_usage(provider=ProviderUsage(5, None, 9))
        self.assertEqual(result["prompt_tokens"], 5)
        self.assertIsNone(result["completion_tokens"])
        self.assertIsNone(result["cost_estimate"])
        self.assertIsNone(result["total_tokens"])
        self.assertEqual(result["provider_total_tokens"], 9)
        self.assertEqual(task_usage_totals(result), (5, None, None))

    def test_task_terminal_usage_valid_zero_is_preserved(self):
        result = self.terminal_usage(provider=ProviderUsage(0, 0, 0))
        self.assertEqual((result["total_tokens"], result["cost_estimate"]), (0, 0))

    def test_task_terminal_usage_known_final_and_planning_sum_once(self):
        final = {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7,
                 "cost_estimate": 0.000009, "usage_source": "provider"}
        planning = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12,
                    "cost_estimate": 0.000014, "usage_source": "provider"}
        result = self.terminal_usage(planning=planning, final=final, provider=ProviderUsage(999, 999, 1998))
        self.assertEqual(result["total_tokens"], 7)
        self.assertEqual(result["overall_total_tokens"], 19)
        self.assertEqual(result["overall_cost_estimate"], 0.000023)
        self.assertNotIn("overall_total_tokens", final)
