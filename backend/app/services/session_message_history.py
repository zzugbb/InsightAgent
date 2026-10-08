"""Session message history with compact completion metadata, independent of task pages."""

from app.services.answer_completion import FINAL_ANSWER_COMPLETION_SQL, answer_completion_snapshot


def load_session_messages(connection, session_id: str, user_id: str) -> list[dict]:
    rows = connection.execute(
        f"""WITH session_messages AS MATERIALIZED (
              SELECT id, session_id, task_id, role, content, created_at FROM messages
              WHERE session_id = ? AND user_id = ?
            ), answer_tasks AS MATERIALIZED (
              SELECT t.id, t.trace_json FROM tasks t JOIN sessions s ON s.id = t.session_id
              WHERE t.session_id = ? AND t.user_id = ? AND s.user_id = ?
                AND EXISTS (SELECT 1 FROM session_messages m WHERE m.task_id = t.id AND m.role = 'assistant')
            ), completions AS MATERIALIZED (
              SELECT r.id,
                     LEFT(final.meta ->> 'agent_stop_reason', 32) AS agent_stop_reason,
                     LEFT(final.meta ->> 'provider_finish_reason', 32) AS provider_finish_reason,
                     CASE WHEN jsonb_typeof(final.seq) = 'number'
                          THEN LEFT(final.seq::text, 32) END AS answer_seq
              FROM answer_tasks r LEFT JOIN LATERAL (
                {FINAL_ANSWER_COMPLETION_SQL}
              ) final ON TRUE
            )
            SELECT m.*, c.agent_stop_reason, c.provider_finish_reason, c.answer_seq
            FROM session_messages m LEFT JOIN completions c ON m.role = 'assistant' AND c.id = m.task_id
            ORDER BY m.created_at ASC, m.id ASC""",
        (session_id, user_id, session_id, user_id, user_id),
    ).fetchall()
    messages = []
    for row in rows:
        completion = answer_completion_snapshot(row)
        message = {key: row[key] for key in ("id", "session_id", "task_id", "role", "content", "created_at")}
        if completion is not None:
            message["completion"] = completion
        messages.append(message)
    return messages
