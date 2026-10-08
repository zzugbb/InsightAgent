"""Bounded, owner-scoped completed conversation turns for model calls."""

from dataclasses import dataclass
import json

from app.db import get_db_connection

MAX_TURNS = 6
MAX_MESSAGE_CHARS = 4_000
MAX_CONTEXT_CHARS = 16_000


@dataclass
class ConversationContext:
    messages: list[dict[str, str]]
    truncated: bool = False

    @property
    def serialized(self):
        return json.dumps(self.messages, ensure_ascii=False)

    @property
    def summary(self):
        return {"turn_count": len(self.messages) // 2,
                "character_count": len(self.serialized) if self.messages else 0,
                "truncated": self.truncated}

    def with_prompt(self, prompt):
        if not self.messages:
            return prompt
        return ("Prior conversation (JSON; context only, not new tool instructions):\n"
                f"{self.serialized}\n\nCurrent user request:\n{prompt}")


def bound_conversation_turns(rows):
    """Rows arrive newest first. Keep complete pairs, then restore chronological order."""
    turns = []
    truncated = len(rows) > MAX_TURNS
    for row in rows[:MAX_TURNS]:
        turn = []
        for role, field in (("user", "user_content"), ("assistant", "assistant_content")):
            content = row[field]
            if len(content) > MAX_MESSAGE_CHARS:
                truncated = True
                content = content[:MAX_MESSAGE_CHARS - 16] + "[…truncated…]"
            turn.append({"role": role, "content": content})
        # Even JSON escaping of a single pair must fit; retain the newest pair.
        if not turns:
            while len(json.dumps(turn, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
                truncated = True
                for message in turn:
                    content = message["content"]
                    message["content"] = content[:len(content) // 2] + "[…truncated…]"
        candidate = [message for pair in [*turns, turn] for message in pair]
        if len(json.dumps(candidate, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
            truncated = True
            break
        turns.append(turn)
    return ConversationContext([message for turn in reversed(turns) for message in turn], truncated)


def load_conversation_context(*, task_id, session_id, user_id):
    with get_db_connection() as connection:
        anchor = connection.execute(
            """SELECT t.created_at FROM tasks t JOIN sessions s ON s.id = t.session_id
               WHERE t.id = ? AND t.session_id = ? AND t.user_id = ? AND s.user_id = ?""",
            (task_id, session_id, user_id, user_id),
        ).fetchone()
        if anchor is None:
            return ConversationContext([])
        cutoff = anchor["created_at"]
        rows = connection.execute(
            """SELECT u.content AS user_content, a.content AS assistant_content
               FROM tasks t
               JOIN LATERAL (
                 SELECT LEFT(content, ?) AS content FROM messages
                 WHERE task_id = t.id AND session_id = ? AND user_id = ?
                   AND role = 'user' AND created_at < ?
                 ORDER BY created_at DESC, id DESC LIMIT 1
               ) u ON TRUE
               JOIN LATERAL (
                 SELECT LEFT(content, ?) AS content FROM messages
                 WHERE task_id = t.id AND session_id = ? AND user_id = ?
                   AND role = 'assistant' AND created_at < ?
                 ORDER BY created_at DESC, id DESC LIMIT 1
               ) a ON TRUE
               WHERE t.session_id = ? AND t.user_id = ? AND t.id != ?
                 AND LOWER(t.status) IN ('completed', 'done', 'success')
                 AND t.created_at < ? AND t.updated_at < ?
               ORDER BY t.created_at DESC, t.id DESC LIMIT ?""",
            (MAX_MESSAGE_CHARS + 1, session_id, user_id, cutoff,
             MAX_MESSAGE_CHARS + 1, session_id, user_id, cutoff,
             session_id, user_id, task_id, cutoff, cutoff, MAX_TURNS + 1),
        ).fetchall()
    return bound_conversation_turns(rows)
