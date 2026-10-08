"""Transaction boundaries for task completion and answer messages."""

from unittest.mock import MagicMock, patch

from app.services import chat_persistence_service as persistence


class TaskCompletionAtomicMixin:
    def completion_connection(self, *, updated=1, fail_on=None):
        connection = MagicMock()
        task_cursor = MagicMock(rowcount=updated)
        task_cursor.fetchone.return_value = {"session_id": "persisted-session"}

        def execute(query, params):
            if fail_on and fail_on in query:
                raise RuntimeError("write fixture")
            return task_cursor

        connection.execute.side_effect = execute
        context = MagicMock()
        context.__enter__.return_value = connection
        return context, connection

    def test_task_completion_atomic_commits_status_answer_and_session_together(self):
        context, connection = self.completion_connection()
        with patch.object(persistence, "get_db_connection", return_value=context) as database:
            self.assertEqual(persistence.complete_task("task", [], "owner", usage={"total_tokens": 3},
                                                      assistant_content="answer", execution_owner_id="instance-a"), 1)
        database.assert_called_once()
        queries = [call.args[0] for call in connection.execute.call_args_list]
        self.assertIn("UPDATE tasks", queries[0])
        self.assertIn("RETURNING session_id", queries[0])
        self.assertIn("execution_owner_id = ?", queries[0])
        self.assertIn("INSERT INTO messages", queries[1])
        self.assertIn("UPDATE sessions", queries[2])
        params = connection.execute.call_args_list[1].args[1]
        self.assertEqual(params[1:6], ("owner", "persisted-session", "task", "assistant", "answer"))
        self.assertEqual(connection.mock_calls[-1][0], "commit")
        connection.commit.assert_called_once()

    def test_task_completion_atomic_lost_terminal_race_never_inserts_answer(self):
        context, connection = self.completion_connection(updated=0)
        with patch.object(persistence, "get_db_connection", return_value=context):
            self.assertEqual(persistence.complete_task("task", [], "owner", assistant_content="answer"), 0)
        self.assertEqual(connection.execute.call_count, 1)

    def test_task_completion_atomic_message_or_session_write_failure_does_not_commit(self):
        for query in ("INSERT INTO messages", "UPDATE sessions"):
            with self.subTest(query=query):
                context, connection = self.completion_connection(fail_on=query)
                with patch.object(persistence, "get_db_connection", return_value=context):
                    with self.assertRaisesRegex(RuntimeError, "write fixture"):
                        persistence.complete_task("task", [], "owner", assistant_content="answer")
                connection.commit.assert_not_called()
                self.assertIs(context.__exit__.call_args.args[0], RuntimeError)

    def test_task_completion_atomic_non_success_or_invalid_answer_is_rejected_before_write(self):
        with patch.object(persistence, "get_db_connection") as database:
            for kwargs in ({"status": "failed", "assistant_content": "answer"},
                           {"status": "cancelled", "assistant_content": "answer"},
                           {"assistant_content": 123}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    persistence.complete_task("task", [], "owner", **kwargs)
            database.assert_not_called()

    def test_task_completion_atomic_standalone_message_keeps_existing_transaction(self):
        context, connection = self.completion_connection()
        with patch.object(persistence, "get_db_connection", return_value=context):
            message = persistence.create_message("session", "owner", "user", "prompt", "task")
        self.assertIsInstance(message, str)
        self.assertEqual(connection.execute.call_args_list[0].args[1][0], message)
        self.assertEqual(connection.execute.call_count, 2)
        connection.commit.assert_called_once()
