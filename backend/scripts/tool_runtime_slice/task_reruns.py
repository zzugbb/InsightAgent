from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import task_reruns as routes
from app.services import task_rerun_service as service


class TaskRerunsMixin:
    def test_task_rerun_request_rejects_blank_input_and_invalid_key(self):
        for payload in [{"user_input": "  "}, {"user_input": "x" * 64001}, {"idempotency_key": "bad"}]:
            with self.assertRaises(ValidationError):
                routes.TaskRerunRequest(**payload)

    def test_task_rerun_request_defaults_to_original_and_unique_keys(self):
        a, b = routes.TaskRerunRequest(), routes.TaskRerunRequest()
        self.assertIsNone(a.user_input)
        self.assertNotEqual(a.idempotency_key, b.idempotency_key)

    def test_task_rerun_request_trims_edited_input(self):
        self.assertEqual(routes.TaskRerunRequest(user_input=" edit ").user_input, "edit")

    def test_task_rerun_service_invalid_edit_rejected_before_database(self):
        with patch.object(service, "get_db_connection") as db:
            for value in [" ", "x" * 64001]:
                with self.assertRaises(service.TaskRerunError) as raised:
                    service.create_task_rerun(user_id="a", parent_task_id="source", user_input=value, idempotency_key="key")
                self.assertEqual(raised.exception.status_code, 422)
            db.assert_not_called()

    def test_task_rerun_route_uses_normalized_create_summary(self):
        parent = uuid4()
        with patch.object(routes, "create_task_rerun", return_value={"task_id": "child", "session_id": "session",
                              "status": "success", "parent_task_id": str(parent)}) as create:
            response = routes.post_rerun(parent, routes.TaskRerunRequest(user_input="edited"), {"id": "owner"})
        self.assertEqual(response.status_normalized, "completed")
        self.assertEqual(response.parent_task_id, str(parent))
        self.assertEqual(create.call_args.kwargs["user_id"], "owner")

    def test_task_rerun_route_translates_fixed_errors(self):
        for status, code in [(404, "task_not_found"), (409, "rerun_parent_not_terminal")]:
            with patch.object(routes, "create_task_rerun", side_effect=service.TaskRerunError(status, code)):
                with self.assertRaises(HTTPException) as raised:
                    routes.post_rerun(uuid4(), routes.TaskRerunRequest(), {"id": "owner"})
                self.assertEqual(raised.exception.status_code, status)
                self.assertEqual(raised.exception.detail, code)

    def test_task_rerun_list_route_is_owner_scoped(self):
        task_id = uuid4()
        with patch.object(routes, "get_task_reruns", return_value={"task_id": str(task_id), "is_rerun": False,
                              "parent_task_id": None, "items": [], "total": 0, "limit": 5, "offset": 10,
                              "has_more": False}) as get:
            response = routes.get_reruns(task_id, 5, 10, {"id": "owner"})
        self.assertEqual(get.call_args.kwargs, {"task_id": str(task_id), "user_id": "owner", "limit": 5, "offset": 10})
        self.assertEqual(response.total, 0)
