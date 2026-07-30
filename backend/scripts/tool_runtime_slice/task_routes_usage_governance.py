from __future__ import annotations

from .context import *


class TaskRoutesUsageGovernanceMixin:
    def test_get_tasks_forwards_query_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        calls: list[tuple[str, str | None]] = []
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Query Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("list", query))
                return [
                    {
                        "id": "task-query-1",
                        "session_id": session_id or "session-query",
                        "prompt": "query matched task",
                        "status": "completed",
                        "trace_json": None,
                        "usage_json": None,
                        "created_at": "2026-06-09T11:00:00",
                        "updated_at": "2026-06-09T11:05:00",
                    }
                ]

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("count", query))
                return 1

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-query",
                query="planning_suite",
                current_user={"id": "user-query"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(calls, [("list", "planning_suite"), ("count", "planning_suite")])
        self.assertEqual(payload.total, 1)
        self.assertEqual(len(payload.items), 1)

    def test_get_tasks_forwards_governance_filters_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile="planning_only",
                tool_registry_provider_source="planning_suite",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )

    def test_get_tasks_trusts_service_governance_filter_normalizer(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            chat_persistence_module._normalize_governance_filter = (
                lambda _value: (_ for _ in ()).throw(
                    AssertionError(
                        "task list route should trust service-layer governance filter normalization"
                    )
                )
            )
            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": " Planning_Only ",
                "tool_registry_provider_source_filter": " Planning_Suite ",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": " Planning_Only ",
                "tool_registry_provider_source_filter": " Planning_Suite ",
            },
        )

    def test_list_tasks_applies_query_to_prompt_id_and_trace_json(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-query",
                limit=20,
                session_id="session-query",
                offset=40,
                query="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(prompt) LIKE ?", rendered_query)
        self.assertIn("LOWER(id) LIKE ?", rendered_query)
        self.assertIn("LOWER(COALESCE(trace_json, '')) LIKE ?", rendered_query)
        self.assertEqual(
            rendered_params,
            (
                "user-query",
                "session-query",
                "%planning_suite%",
                "%planning_suite%",
                "%planning_suite%",
                20,
                40,
            ),
        )

    def test_list_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
                20,
                0,
            ),
        )

    def test_count_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
            ),
        )

    def test_task_list_queries_reuse_shared_governance_filter_normalizer(self) -> None:
        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {
            "normalize_inputs": [],
            "queries": [],
        }

        class FakeListCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeCountCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["queries"].append((str(query), tuple(params)))
                if "COUNT(*) AS n" in str(query):
                    return FakeCountCursor()
                return FakeListCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )

            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["normalize_inputs"],
            [
                " Planning_Only ",
                " Planning_Suite ",
                " Planning_Only ",
                " Planning_Suite ",
            ],
        )
        self.assertEqual(len(captured["queries"]), 2)
        list_query, list_params = captured["queries"][0]
        count_query, count_params = captured["queries"][1]
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", list_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            list_query,
        )
        self.assertEqual(
            list_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
                20,
                0,
            ),
        )
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", count_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            count_query,
        )
        self.assertEqual(
            count_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
            ),
        )

    def test_update_task_trace_steps_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.update_task_trace_steps(
                "task-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[2], "planning_only")
        self.assertEqual(rendered_params[3], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[4])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[5])), ["Task Planner Suite"])

    def test_complete_task_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.complete_task(
                "task-complete-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
                usage={"prompt_tokens": 1, "completion_tokens": 2},
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[4], "planning_only")
        self.assertEqual(rendered_params[5], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[6])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[7])), ["Task Planner Suite"])

    def test_initialize_postgres_database_ensures_task_governance_columns(self) -> None:
        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return SimpleNamespace(rowcount=0)

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = db_module.get_db_connection
        original_ensure_column = db_module._ensure_postgres_column
        original_ensure_indexes = db_module._ensure_common_indexes
        calls: list[tuple[str, str, str]] = []
        try:
            db_module.get_db_connection = lambda: FakeContextManager()
            db_module._ensure_postgres_column = (
                lambda connection, table, column, definition: calls.append(
                    (table, column, definition)
                )
            )
            db_module._ensure_common_indexes = lambda connection: None
            db_module.initialize_postgres_database()
        finally:
            db_module.get_db_connection = original_get_db_connection
            db_module._ensure_postgres_column = original_ensure_column
            db_module._ensure_common_indexes = original_ensure_indexes

        self.assertIn(("tasks", "tool_registry_profile", "TEXT"), calls)
        self.assertIn(("tasks", "tool_registry_provider_source", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_names_json", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_labels_json", "TEXT"), calls)

    def test_get_task_detail_trusts_service_governance_shape(self) -> None:
        original_get_task = task_routes_module.get_task
        original_response_builder = getattr(task_routes_module, "_build_task_response", None)
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "get_task_detail should construct governance directly from the shared row parser output"
                    )

            if original_response_builder is not None:
                task_routes_module._build_task_response = lambda _task: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                    AssertionError(
                        "get_task_detail should route governance through the shared dict-builder directly"
                    )
                )
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-service-governance-route",
                "session_id": "session-service-governance-route",
                "prompt": "service governance route task",
                "status": "completed",
                "trace_json": None,
                "usage_json": None,
                "governance": GuardedGovernanceDict(
                    profile="guarded_profile",
                    provider_source="guarded_source",
                    allowed_tool_names=["guarded_tool"],
                    allowed_tool_labels=["Guarded Tool"],
                ),
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "default",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-11T15:00:00",
                "updated_at": "2026-06-11T15:01:00",
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should trust service governance instead of reusing the shared row parser"
                    )
                )
            )
            response = task_routes_module.get_task_detail(
                "task-service-governance-route",
                current_user={"id": "user-service-governance-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )
            if original_response_builder is None:
                if hasattr(task_routes_module, "_build_task_response"):
                    delattr(task_routes_module, "_build_task_response")
            else:
                task_routes_module._build_task_response = original_response_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "guarded_profile")
        self.assertEqual(response.governance.provider_source, "guarded_source")
        self.assertEqual(response.governance.allowed_tool_names, ["guarded_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Guarded Tool"])

    def test_get_task_detail_trusts_service_governance_summary(self) -> None:
        original_get_task = task_routes_module.get_task
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-service-governance-summary-route",
                "session_id": "session-service-governance-summary-route",
                "prompt": "service governance summary route task",
                "status": "completed",
                "trace_json": None,
                "usage_json": None,
                "governance": {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                },
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "default",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-11T16:00:00",
                "updated_at": "2026-06-11T16:01:00",
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should not re-parse governance when service already provides it"
                    )
                )
            )
            response = task_routes_module.get_task_detail(
                "task-service-governance-summary-route",
                current_user={"id": "user-service-governance-summary-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "normalized_profile")
        self.assertEqual(response.governance.provider_source, "normalized_source")
        self.assertEqual(response.governance.allowed_tool_names, ["normalized_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Normalized Tool"])

    def test_task_route_module_no_longer_exposes_task_governance_summary_dict_builder(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_governance_summary_from_dict")
        )

    def test_task_route_module_no_longer_exposes_latest_seq_from_task(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_latest_seq_from_task"))

    def test_chat_persistence_service_no_longer_exposes_governance_clone_helpers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(chat_persistence_module, "_clone_task_governance_dict")
        )
        self.assertFalse(
            hasattr(chat_persistence_module, "_clone_session_governance_summary_dict")
        )

    def test_chat_persistence_service_no_longer_exposes_raw_task_trace_helpers(
        self,
    ) -> None:
        self.assertFalse(hasattr(chat_persistence_module, "get_task_trace"))
        self.assertFalse(hasattr(chat_persistence_module, "get_task_trace_delta"))
        self.assertFalse(
            hasattr(chat_persistence_module, "get_task_trace_delta_from_task")
        )

    def test_chat_persistence_service_load_trace_steps_from_trace_json_filters_and_normalizes_steps(
        self,
    ) -> None:
        original_normalizer = chat_persistence_module._normalize_trace_steps
        captured: list[object] = []
        try:
            chat_persistence_module._normalize_trace_steps = lambda steps: captured.append(  # type: ignore[attr-defined]
                steps
            ) or [
                {
                    "id": "normalized-step",
                    "type": "thought",
                    "content": "normalized",
                    "seq": 3,
                }
            ]
            payload = chat_persistence_module._load_trace_steps_from_trace_json(  # type: ignore[attr-defined]
                json.dumps(
                    [
                        {"id": "raw-step", "type": "thought", "content": "raw", "seq": 3},
                        "skip-me",
                    ]
                )
            )
        finally:
            chat_persistence_module._normalize_trace_steps = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [[{"id": "raw-step", "type": "thought", "content": "raw", "seq": 3}]],
        )
        self.assertEqual(
            payload,
            [
                {
                    "id": "normalized-step",
                    "type": "thought",
                    "content": "normalized",
                    "seq": 3,
                }
            ],
        )

    def test_chat_persistence_service_load_parsed_trace_steps_from_trace_json_reuses_shared_loader_and_trace_parser(
        self,
    ) -> None:
        original_loader = chat_persistence_module._load_trace_steps_from_trace_json  # type: ignore[attr-defined]
        original_parser = chat_persistence_module.parse_trace_steps  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._load_trace_steps_from_trace_json = lambda raw: captured.append(  # type: ignore[attr-defined]
                ("loader", raw)
            ) or [
                {
                    "id": "raw-step",
                    "type": "thought",
                    "content": "raw",
                    "seq": 4,
                }
            ]
            chat_persistence_module.parse_trace_steps = lambda steps: captured.append(  # type: ignore[attr-defined]
                ("parser", steps)
            ) or [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="parsed-step",
                    type="thought",
                    content="parsed",
                    seq=4,
                )
            ]
            payload = chat_persistence_module._load_parsed_trace_steps_from_trace_json(  # type: ignore[attr-defined]
                "guarded-trace-json"
            )
        finally:
            chat_persistence_module._load_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.parse_trace_steps = original_parser  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                ("loader", "guarded-trace-json"),
                (
                    "parser",
                    [
                        {
                            "id": "raw-step",
                            "type": "thought",
                            "content": "raw",
                            "seq": 4,
                        }
                    ],
                ),
            ],
        )
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0].id, "parsed-step")

    def test_legacy_task_governance_trace_json_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_trace_json",
            )
        )

    def test_legacy_task_governance_parsed_trace_steps_helper_is_removed(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_parsed_trace_steps",
            )
        )

    def test_legacy_task_governance_parsed_trace_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "_extract_task_governance_from_task_with_parsed_trace_steps",
            )
        )

    def test_get_task_trace_steps_reuses_shared_parsed_trace_steps_loader(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "get_task_trace_steps",
            )
        )

    def test_get_task_trace_steps_from_task_reuses_shared_parsed_trace_steps_loader(
        self,
    ) -> None:
        original_loader = chat_persistence_module._load_parsed_trace_steps_from_trace_json  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="parsed-step",
                        type="thought",
                        content="parsed",
                        seq=6,
                    )
                ]
            )
            payload = chat_persistence_module.get_task_trace_steps_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"}
            )
        finally:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]

        self.assertEqual(captured, ["guarded-trace-json"])
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0].seq, 6)

    def test_get_task_trace_steps_from_task_accepts_model_dump_row(self) -> None:
        original_loader = chat_persistence_module._load_parsed_trace_steps_from_trace_json  # type: ignore[attr-defined]

        class TaskRowPayload:
            def model_dump(self):
                return {"trace_json": "typed-trace-json"}

        captured: list[object] = []
        try:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="typed-parsed-step",
                        type="thought",
                        content="typed parsed",
                        seq=8,
                    )
                ]
            )
            payload = chat_persistence_module.get_task_trace_steps_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module._load_parsed_trace_steps_from_trace_json = original_loader  # type: ignore[attr-defined]

        self.assertEqual(captured, ["typed-trace-json"])
        self.assertEqual([step.id for step in payload], ["typed-parsed-step"])

    def test_legacy_task_trace_delta_steps_helper_is_removed(self) -> None:
        self.assertFalse(
            hasattr(
                chat_persistence_module,
                "get_task_trace_delta_steps_from_task",
            )
        )

    def test_get_task_trace_delta_snapshot_from_task_reuses_shared_task_trace_steps_helper(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-1",
                    type="thought",
                    content="first",
                    seq=1,
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-3",
                    type="thought",
                    content="third",
                    seq=3,
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-5",
                    type="thought",
                    content="fifth",
                    seq=5,
                ),
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                {"status": "completed", "trace_json": "guarded-trace-json"},
                after_seq=1,
                limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        self.assertEqual([step.seq for step in payload], [3])
        self.assertEqual(next_cursor, 3)
        self.assertTrue(has_more)
        self.assertEqual(latest_seq, 5)
        self.assertEqual(latest_step_id, "step-5")

    def test_get_task_trace_delta_snapshot_from_task_accepts_model_dump_row(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]

        class TaskRowPayload:
            def model_dump(self):
                return {"status": "running", "trace_json": "typed-trace-json"}

        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="typed-delta-step",
                    type="thought",
                    content="typed delta",
                    seq=5,
                )
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                TaskRowPayload(),
                after_seq=0,
                limit=20,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        self.assertEqual([step.id for step in payload], ["typed-delta-step"])
        self.assertEqual(next_cursor, 5)
        self.assertTrue(has_more)
        self.assertEqual(latest_seq, 5)
        self.assertEqual(latest_step_id, "typed-delta-step")

    def test_get_task_trace_delta_snapshot_from_task_sanitizes_legacy_http_json_content(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="delta-step-http-json-legacy-content",
            type="action",
            content=(
                'Tool done: Provider Status Preview: {"status":"ready",'
                '"message":"gateway token=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"}'
            ),
            seq=9,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": ["status", "message"],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            payload, next_cursor, has_more, latest_seq, latest_step_id = chat_persistence_module.get_task_trace_delta_snapshot_from_task(  # type: ignore[attr-defined]
                {"status": "completed", "trace_json": "guarded-delta-trace-json"},
                after_seq=0,
                limit=20,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]

        serialized = json.dumps([step.model_dump() for step in payload], ensure_ascii=False)
        self.assertEqual(next_cursor, 9)
        self.assertFalse(has_more)
        self.assertEqual(latest_seq, 9)
        self.assertEqual(latest_step_id, "delta-step-http-json-legacy-content")
        self.assertIn("gateway token=[redacted]", payload[0].content)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_task_route_module_no_longer_exposes_task_trace_delta_steps_helper(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "get_task_trace_delta_steps_from_task"))

    def test_stream_running_task_reconnect_reuses_task_trace_steps_from_current_task_for_terminal_step_id(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_task = task_routes_module.get_task
        original_trace_steps_loader = (
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task
        )
        original_delta_snapshot_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        try:
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_steps"))
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_delta_steps_from_task"))
            task = {
                "id": "task-reconnect-terminal-step-id",
                "session_id": "session-reconnect-terminal-step-id",
                "status": "completed",
                "usage_json": json.dumps({"prompt_tokens": 3, "completion_tokens": 5}),
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.get_settings = lambda: SimpleNamespace(
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.5,
                stream_reconnect_heartbeat_interval_sec=1.0,
            )
            task_routes_module.get_task = lambda _task_id, _user_id: dict(task)
            task_routes_module.get_task_trace_steps = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "terminal reconnect stream should reuse get_task_trace_steps_from_task(task) instead of refetching full trace by task id"
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "terminal reconnect stream should reuse get_task_trace_delta_snapshot_from_task(task) instead of reloading full steps after delta polling"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: (
                    [],
                    after_seq,
                    False,
                    7,
                    "fallback::guarded-trace-json",
                )
            )

            async def collect_events() -> list[str]:
                events: list[str] = []
                async for event in task_routes_module.stream_running_task_reconnect(
                    "task-reconnect-terminal-step-id",
                    "user-reconnect-terminal-step-id",
                ):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_task = original_get_task
            if hasattr(task_routes_module, "get_task_trace_steps"):
                delattr(task_routes_module, "get_task_trace_steps")
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (
                original_trace_steps_loader
            )
            if original_delta_snapshot_loader is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_loader  # type: ignore[attr-defined]

        self.assertEqual(len(events), 2)
        self.assertIn('"status": "completed"', events[-1])
        self.assertIn(
            '"step_id": "fallback::guarded-trace-json"',
            events[-1],
        )

    def test_chat_persistence_service_parse_usage_json_blob_accepts_only_dict_payloads(
        self,
    ) -> None:
        payload = chat_persistence_module._parse_usage_json_blob(  # type: ignore[attr-defined]
            json.dumps(
                {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "cost_estimate": 0.12,
                }
            )
        )
        self.assertEqual(
            payload,
            {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost_estimate": 0.12,
            },
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob(json.dumps(["skip"]))  # type: ignore[attr-defined]
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob("not-json")  # type: ignore[attr-defined]
        )
        self.assertIsNone(
            chat_persistence_module._parse_usage_json_blob(None)  # type: ignore[attr-defined]
        )

    def test_get_task_usage_from_task_reuses_shared_usage_json_parser(self) -> None:
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw)
                or {
                    "prompt_tokens": 8,
                    "completion_tokens": 13,
                    "cost_estimate": 0.03,
                }
            )
            payload = chat_persistence_module.get_task_usage_from_task(  # type: ignore[attr-defined]
                {"usage_json": "usage-json-guarded"}
            )
        finally:
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-guarded"])
        self.assertEqual(
            payload,
            {
                "prompt_tokens": 8,
                "completion_tokens": 13,
                "cost_estimate": 0.03,
            },
        )

    def test_get_task_usage_from_task_accepts_model_dump_row(self) -> None:
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []

        class TaskRowPayload:
            def model_dump(self):
                return {"usage_json": "typed-usage-json"}

        try:
            chat_persistence_module._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda raw: captured.append(raw) or {"total_tokens": 21}
            )
            payload = chat_persistence_module.get_task_usage_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["typed-usage-json"])
        self.assertEqual(payload, {"total_tokens": 21})

    def test_get_task_trace_preview_summary_reuses_shared_trace_export_summary_helper(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_export_helper = getattr(
            chat_persistence_module,
            "get_task_trace_export_summary_from_task",
            None,
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "trace preview summary should reuse get_task_trace_export_summary_from_task(task) instead of touching parsed trace steps directly"
                )
            )
            chat_persistence_module.get_task_trace_export_summary_from_task = lambda _task: {  # type: ignore[attr-defined]
                "steps": [
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-1",
                        type="thought",
                        content="planner note",
                        seq=1,
                    ),
                    chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-2",
                        type="tool_result",
                        content="result body",
                        seq=2,
                    ),
                ],
                "step_count": 2,
                "rag_hit_count": 2,
                "rag_knowledge_base_ids": ["kb-shared"],
                "rag_chunks": [
                    {
                        "step_id": "step-1",
                        "knowledge_base_id": "kb-shared",
                        "content": "chunk-1",
                    }
                ],
            }
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            if original_export_helper is None:
                if hasattr(
                    chat_persistence_module,
                    "get_task_trace_export_summary_from_task",
                ):
                    delattr(
                        chat_persistence_module,
                        "get_task_trace_export_summary_from_task",
                    )
            else:
                chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["trace_step_count"], 2)
        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(
            payload["trace_preview"],
            [
                {
                    "id": "step-2",
                    "seq": 2,
                    "type": "tool_result",
                    "title": "tool result",
                    "content_excerpt": "result body",
                }
            ],
        )

    def test_get_task_trace_preview_summary_coerces_trace_step_dicts(self) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-dict",
                            "type": "tool_result",
                            "content": "preview dict body",
                            "seq": 12,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"],
            [
                {
                    "id": "step-preview-dict",
                    "seq": 12,
                    "type": "tool_result",
                    "title": "tool result",
                    "content_excerpt": "preview dict body",
                }
            ],
        )

    def test_get_task_trace_preview_summary_prefers_inferred_result_summary_from_preview_only_action_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool",
                            "type": "action",
                            "content": "Tool done: Task Planner",
                            "seq": 21,
                            "meta": {
                                "tool": {
                                    "name": "task_plan",
                                    "label": "Task Planner",
                                    "status": "done",
                                    "output_preview": {
                                        "plan": "Analyze request -> synthesize answer",
                                        "prompt_preview": "trace preview prompt",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Planned steps - Analyze request -> synthesize answer.", excerpt)
        self.assertNotIn("Tool done: Task Planner", excerpt)
        self.assertIn('Preview: {"plan":"Analyze request -> synthesize answer","prompt_preview":"trace preview prompt"}', excerpt)
        self.assertIn("Analyze request -> synthesize answer", excerpt)
        self.assertIn("trace preview prompt", excerpt)

    def test_get_task_trace_preview_summary_prefers_output_preview_without_leaking_raw_output(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-safe",
                            "type": "action",
                            "content": "Tool done: Hot Retrieval",
                            "seq": 22,
                            "meta": {
                                "tool": {
                                    "name": "task_retrieve_hot",
                                    "label": "Hot Retrieval",
                                    "status": "done",
                                    "output": {
                                        "tool_kind": "hot_knowledge_retrieval",
                                        "knowledge_base_id": "demo-kb",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                    "output_preview": {
                                        "tool_kind": "hot_knowledge_retrieval",
                                        "knowledge_base_id": "demo-kb",
                                        "hit_count": 2,
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn('"knowledge_base_id":"demo-kb"', excerpt)
        self.assertIn('"hit_count":2', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_appends_safe_tool_output_when_effective_result_output_keys_present(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 23,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Preview: {"documents_total":2}', excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)

    def test_get_task_trace_preview_summary_filters_safe_tool_output_to_effective_result_output_keys_subset(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy-filtered",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 24,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_accepts_tuple_effective_result_output_keys(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-output-policy-tuple",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 25,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "effective_result_output_keys": (
                                        "documents_total",
                                        "request_id",
                                    ),
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-1",
                                        "raw_documents": [{"id": "doc-1"}],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Retrieved 2 documents (request id req-1).", excerpt)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', excerpt)
        self.assertNotIn("raw_documents", excerpt)

    def test_get_task_trace_preview_summary_appends_tuple_tool_output_preview_for_action_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-tool-tuple-preview",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 26,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "status": "done",
                                    "output_preview": (
                                        "alpha",
                                        "beta",
                                    ),
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn('Preview: ["alpha","beta"]', excerpt)

    def test_get_task_trace_preview_summary_uses_productized_tool_title_for_real_tool_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-provider-search",
                            "type": "action",
                            "content": "Tool done: Provider Search",
                            "seq": 23,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "semantic_kind": "provider_search",
                                    "semantic_family": "knowledge_retrieval",
                                    "status": "done",
                                    "output_preview": {
                                        "hit_count": 2,
                                        "knowledge_base_id": "demo-kb",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Provider Search [provider_search · knowledge_retrieval]",
        )

    def test_get_task_trace_preview_summary_uses_productized_title_for_rag_followup_steps(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-rag-followup",
                            "type": "thought",
                            "content": "Provider Search returned snippets.",
                            "seq": 24,
                            "meta": {
                                "step_type": "rag_retrieval",
                                "rag": {
                                    "chunks": ["alpha", "beta"],
                                    "knowledge_base_id": "demo-kb",
                                },
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 2,
                    "rag_knowledge_base_ids": ["demo-kb"],
                    "rag_chunks": [
                        {
                            "step_id": "step-rag-followup",
                            "knowledge_base_id": "demo-kb",
                            "content": "alpha",
                        },
                        {
                            "step_id": "step-rag-followup",
                            "knowledge_base_id": "demo-kb",
                            "content": "beta",
                        },
                    ],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Knowledge Retrieval Snippets",
        )

    def test_get_task_trace_preview_summary_infers_calc_summary_from_structural_kind_output_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 27,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "result": 7,
                                    },
                                    "output": {
                                        "kind": "provider_calc",
                                        "result": 7,
                                        "request_id": "req-calc-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Preview: {"result":7}', excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)

    def test_get_task_trace_preview_summary_uses_file_backed_real_calc_summary(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-file-backed-provider-math",
                            "type": "action",
                            "content": "Tool done: Provider Calculator",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "provider_math",
                                    "label": "Provider Calculator",
                                    "kind": "provider_calc",
                                    "semantic_kind": "provider_math",
                                    "semantic_family": "local_calculator",
                                    "execution_kind": "http_json",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "expression",
                                        "result",
                                        "request_id",
                                        "source",
                                        "profile",
                                    ],
                                    "output_preview": {
                                        "expression": "8/4",
                                        "result": 2,
                                        "source": "calculator_suite",
                                        "profile": "calculator_only",
                                    },
                                    "output": {
                                        "expression": "8/4",
                                        "result": 2,
                                        "request_id": "req-calc-1",
                                        "source": "calculator_suite",
                                        "profile": "calculator_only",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        preview = payload["trace_preview"][0]
        self.assertEqual(
            preview["title"],
            "Provider Calculator [provider_math · local_calculator]",
        )
        excerpt = preview["content_excerpt"]
        self.assertIn("Calculated 8/4 = 2 (request id req-calc-1).", excerpt)
        self.assertIn(
            'Output: {"expression":"8/4","result":2,"request_id":"req-calc-1"',
            excerpt,
        )
        self.assertNotIn("Tool done: Provider Calculator", excerpt)

    def test_get_task_trace_preview_summary_infers_calc_summary_from_json_string_safe_output_without_preview(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math-json-string-safe-output",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Math [calculator]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)
        self.assertNotIn("secret", excerpt)

    def test_get_task_trace_preview_summary_infers_calc_summary_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-math-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Math",
                            "seq": 28,
                            "meta": {
                                "tool": {
                                    "name": "hosted_math",
                                    "label": "Hosted Math",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "result",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "result": 7,
                                    },
                                    "output": {
                                        "result": 7,
                                        "request_id": "req-calc-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Math [calculator]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn("Calculated result = 7 (request id req-calc-1).", excerpt)
        self.assertIn('Preview: {"result":7}', excerpt)
        self.assertIn('Output: {"result":7,"request_id":"req-calc-1"}', excerpt)
        self.assertNotIn("Tool done: Hosted Math", excerpt)

    def test_get_task_trace_preview_summary_infers_planner_title_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-planner-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Planner",
                            "seq": 29,
                            "meta": {
                                "tool": {
                                    "name": "hosted_planner",
                                    "label": "Hosted Planner",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "steps",
                                    ],
                                    "output_preview": {
                                        "steps": [
                                            "Analyze request",
                                            "Synthesize final answer",
                                        ],
                                    },
                                    "output": {
                                        "steps": [
                                            "Analyze request",
                                            "Synthesize final answer",
                                        ],
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Planner [planner]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn(
            "Planned steps - Analyze request -> Synthesize final answer.",
            excerpt,
        )
        self.assertNotIn("Tool done: Hosted Planner", excerpt)

    def test_get_task_trace_preview_summary_infers_retrieval_title_for_name_only_real_tool_without_semantic_family(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-hosted-search-name-only",
                            "type": "action",
                            "content": "Tool done: Hosted Search",
                            "seq": 30,
                            "meta": {
                                "tool": {
                                    "name": "hosted_search",
                                    "label": "Hosted Search",
                                    "status": "done",
                                    "effective_result_output_keys": [
                                        "documents_total",
                                        "request_id",
                                    ],
                                    "output_preview": {
                                        "documents_total": 2,
                                    },
                                    "output": {
                                        "documents_total": 2,
                                        "request_id": "req-search-1",
                                    },
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace_preview"][0]["title"],
            "Hosted Search [retrieval]",
        )
        excerpt = payload["trace_preview"][0]["content_excerpt"]
        self.assertIn(
            "Retrieved 2 documents (request id req-search-1).",
            excerpt,
        )
        self.assertIn('Preview: {"documents_total":2}', excerpt)
        self.assertIn(
            'Output: {"documents_total":2,"request_id":"req-search-1"}',
            excerpt,
        )
        self.assertNotIn("Tool done: Hosted Search", excerpt)

    def test_get_task_trace_preview_summary_redacts_http_json_tool_label_title_diagnostics(
        self,
    ) -> None:
        original_export_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-preview-http-json-tool-label-diagnostic",
                            "type": "action",
                            "content": (
                                'Tool done: Provider Status Preview: {"message":"ok"}'
                            ),
                            "seq": 31,
                            "meta": {
                                "tool": {
                                    "name": "provider_status",
                                    "label": (
                                        "Provider token=hidden "
                                        "https://provider.example/cb?"
                                        "access_token=secret-token"
                                    ),
                                    "execution_kind": "http_json",
                                    "status": "done",
                                    "output_preview": {"message": "ok"},
                                }
                            },
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_preview_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-trace-json"},
                preview_limit=1,
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_export_helper  # type: ignore[attr-defined]

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("[redacted]", payload["trace_preview"][0]["title"])
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_rag_export_summary_reuses_shared_trace_steps_shape(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": [" chunk-1 ", "", "chunk-2"],
                            "knowledge_base_id": " kb-1 ",
                        }
                    },
                ),
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-2",
                    type="tool_result",
                    content="result body",
                    seq=2,
                    meta={
                        "rag": {
                            "chunks": ["chunk-3"],
                            "knowledge_base_id": "kb-1",
                        }
                    },
                ),
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 3)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
                {
                    "step_id": "step-2",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-3",
                },
            ],
        )

    def test_get_trace_rag_export_summary_accepts_tuple_chunks(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                    id="step-tuple-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta={
                        "rag": {
                            "chunks": (" chunk-1 ", "", "chunk-2"),
                            "knowledge_base_id": " kb-1 ",
                        }
                    },
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-tuple-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-tuple-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
            ],
        )

    def test_get_trace_rag_export_summary_accepts_wrapped_chunks(self) -> None:
        payload = chat_persistence_module.get_trace_rag_export_summary(  # type: ignore[attr-defined]
            [
                SimpleNamespace(
                    id="step-wrapped-rag-1",
                    type="thought",
                    content="planner note",
                    seq=1,
                    meta=SimpleNamespace(
                        rag={
                            "chunks": UserList(
                                [
                                    UserString(" chunk-1 "),
                                    UserString(""),
                                    UserString("chunk-2"),
                                ]
                            ),
                            "knowledge_base_id": UserString(" kb-1 "),
                        }
                    ),
                )
            ]
        )

        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-1"])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "step-wrapped-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-1",
                },
                {
                    "step_id": "step-wrapped-rag-1",
                    "knowledge_base_id": "kb-1",
                    "content": "chunk-2",
                },
            ],
        )

    def test_get_task_trace_export_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        fake_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-1",
            type="thought",
            content="export summary body",
            seq=3,
        )
        captured: list[list[object]] = []
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                fake_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda trace_steps: captured.append(  # type: ignore[attr-defined]
                trace_steps
            ) or {
                "rag_hit_count": 2,
                "rag_knowledge_base_ids": ["kb-shared"],
                "rag_chunks": [
                    {
                        "step_id": "export-step-1",
                        "knowledge_base_id": "kb-shared",
                        "content": "chunk-shared",
                    }
                ],
            }
            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, [[fake_step]])
        self.assertEqual(payload["step_count"], 1)
        self.assertEqual(payload["rag_hit_count"], 2)
        self.assertEqual(payload["rag_knowledge_base_ids"], ["kb-shared"])
        self.assertEqual(payload["steps"], [fake_step])
        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "export-step-1",
                    "knowledge_base_id": "kb-shared",
                    "content": "chunk-shared",
                }
            ],
        )

    def test_get_task_trace_export_summary_sanitizes_http_json_tool_meta_for_json_export(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-http-json-sensitive",
            type="action",
            content="Tool done: Provider Status",
            seq=5,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "input": {
                        "query": "status token=hidden",
                        "access_token": "hidden",
                        "headers": {
                            "Authorization": "Bearer hidden",
                        },
                    },
                    "effective_result_preview_keys": ["status", "message"],
                    "effective_result_output_keys": [
                        "status",
                        "message",
                        "request_id",
                    ],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                    "output": {
                        "status": "ready",
                        "message": "secret=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            }

            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        exported_step = payload["steps"][0]
        tool_meta = exported_step.meta.tool  # type: ignore[union-attr]

        self.assertEqual(
            tool_meta["input"],
            {
                "query": "status token=[redacted]",
                "access_token": "[redacted]",
                "headers": {
                    "Authorization": "[redacted]",
                },
            },
        )
        self.assertEqual(
            tool_meta["output_preview"],
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        self.assertEqual(
            tool_meta["output"],
            {
                "status": "ready",
                "message": "secret=[redacted]",
            },
        )
        exported_json = json.dumps(exported_step.model_dump(), ensure_ascii=False)
        self.assertNotIn('"access_token": "hidden"', exported_json)
        self.assertNotIn("Bearer hidden", exported_json)
        self.assertNotIn("secret-token", exported_json)
        self.assertNotIn("token=hidden", exported_json)
        self.assertNotIn("secret=hidden", exported_json)

    def test_get_task_trace_export_summary_sanitizes_legacy_http_json_content_for_json_export(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]
        raw_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-http-json-legacy-content",
            type="action",
            content=(
                'Tool done: Provider Status Preview: {"status":"ready",'
                '"message":"gateway token=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"} Output: {"status":"ready",'
                '"message":"secret=hidden","access_token":"hidden",'
                '"request_id":"Bearer secret-token"}'
            ),
            seq=6,
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_preview_keys": ["status", "message"],
                    "effective_result_output_keys": ["status", "message"],
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                    "output": {
                        "status": "ready",
                        "message": "secret=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                raw_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 0,
                "rag_knowledge_base_ids": [],
                "rag_chunks": [],
            }

            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-legacy-content"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        exported_step = payload["steps"][0]
        exported_json = json.dumps(exported_step.model_dump(), ensure_ascii=False)

        self.assertIn("Provider Status: ", exported_step.content)
        self.assertIn("gateway token=[redacted]", exported_step.content)
        self.assertIn("secret=[redacted]", exported_step.content)
        self.assertNotIn("access_token", exported_json)
        self.assertNotIn("token=hidden", exported_json)
        self.assertNotIn("secret=hidden", exported_json)
        self.assertNotIn("Bearer", exported_json)
        self.assertNotIn("secret-token", exported_json)

    def test_get_task_trace_export_summary_from_task_coerces_model_rag_chunks(
        self,
    ) -> None:
        original_loader = chat_persistence_module.get_task_trace_steps_from_task  # type: ignore[attr-defined]
        original_rag_helper = chat_persistence_module.get_trace_rag_export_summary  # type: ignore[attr-defined]

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        fake_step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="export-step-model-rag",
            type="thought",
            content="export summary body",
            seq=4,
        )
        try:
            chat_persistence_module.get_task_trace_steps_from_task = lambda _task: [  # type: ignore[attr-defined]
                fake_step
            ]
            chat_persistence_module.get_trace_rag_export_summary = lambda _trace_steps: {  # type: ignore[attr-defined]
                "rag_hit_count": 1,
                "rag_knowledge_base_ids": ["kb-model"],
                "rag_chunks": (
                    ResponseReadyChunk(
                        {
                            "step_id": "export-step-model-rag",
                            "knowledge_base_id": "kb-model",
                            "content": "chunk-model",
                        }
                    ),
                ),
            }
            payload = chat_persistence_module.get_task_trace_export_summary_from_task(  # type: ignore[attr-defined]
                {"trace_json": "guarded-export-trace-json"}
            )
        finally:
            chat_persistence_module.get_task_trace_steps_from_task = original_loader  # type: ignore[attr-defined]
            chat_persistence_module.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["rag_chunks"],
            [
                {
                    "step_id": "export-step-model-rag",
                    "knowledge_base_id": "kb-model",
                    "content": "chunk-model",
                }
            ],
        )

    def test_get_task_export_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_usage_helper = chat_persistence_module.get_task_usage_from_task
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        task = {
            "id": "task-export-summary",
            "session_id": "session-export-summary",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "usage_json": "usage-json-guarded",
            "governance": {"profile": "shared_profile"},
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"trace:{raw_task.get('id')}")
                or {
                    "steps": [
                        chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                            id="step-1",
                            type="thought",
                            content="trace body",
                            seq=1,
                        )
                    ],
                    "step_count": 1,
                    "rag_hit_count": 2,
                    "rag_knowledge_base_ids": ["kb-shared"],
                    "rag_chunks": [
                        {
                            "step_id": "step-1",
                            "knowledge_base_id": "kb-shared",
                            "content": "chunk-shared",
                        }
                    ],
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"usage:{raw_task.get('id')}")
                or {"usage_task_id": str(raw_task.get("id"))}
            )
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 23
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "trace:task-export-summary",
                "normalize:completed",
                "label:completed",
                "rank:completed",
                "usage:task-export-summary",
            ],
        )
        self.assertEqual(payload["usage"], {"usage_task_id": "task-export-summary"})
        self.assertEqual(
            payload["task"],
            {
                "id": "task-export-summary",
                "session_id": "session-export-summary",
                "prompt": "export summary prompt",
                "status": "completed",
                "status_normalized": "normalized::completed",
                "status_label": "label::completed",
                "status_rank": 23,
                "created_at": "2026-06-22T13:00:00",
                "updated_at": "2026-06-22T13:05:00",
            },
        )
        self.assertEqual(payload["trace"]["governance"], {"profile": "shared_profile"})
        self.assertEqual(payload["trace"]["step_count"], 1)
        self.assertEqual(payload["trace"]["rag_hit_count"], 2)
        self.assertEqual(payload["trace"]["rag_knowledge_base_ids"], ["kb-shared"])
        self.assertEqual(payload["trace"]["rag_chunks"], [{"step_id": "step-1", "knowledge_base_id": "kb-shared", "content": "chunk-shared"}])

    def test_get_task_export_summary_from_task_accepts_model_dump_row(self) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_usage_helper = chat_persistence_module.get_task_usage_from_task

        class TaskRowPayload:
            def model_dump(self):
                return {
                    "id": "task-export-model-row",
                    "session_id": "session-export-model-row",
                    "prompt": "export model row",
                    "status": "completed",
                    "created_at": "2026-07-02T15:40:00",
                    "updated_at": "2026-07-02T15:41:00",
                    "governance": {"profile": "planning_only"},
                }

        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            chat_persistence_module.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda _task: {"total_tokens": 12}
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                TaskRowPayload()
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(payload["task"]["id"], "task-export-model-row")
        self.assertEqual(payload["usage"], {"total_tokens": 12})
        self.assertEqual(payload["trace"]["governance"], {"profile": "planning_only"})

    def test_get_task_export_summary_from_task_coerces_model_rag_chunks(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )

        class ResponseReadyChunk:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-rag",
            "session_id": "session-export-summary-model-rag",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": None,
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: {
                    "steps": [],
                    "step_count": 0,
                    "rag_hit_count": 1,
                    "rag_knowledge_base_ids": ["kb-model"],
                    "rag_chunks": [
                        ResponseReadyChunk(
                            {
                                "step_id": "step-model-rag",
                                "knowledge_base_id": "kb-model",
                                "content": "chunk-model",
                            }
                        )
                    ],
                }
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(
            payload["trace"]["rag_chunks"],
            [
                {
                    "step_id": "step-model-rag",
                    "knowledge_base_id": "kb-model",
                    "content": "chunk-model",
                }
            ],
        )

    def test_get_task_export_summary_from_task_coerces_governance_models(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-governance",
            "session_id": "session-export-summary-model-governance",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": ResponseReadyGovernance(
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ),
        }
        payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
            task
        )

        self.assertIsInstance(payload["trace"]["governance"], dict)
        self.assertIsNot(payload["trace"]["governance"], task["governance"])
        self.assertEqual(payload["trace"]["governance"]["profile"], "planning_only")

    def test_get_task_export_summary_from_task_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        task = {
            "id": "task-export-summary-model-governance-source-context",
            "session_id": "session-export-summary-model-governance-source-context",
            "prompt": "export summary prompt source context",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
            "governance": ResponseReadyGovernance(
                {
                    "profile": "calculator_only",
                    "provider_source": "calculator_suite",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["calc_eval"],
                }
            ),
        }
        payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
            task
        )

        self.assertEqual(
            payload["trace"]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_get_task_export_summary_from_task_coerces_trace_step_dicts(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        task = {
            "id": "task-export-summary-dict-steps",
            "session_id": "session-export-summary-dict-steps",
            "prompt": "export summary prompt",
            "status": "completed",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: {
                    "steps": [
                        {
                            "id": "step-export-dict",
                            "type": "thought",
                            "content": "export dict body",
                            "seq": 11,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_export_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["trace"]["steps"]), 1)
        self.assertIsInstance(
            payload["trace"]["steps"][0],
            chat_persistence_module.TraceStep,  # type: ignore[attr-defined]
        )
        self.assertEqual(payload["trace"]["steps"][0].id, "step-export-dict")
        self.assertEqual(payload["trace"]["steps"][0].seq, 11)

    def test_get_task_trace_response_summary_from_task_reuses_shared_helpers(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        original_normalize = chat_persistence_module.normalize_task_status
        original_label = chat_persistence_module.task_status_label
        original_rank = chat_persistence_module.task_status_rank
        captured: list[str] = []
        task = {
            "id": "task-trace-response-summary",
            "status": "running",
            "trace_json": "trace-json-shared",
        }
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: captured.append(f"trace:{raw_task.get('id')}")
                or {
                    "steps": [
                        chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                            id="trace-step-1",
                            type="thought",
                            content="trace response body",
                            seq=5,
                        )
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            chat_persistence_module.normalize_task_status = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"normalize:{status}")
                or f"normalized::{status}"
            )
            chat_persistence_module.task_status_label = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"label:{status}")
                or f"label::{status}"
            )
            chat_persistence_module.task_status_rank = (  # type: ignore[attr-defined]
                lambda status: captured.append(f"rank:{status}") or 17
            )
            payload = chat_persistence_module.get_task_trace_response_summary_from_task(  # type: ignore[attr-defined]
                task
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]
            chat_persistence_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            chat_persistence_module.task_status_label = original_label  # type: ignore[attr-defined]
            chat_persistence_module.task_status_rank = original_rank  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                "trace:task-trace-response-summary",
                "normalize:running",
                "label:running",
                "rank:running",
            ],
        )
        self.assertEqual(
            [
                step.id
                for step in payload["steps"]
                if isinstance(step, chat_persistence_module.TraceStep)  # type: ignore[attr-defined]
            ],
            ["trace-step-1"],
        )
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["status_normalized"], "normalized::running")
        self.assertEqual(payload["status_label"], "label::running")
        self.assertEqual(payload["status_rank"], 17)

    def test_get_task_trace_response_summary_from_task_coerces_trace_step_dicts(
        self,
    ) -> None:
        original_trace_helper = (
            chat_persistence_module.get_task_trace_export_summary_from_task
        )
        try:
            chat_persistence_module.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [
                        {
                            "id": "step-response-dict",
                            "type": "thought",
                            "content": "response dict body",
                            "seq": 13,
                        }
                    ],
                    "step_count": 1,
                    "rag_hit_count": 0,
                    "rag_knowledge_base_ids": [],
                    "rag_chunks": [],
                }
            )
            payload = chat_persistence_module.get_task_trace_response_summary_from_task(  # type: ignore[attr-defined]
                {
                    "id": "task-trace-response-dict",
                    "status": "running",
                }
            )
        finally:
            chat_persistence_module.get_task_trace_export_summary_from_task = original_trace_helper  # type: ignore[attr-defined]

        self.assertEqual(len(payload["steps"]), 1)
        self.assertIsInstance(
            payload["steps"][0],
            chat_persistence_module.TraceStep,  # type: ignore[attr-defined]
        )
        self.assertEqual(payload["steps"][0].id, "step-response-dict")
        self.assertEqual(payload["steps"][0].seq, 13)

    def test_get_task_trace_delta_response_summary_from_task_reuses_shared_snapshot_helper(
        self,
    ) -> None:
        original_delta_snapshot_helper = getattr(
            chat_persistence_module,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        captured: list[tuple[str, int, int]] = []
        task = {
            "id": "task-trace-delta-response-summary",
            "trace_json": "trace-delta-response-summary",
        }
        try:
            chat_persistence_module.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda raw_task, after_seq=0, limit=200: captured.append(
                    (str(raw_task.get("id", "")), after_seq, limit)
                )
                or (
                    [
                        chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
                            id="delta-step-1",
                            type="thought",
                            content="delta body",
                            seq=8,
                        )
                    ],
                    8,
                    False,
                    11,
                    "delta-step-1",
                )
            )
            payload = chat_persistence_module.get_task_trace_delta_response_summary_from_task(  # type: ignore[attr-defined]
                task,
                after_seq=3,
                limit=50,
            )
        finally:
            if original_delta_snapshot_helper is None:
                if hasattr(
                    chat_persistence_module,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        chat_persistence_module,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                chat_persistence_module.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [("task-trace-delta-response-summary", 3, 50)],
        )
        self.assertEqual(
            [
                step.id
                for step in payload["steps"]
                if isinstance(step, chat_persistence_module.TraceStep)  # type: ignore[attr-defined]
            ],
            ["delta-step-1"],
        )
        self.assertEqual(payload["next_cursor"], 8)
        self.assertFalse(payload["has_more"])
        self.assertEqual(payload["lag_seq"], 3)
        self.assertFalse(payload["dropped"])

    def test_get_tasks_usage_dashboard_response_summary_plain_clones_governance_dicts(
        self,
    ) -> None:
        class GuardedTopTaskGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_tasks_usage_dashboard_response_summary should plain-clone top-task governance dicts before outward model validation"
                )

        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_tasks_usage_dashboard_response_summary should plain-clone session governance dicts before outward model validation"
                )

        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {"tasks_total": 1},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-summary",
                        "session_title": "Usage Summary Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-22T20:00:00",
                        "governance": GuardedSessionGovernanceDict(
                            profiles=["planning_only"],
                            provider_sources=["planning_suite"],
                            allowed_tool_names=["task_plan"],
                            allowed_tool_labels=["Task Planner Suite"],
                        ),
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-summary",
                        "session_id": "session-usage-summary",
                        "session_title": "Usage Summary Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "source_kind": "provider",
                        "governance": GuardedTopTaskGovernanceDict(
                            profile="planning_only",
                            provider_source="planning_suite",
                            allowed_tool_names=["task_plan"],
                            allowed_tool_labels=["Task Planner Suite"],
                        ),
                    }
                ],
            }
        )

        self.assertIsInstance(payload["by_session"][0]["governance"], dict)
        self.assertNotIsInstance(
            payload["by_session"][0]["governance"],
            GuardedSessionGovernanceDict,
        )
        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )
        self.assertIsInstance(payload["top_tasks"][0]["governance"], dict)
        self.assertNotIsInstance(
            payload["top_tasks"][0]["governance"],
            GuardedTopTaskGovernanceDict,
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_response_summary_coerces_response_ready_models(
        self,
    ) -> None:
        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": ResponseReadyBlock(
                    {
                        "tasks_total": 2,
                        "tasks_with_usage": 2,
                    }
                ),
                "trend": [
                    ResponseReadyBlock(
                        {
                            "date": "2026-06-22",
                            "tasks_with_usage": 2,
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                        }
                    )
                ],
                "by_session": [
                    ResponseReadyBlock(
                        {
                            "session_id": "session-ready-model",
                            "session_title": "Ready Model Session",
                            "tasks_with_usage": 2,
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                            "last_task_at": "2026-06-22T20:00:00",
                            "governance": {
                                "profiles": ["planning_only"],
                                "provider_sources": ["planning_suite"],
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    )
                ],
                "top_tasks": [
                    ResponseReadyBlock(
                        {
                            "task_id": "task-ready-model",
                            "session_id": "session-ready-model",
                            "session_title": "Ready Model Session",
                            "prompt_excerpt": "ready model task",
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                            "created_at": "2026-06-22T20:00:00",
                            "updated_at": "2026-06-22T20:05:00",
                            "source_kind": "provider",
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    )
                ],
            }
        )

        self.assertEqual(
            payload["summary"],
            {
                "tasks_total": 2,
                "tasks_with_usage": 2,
            },
        )
        self.assertEqual(payload["trend"][0]["date"], "2026-06-22")
        self.assertEqual(payload["by_session"][0]["session_id"], "session-ready-model")
        self.assertEqual(payload["by_session"][0]["total_tokens"], 123)
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-ready-model")
        self.assertEqual(payload["top_tasks"][0]["source_kind"], "provider")
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["profile"],
            "planning_only",
        )

    def test_get_tasks_usage_dashboard_response_summary_normalizes_plain_wrapped_rows(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {
                    "tasks_total": 2,
                    "source_tasks_provider": 1,
                },
                "trend": [
                    {
                        "date": UserString("2026-06-22"),
                        "tasks_with_usage": 2,
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                    }
                ],
                "by_session": [
                    {
                        "session_id": UserString("session-plain-wrapped"),
                        "session_title": UserString("Plain Wrapped Session"),
                        "tasks_with_usage": 2,
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                        "last_task_at": UserString("2026-06-22T20:00:00"),
                        "governance": {
                            "profiles": [UserString("planning_only")],
                            "provider_sources": [UserString("planning_suite")],
                            "allowed_tool_names": [UserString("task_plan")],
                            "allowed_tool_labels": [UserString("Task Planner Suite")],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": UserString("task-plain-wrapped"),
                        "session_id": UserString("session-plain-wrapped"),
                        "session_title": UserString("Plain Wrapped Session"),
                        "prompt_excerpt": UserString("plain wrapped task"),
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                        "created_at": UserString("2026-06-22T20:00:00"),
                        "updated_at": UserString("2026-06-22T20:05:00"),
                        "source_kind": UserString("provider"),
                        "governance": {
                            "profile": UserString("planning_only"),
                            "provider_source": UserString("planning_suite"),
                            "allowed_tool_names": [UserString("task_plan")],
                            "allowed_tool_labels": [UserString("Task Planner Suite")],
                        },
                    }
                ],
            }
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["trend"][0]["date"], "2026-06-22")
        self.assertEqual(payload["by_session"][0]["session_title"], "Plain Wrapped Session")
        self.assertEqual(payload["by_session"][0]["governance"]["profiles"], ["planning_only"])
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-plain-wrapped")
        self.assertEqual(payload["top_tasks"][0]["source_kind"], "provider")
        self.assertNotIn("UserString", serialized)

    def test_get_tasks_usage_dashboard_response_summary_coerces_governance_models(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-governance-model",
                        "tasks_with_usage": 1,
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "governance": session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-governance-model",
                        "session_id": "session-governance-model",
                        "prompt_excerpt": "governance model",
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "governance": task_governance,
                    }
                ],
            }
        )

        self.assertIsInstance(payload["by_session"][0]["governance"], dict)
        self.assertIsNot(payload["by_session"][0]["governance"], session_governance)
        self.assertEqual(
            payload["by_session"][0]["governance"]["profiles"],
            ["planning_only"],
        )
        self.assertIsInstance(payload["top_tasks"][0]["governance"], dict)
        self.assertIsNot(payload["top_tasks"][0]["governance"], task_governance)
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["profile"],
            "planning_only",
        )

    def test_get_tasks_usage_dashboard_response_summary_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-governance-source-model",
                        "tasks_with_usage": 1,
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "governance": session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-governance-source-model",
                        "session_id": "session-governance-source-model",
                        "prompt_excerpt": "governance source model",
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "governance": task_governance,
                    }
                ],
            }
        )

        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_task_route_module_does_not_expose_dead_clone_builders(self) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_governance_summary_from_clone")
        )
        self.assertFalse(
            hasattr(
                task_routes_module,
                "_build_task_usage_session_governance_summary_from_clone",
            )
        )

    def test_task_route_module_does_not_expose_dead_local_clone_helpers(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_clone_task_governance"))
        self.assertFalse(hasattr(task_routes_module, "_clone_session_governance_summary"))

    def test_task_route_module_does_not_expose_dead_trace_json_governance_collector(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_task_governance_from_trace_json"))

    def test_task_route_module_does_not_expose_dead_task_response_builder(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_build_task_response"))

    def test_task_response_route_coercion_redacts_http_json_trace_json(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="task-response-route-http-json-trace-json"
        )

        payload = task_routes_module._coerce_task_response_summary(  # type: ignore[attr-defined]
            {
                "id": "task-response-route-trace-json-safe",
                "session_id": "session-response-route-trace-json-safe",
                "prompt": "response route trace json safe",
                "status": "completed",
                "trace_json": json.dumps([raw_step], ensure_ascii=False),
                "usage_json": None,
                "created_at": "2026-07-20T10:00:00",
                "updated_at": "2026-07-20T10:01:00",
            }
        )

        serialized = str(payload["trace_json"])
        parsed = json.loads(serialized)

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("gateway token=[redacted]", serialized)
        self.assertIn("preview token=[redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)
        self.assertEqual(parsed[0]["id"], "task-response-route-http-json-trace-json")

    def test_task_route_module_does_not_expose_dead_status_meta_helper(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_with_status_meta"))

    def test_task_route_module_does_not_expose_dead_task_governance_collector(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_task_governance_from_task"))

    def test_task_route_module_does_not_expose_dead_trace_governance_export_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_trace_governance_export"))

    def test_task_route_module_does_not_expose_dead_usage_row_builders(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_build_task_usage_top_task_row"))
        self.assertFalse(hasattr(task_routes_module, "_build_task_usage_by_session_row"))

    def test_task_route_module_does_not_expose_dead_task_export_governance_helpers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_collect_task_governance_summary_from_trace_steps")
        )
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_export_governance_from_summary")
        )

    def test_task_route_module_does_not_expose_dead_task_usage_blob_parser(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_parse_task_usage_blob"))

    def test_get_tasks_usage_dashboard_top_task_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage dashboard governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(row["task_id"], "task-usage-governance-1")
        self.assertEqual(row["source_kind"], "provider")
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_summary_reuses_shared_usage_json_parser(self) -> None:
        rows = [
            {"usage_json": "usage-json-1"},
            {"usage_json": "usage-json-2"},
        ]

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return rows

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._parse_usage_json_blob = lambda raw: captured.append(raw) or {  # type: ignore[attr-defined]
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "cost_estimate": 0.05,
                "usage_source": "provider",
            }
            payload = chat_persistence_module.get_tasks_usage_summary("user-usage-parser")
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-1", "usage-json-2"])
        self.assertEqual(payload["tasks_with_usage"], 2)
        self.assertEqual(payload["source_tasks_provider"], 2)
        self.assertEqual(payload["prompt_tokens"], 20)
        self.assertEqual(payload["completion_tokens"], 30)
        self.assertEqual(payload["total_tokens"], 50)

    def test_get_tasks_usage_dashboard_top_task_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage dashboard governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_reuses_with_task_governance_helper(self) -> None:
        rows = [
            {
                "id": "task-usage-shared-row-helper-1",
                "session_id": "session-usage-shared-row-helper",
                "prompt": "usage dashboard should reuse shared task row helper",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 5,
                        "cost_estimate": 0.02,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": "poisoned-trace-json",
                "tool_registry_profile": "poisoned_profile",
                "tool_registry_provider_source": "poisoned_source",
                "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                "created_at": "2026-06-17T22:00:00",
                "updated_at": "2026-06-17T22:05:00",
                "session_title": "Usage Shared Row Helper Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_with_task_governance = chat_persistence_module._with_task_governance  # type: ignore[attr-defined]
        original_extractor = chat_persistence_module._extract_task_governance_from_task_row  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._with_task_governance = (  # type: ignore[attr-defined]
                lambda task: captured.append(task)
                or {
                    "id": task["id"],
                    "session_id": task["session_id"],
                    "prompt": task["prompt"],
                    "usage_json": task["usage_json"],
                    "trace_json": task["trace_json"],
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"],
                    "session_title": task["session_title"],
                    "governance": {
                        "profile": "shared_profile",
                        "provider_source": "shared_source",
                        "allowed_tool_names": ["shared_tool"],
                        "allowed_tool_labels": ["Shared Tool"],
                    },
                }
            )
            chat_persistence_module._extract_task_governance_from_task_row = (  # type: ignore[attr-defined]
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "usage dashboard should reuse _with_task_governance instead of directly reusing the row governance extractor"
                    )
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-shared-row-helper"
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._with_task_governance = original_with_task_governance  # type: ignore[attr-defined]
            chat_persistence_module._extract_task_governance_from_task_row = original_extractor  # type: ignore[attr-defined]

        self.assertEqual(captured, [rows[0]])
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "shared_profile",
                "provider_source": "shared_source",
                "allowed_tool_names": ["shared_tool"],
                "allowed_tool_labels": ["Shared Tool"],
            },
        )
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["shared_profile"],
                "provider_sources": ["shared_source"],
                "allowed_tool_names": ["shared_tool"],
                "allowed_tool_labels": ["Shared Tool"],
            },
        )

    def test_get_tasks_usage_dashboard_reuses_shared_usage_json_parser(self) -> None:
        rows = [
            {
                "id": "task-usage-parser-1",
                "session_id": "session-usage-parser-1",
                "prompt": "usage parser task",
                "usage_json": "usage-json-1",
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-16T10:00:00",
                "updated_at": "2026-06-16T10:05:00",
                "session_title": "Usage Parser Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._parse_usage_json_blob = lambda raw: captured.append(raw) or {  # type: ignore[attr-defined]
                "prompt_tokens": 11,
                "completion_tokens": 13,
                "cost_estimate": 0.07,
                "usage_source": "provider",
            }
            payload = chat_persistence_module.get_tasks_usage_dashboard("user-usage-parser")
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-1"])
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(payload["summary"]["prompt_tokens"], 11)
        self.assertEqual(payload["summary"]["completion_tokens"], 13)
        self.assertEqual(payload["summary"]["total_tokens"], 24)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_top_tasks_do_not_expose_dead_trace_json(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-no-trace-json-1",
                "session_id": "session-usage-no-trace-json",
                "prompt": "usage top tasks should not surface dead trace json",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 7,
                        "completion_tokens": 9,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": "poisoned-trace-json",
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-17T21:00:00",
                "updated_at": "2026-06-17T21:05:00",
                "session_title": "Usage No Trace JSON Session",
            }
        ]
        original_get_db_connection = chat_persistence_module.get_db_connection

        class FakeCursor:
            def fetchall(self):
                return rows

        class FakeConnection:
            def execute(self, _query, _params):
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-no-trace-json"
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertNotIn("trace_json", payload["top_tasks"][0])

    def test_get_tasks_usage_dashboard_route_surfaces_top_task_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-governance-1",
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-09T10:00:00",
                        "updated_at": "2026-06-09T10:05:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.top_tasks), 1)
        row = payload.top_tasks[0]
        self.assertEqual(row.source_kind, "provider")
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "planning_only")
        self.assertEqual(row.governance.provider_source, "planning_suite")
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_get_tasks_usage_dashboard_route_trusts_top_task_governance_shape(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "usage top-task route should construct outward model directly from service governance dict"
                    )

            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-dict-builder-1",
                        "session_id": "session-usage-top-dict-builder",
                        "session_title": "Usage Governance Dict Builder Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-15T18:00:00",
                        "updated_at": "2026-06-15T18:05:00",
                        "source_kind": "provider",
                        "governance": GuardedGovernanceDict(
                            profile="guarded_profile",
                            provider_source="guarded_source",
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                        "trace_json": None,
                    }
                ],
            }
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-dict-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
        self.assertIsNotNone(payload.top_tasks[0].governance)
        assert payload.top_tasks[0].governance is not None
        self.assertEqual(payload.top_tasks[0].governance.profile, "guarded_profile")
        self.assertEqual(
            payload.top_tasks[0].governance.provider_source, "guarded_source"
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_get_tasks_usage_dashboard_route_trusts_service_top_task_governance(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "usage top-task route should construct outward model directly from the service governance dict"
                    )

            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-persisted-builder-1",
                        "session_id": "session-usage-top-persisted-builder",
                        "session_title": "Usage Persisted Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-16T18:00:00",
                        "updated_at": "2026-06-16T18:05:00",
                        "source_kind": "provider",
                        "governance": GuardedGovernanceDict(
                            profile="guarded_profile",
                            provider_source="guarded_source",
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                        "tool_registry_profile": "poisoned_profile",
                        "tool_registry_provider_source": "poisoned_source",
                        "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                        "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                        "trace_json": "poisoned-trace-json",
                    }
                ],
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _row: (_ for _ in ()).throw(
                    AssertionError(
                        "usage top-task route should not fall back to the shared row parser when service governance is already present"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-persisted-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNotNone(payload.top_tasks[0].governance)
        assert payload.top_tasks[0].governance is not None
        self.assertEqual(payload.top_tasks[0].governance.profile, "guarded_profile")
        self.assertEqual(
            payload.top_tasks[0].governance.provider_source, "guarded_source"
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_get_tasks_usage_dashboard_route_does_not_fallback_top_task_governance_from_row(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-no-fallback-1",
                        "session_id": "session-usage-top-no-fallback",
                        "session_title": "Usage No Fallback Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-17T08:00:00",
                        "updated_at": "2026-06-17T08:05:00",
                        "source_kind": "provider",
                        "tool_registry_profile": "poisoned_profile",
                        "tool_registry_provider_source": "poisoned_source",
                        "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                        "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                        "trace_json": "poisoned-trace-json",
                    }
                ],
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _row: (_ for _ in ()).throw(
                    AssertionError(
                        "usage top-task route should not fall back to the shared row parser when service governance is absent"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-no-fallback"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNone(payload.top_tasks[0].governance)

    def test_get_tasks_usage_dashboard_route_passes_raw_governance_dicts_to_usage_models(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_by_session_row = task_routes_module.TaskUsageBySessionRow
        original_top_task_row = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        captured: dict[str, list[object]] = {"by_session": [], "top_tasks": []}
        by_session_governance = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        top_task_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-raw-governance",
                        "session_title": "Usage Raw Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-18T10:20:00",
                        "governance": by_session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-raw-governance",
                        "session_id": "session-usage-raw-governance",
                        "session_title": "Usage Raw Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-18T10:20:00",
                        "updated_at": "2026-06-18T10:25:00",
                        "source_kind": "provider",
                        "governance": top_task_governance,
                    }
                ],
            }
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.__setitem__(
                    "by_session",
                    [row["governance"] for row in kwargs["by_session"]],
                )
                or captured.__setitem__(
                    "top_tasks",
                    [row["governance"] for row in kwargs["top_tasks"]],
                )
                or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-raw-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.TaskUsageBySessionRow = original_by_session_row
            task_routes_module.TaskUsageTopTaskRow = original_top_task_row
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(captured["by_session"], [by_session_governance])
        self.assertEqual(captured["top_tasks"], [top_task_governance])

    def test_get_tasks_usage_dashboard_route_reuses_shared_response_summary_helper_for_governance(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )
        original_by_session_row = task_routes_module.TaskUsageBySessionRow
        original_top_task_row = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        cloned_by_session = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        cloned_top_task = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: dict[str, list[object]] = {"by_session": [], "top_tasks": []}
        try:
            self.assertFalse(hasattr(task_routes_module, "_plain_clone_dict"))
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-clone-helper",
                        "session_title": "Usage Clone Helper Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-18T12:10:00",
                        "governance": {
                            "profiles": ["poisoned_profile"],
                            "provider_sources": ["poisoned_source"],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-clone-helper",
                        "session_id": "session-usage-clone-helper",
                        "session_title": "Usage Clone Helper Session",
                        "prompt_excerpt": "usage clone helper task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-18T12:10:00",
                        "updated_at": "2026-06-18T12:15:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "poisoned_profile",
                            "provider_source": "poisoned_source",
                        },
                    }
                ],
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda payload: {
                    **payload,
                    "by_session": [
                        {
                            "session_id": "session-usage-clone-helper",
                            "session_title": "Usage Clone Helper Session",
                            "tasks_with_usage": 1,
                            "total_tokens": 46,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-06-18T12:10:00",
                            "governance": cloned_by_session,
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-clone-helper",
                            "session_id": "session-usage-clone-helper",
                            "session_title": "Usage Clone Helper Session",
                            "prompt_excerpt": "usage clone helper task",
                            "total_tokens": 46,
                            "cost_estimate": 0.12,
                            "created_at": "2026-06-18T12:10:00",
                            "updated_at": "2026-06-18T12:15:00",
                            "source_kind": "provider",
                            "governance": cloned_top_task,
                        }
                    ],
                }
            )
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.__setitem__(
                    "by_session",
                    [row["governance"] for row in kwargs["by_session"]],
                )
                or captured.__setitem__(
                    "top_tasks",
                    [row["governance"] for row in kwargs["top_tasks"]],
                )
                or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-clone-helper"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskUsageBySessionRow = original_by_session_row
            task_routes_module.TaskUsageTopTaskRow = original_top_task_row
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(captured["by_session"], [cloned_by_session])
        self.assertEqual(captured["top_tasks"], [cloned_top_task])

    def test_get_tasks_usage_dashboard_route_reuses_top_level_response_model_for_outward_models(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )
        original_usage_summary_model = task_routes_module.TaskUsageSummaryResponse
        original_trend_point_model = task_routes_module.TaskUsageTrendPoint
        original_by_session_model = task_routes_module.TaskUsageBySessionRow
        original_top_task_model = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "ignored": True
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda _payload: {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 1,
                        "source_tasks_provider": 1,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost_estimate": 0.12,
                        "avg_total_tokens": 30.0,
                        "avg_cost_estimate": 0.12,
                    },
                    "trend": [
                        {
                            "day": "2026-06-23",
                            "tasks_total": 1,
                            "tasks_with_usage": 1,
                            "prompt_tokens": 10,
                            "completion_tokens": 20,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                        }
                    ],
                    "by_session": [
                        {
                            "session_id": "session-usage-outward-model",
                            "session_title": "Usage Session",
                            "tasks_with_usage": 1,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-06-23T16:10:00",
                            "governance": {
                                "profiles": ["planning_only"],
                                "provider_sources": ["planning_suite"],
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-outward-model",
                            "session_id": "session-usage-outward-model",
                            "session_title": "Usage Session",
                            "prompt_excerpt": "usage outward model",
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "created_at": "2026-06-23T16:10:00",
                            "updated_at": "2026-06-23T16:11:00",
                            "source_kind": "provider",
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ],
                }
            )
            task_routes_module.TaskUsageSummaryResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageSummaryResponse(...)"
                )
            )
            task_routes_module.TaskUsageTrendPoint = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTrendPoint(...)"
                )
            )
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                current_user={"id": "user-usage-outward-model"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskUsageSummaryResponse = original_usage_summary_model
            task_routes_module.TaskUsageTrendPoint = original_trend_point_model
            task_routes_module.TaskUsageBySessionRow = original_by_session_model
            task_routes_module.TaskUsageTopTaskRow = original_top_task_model
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["window_days"], 14)
        self.assertEqual(captured[0]["summary"]["tasks_total"], 1)
        self.assertEqual(captured[0]["trend"][0]["day"], "2026-06-23")
        self.assertEqual(
            captured[0]["by_session"][0]["governance"]["provider_sources"],
            ["planning_suite"],
        )
        self.assertEqual(
            captured[0]["top_tasks"][0]["governance"]["provider_source"],
            "planning_suite",
        )

    def test_get_tasks_usage_dashboard_by_session_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage session governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-session-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(row["session_id"], "session-usage-governance")
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_by_session_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage session governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_route_surfaces_session_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-09T10:05:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": ["planning_suite"],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-session-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.by_session), 1)
        row = payload.by_session[0]
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profiles, ["planning_only"])
        self.assertEqual(row.governance.provider_sources, ["planning_suite"])
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_get_tasks_usage_dashboard_route_trusts_service_session_governance_summary(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalizer = getattr(
            task_routes_module.chat_persistence_service,
            "_normalize_session_governance_summary_dict",
            None,
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-dict-builder",
                        "session_title": "Usage Governance Dict Builder Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-15T18:05:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": ["planning_suite"],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda _governance: (_ for _ in ()).throw(
                    AssertionError(
                        "usage by-session route should trust the normalized governance dict from the service"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-session-dict-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_normalizer is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "_normalize_session_governance_summary_dict",
                )
            else:
                task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.by_session[0].governance)
        assert payload.by_session[0].governance is not None
        self.assertEqual(payload.by_session[0].governance.profiles, ["planning_only"])
        self.assertEqual(
            payload.by_session[0].governance.provider_sources,
            ["planning_suite"],
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_names,
            ["task_plan"],
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_get_tasks_usage_dashboard_route_trusts_normalized_session_governance_shape(
        self,
    ) -> None:
        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "usage by-session route should construct outward model directly from normalized session governance dict"
                )

        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalizer = getattr(
            task_routes_module.chat_persistence_service,
            "_normalize_session_governance_summary_dict",
            None,
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-guarded-dict",
                        "session_title": "Usage Guarded Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-16T22:00:00",
                        "governance": GuardedSessionGovernanceDict(
                            profiles=["guarded_profile"],
                            provider_sources=["guarded_source"],
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                    }
                ],
                "top_tasks": [],
            }
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda _governance: (_ for _ in ()).throw(
                    AssertionError(
                        "usage by-session route should not re-normalize service governance dicts"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-guarded-dict"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_normalizer is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "_normalize_session_governance_summary_dict",
                )
            else:
                task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(len(payload.by_session), 1)
        self.assertIsNotNone(payload.by_session[0].governance)
        assert payload.by_session[0].governance is not None
        self.assertEqual(payload.by_session[0].governance.profiles, ["guarded_profile"])
        self.assertEqual(
            payload.by_session[0].governance.provider_sources, ["guarded_source"]
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_task_route_module_does_not_expose_dead_usage_session_governance_summary_builder(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                task_routes_module,
                "_build_task_usage_session_governance_summary_from_dict",
            )
        )

    def test_get_tasks_usage_dashboard_filters_by_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-1",
                "session_id": "session-usage-filtered-1",
                "prompt": "planning suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-1",
                            "type": "thought",
                            "content": "planner constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-2",
                "session_id": "session-usage-filtered-2",
                "prompt": "retrieval suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-2",
                            "type": "thought",
                            "content": "retrieval constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "retrieval_only",
                                "tool_registry_provider_source": "retrieval_suite",
                                "allowed_tool_names": ["task_retrieve"],
                                "allowed_tool_labels": ["Knowledge Retrieval Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T11:00:00",
                "updated_at": "2026-06-09T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(payload["by_session"][0]["session_id"], "session-usage-filtered-1")
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-usage-filtered-1")

    def test_get_tasks_usage_dashboard_filters_by_persisted_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-columns-1",
                "session_id": "session-usage-filtered-columns-1",
                "prompt": "planning suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-columns-2",
                "session_id": "session-usage-filtered-columns-2",
                "prompt": "retrieval suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "retrieval_only",
                "tool_registry_provider_source": "retrieval_suite",
                "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval Suite"]),
                "created_at": "2026-06-10T11:00:00",
                "updated_at": "2026-06-10T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-columns",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["session_id"],
            "session-usage-filtered-columns-1",
        )
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["task_id"],
            "task-usage-filtered-columns-1",
        )

    def test_get_tasks_usage_dashboard_reuses_shared_governance_filter_normalizer_for_task_match(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-normalizer-1",
                "session_id": "session-usage-filtered-normalizer-1",
                "prompt": "planning suite dashboard row with shared normalizer",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {"normalize_inputs": []}
        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value in {
                    " Planning_Only ",
                    "planning_only",
                    "profile::normalized",
                }:
                    return "profile::normalized"
                if value in {
                    " Planning_Suite ",
                    "planning_suite",
                    "provider::normalized",
                }:
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-normalizer",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        normalize_inputs = list(captured["normalize_inputs"])
        self.assertEqual(
            normalize_inputs[:4],
            [
                " Planning_Only ",
                " Planning_Suite ",
                "planning_only",
                "planning_suite",
            ],
        )
        self.assertGreaterEqual(normalize_inputs.count("profile::normalized"), 1)
        self.assertGreaterEqual(normalize_inputs.count("provider::normalized"), 1)
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_reuses_shared_task_governance_filter_matcher(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-matcher-1",
                "session_id": "session-usage-filtered-matcher-1",
                "prompt": "planning suite dashboard row with matcher",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-15T20:00:00",
                "updated_at": "2026-06-15T20:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-matcher-2",
                "session_id": "session-usage-filtered-matcher-2",
                "prompt": "retrieval suite dashboard row with matcher",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "retrieval_only",
                "tool_registry_provider_source": "retrieval_suite",
                "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval Suite"]),
                "created_at": "2026-06-15T21:00:00",
                "updated_at": "2026-06-15T21:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_matcher = getattr(
            chat_persistence_module,
            "_task_governance_matches_filters",
            None,
        )
        captured: list[tuple[object, object, object]] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._task_governance_matches_filters = (  # type: ignore[attr-defined]
                lambda governance, profile_filter, provider_source_filter: captured.append(
                    (governance, profile_filter, provider_source_filter)
                )
                or (
                    isinstance(governance, dict)
                    and governance.get("profile") == "planning_only"
                    and governance.get("provider_source") == "planning_suite"
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-matcher",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            if original_matcher is None:
                delattr(chat_persistence_module, "_task_governance_matches_filters")
            else:
                chat_persistence_module._task_governance_matches_filters = original_matcher  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                (
                    {
                        "profile": "planning_only",
                        "provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                    "planning_only",
                    "planning_suite",
                ),
                (
                    {
                        "profile": "retrieval_only",
                        "provider_source": "retrieval_suite",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval Suite"],
                    },
                    "planning_only",
                    "planning_suite",
                ),
            ],
        )
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_route_trusts_service_governance_filter_normalizer(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalize_governance_filter = (
            task_routes_module.chat_persistence_service._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: dict[str, object] = {}
        try:
            def fake_get_tasks_usage_dashboard(user_id, **kwargs):
                captured["user_id"] = user_id
                captured.update(kwargs)
                return {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 0,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "trend": [],
                    "by_session": [],
                    "top_tasks": [],
                }

            task_routes_module.get_tasks_usage_dashboard = fake_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                lambda _value: (_ for _ in ()).throw(
                    AssertionError(
                        "usage dashboard route should trust service-layer governance filter normalization"
                    )
                )
            )

            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-usage-filtered"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured["user_id"], "user-usage-filtered")
        self.assertEqual(
            captured["tool_registry_profile_filter"],
            " Planning_Only ",
        )
        self.assertEqual(
            captured["tool_registry_provider_source_filter"],
            " Planning_Suite ",
        )
