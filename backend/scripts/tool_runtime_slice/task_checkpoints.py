from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from app.providers.base import ProviderCallError
from app.services import task_checkpoint_service as checkpoints
from app.services.tool_runtime import DefaultToolRegistryProvider, StaticToolRegistryProvider


class TaskCheckpointsMixin:
    def checkpoint_fixture(self):
        plan = [{"name": "task_plan", "input": {}}, {"name": "calc_eval", "input": {"expression": "2+3"}}]
        steps = [{"id": str(uuid4()), "type": "thought", "content": "plan", "meta": {"checkpoint_plan": plan}}]
        for index, node in enumerate(plan, 1):
            steps.append({"id": str(uuid4()), "type": "action", "content": "result", "meta": {
                "checkpoint_index": index, "tokens": 9, "cost_estimate": 1.0,
                "checkpoint_observations": [f"result {index}"], "tool": {"name": node["name"], "status": "done"}}})
        return plan, steps

    def test_task_checkpoint_only_actual_builtin_runners_are_supported(self):
        plan, _ = self.checkpoint_fixture()
        registry = DefaultToolRegistryProvider().load_tool_registry()
        self.assertEqual(checkpoints.checkpoint_plan(plan, StaticToolRegistryProvider(registry)), plan)
        registry["calc_eval"] = replace(registry["calc_eval"], runner=lambda **kwargs: {})
        self.assertIsNone(checkpoints.checkpoint_plan(plan, StaticToolRegistryProvider(registry)))

    def test_task_checkpoint_rejects_http_dag_and_redacted_inputs(self):
        plan, _ = self.checkpoint_fixture()
        provider = DefaultToolRegistryProvider()
        for node in [{"name": "external_http", "input": {}},
                     {"name": "calc_eval", "input": {"expression": "0"}, "depends_on": []},
                     {"name": "calc_eval", "input": {"expression": "0", "api_key": "secret"}}]:
            self.assertIsNone(checkpoints.checkpoint_plan([*plan, node], provider))
        self.assertIsNone(checkpoints.checkpoint_plan([], provider))

    def test_task_checkpoint_candidates_stop_after_failed_prefix(self):
        _, steps = self.checkpoint_fixture()
        self.assertEqual(len(checkpoints.checkpoint_candidates(steps)), 2)
        steps[1]["meta"]["tool"]["status"] = "error"
        self.assertEqual(len(checkpoints.checkpoint_candidates(steps)), 1)
        self.assertIsNone(checkpoints.build_checkpoint_seed(steps, steps[2]["id"]))

    def test_task_checkpoint_seed_is_independent_and_bounded(self):
        _, steps = self.checkpoint_fixture()
        before = deepcopy(steps)
        seed = checkpoints.build_checkpoint_seed(steps, steps[-1]["id"])
        restored, observations = checkpoints.restored_prefix(seed, 2)
        self.assertEqual(observations, ["result 1"])
        self.assertEqual(restored[0]["seq"], 2)
        self.assertNotEqual(restored[0]["id"], steps[1]["id"])
        self.assertEqual(restored[0]["meta"]["tokens"], 0)
        self.assertEqual(restored[0]["meta"]["cost_estimate"], 0)
        self.assertTrue(restored[0]["meta"]["checkpoint_reused"])
        self.assertEqual(steps, before)
        with patch.object(checkpoints, "MAX_SNAPSHOT_BYTES", 1):
            self.assertIsNone(checkpoints.build_checkpoint_seed(steps, steps[-1]["id"]))

    def test_task_checkpoint_old_or_unknown_steps_are_unavailable(self):
        _, steps = self.checkpoint_fixture()
        self.assertIsNone(checkpoints.build_checkpoint_seed(steps, str(uuid4())))
        self.assertEqual(checkpoints.checkpoint_candidates(steps[1:]), [])
        self.assertEqual(checkpoints.load_trace("invalid"), [])

    def test_task_checkpoint_resume_checks_current_capabilities(self):
        _, steps = self.checkpoint_fixture()
        seed = checkpoints.build_checkpoint_seed(steps, steps[-1]["id"])
        with self.assertRaises(ProviderCallError) as raised:
            checkpoints.validate_resume(seed, StaticToolRegistryProvider({}))
        self.assertEqual(raised.exception.code, "checkpoint_unavailable")
        self.assertFalse(raised.exception.retryable)
