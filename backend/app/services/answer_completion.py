"""Explicit tool-stop context for the final answer; no inference of goal completion."""

from app.providers.completion_signals import normalize_finish_reason

TOOL_STOP_REASONS = frozenset({"no_tools", "max_rounds", "max_tool_calls", "observation_limit",
                              "repeated_action", "invalid_decision"})

# Both readers provide an owner-scoped candidate named r before this projection.
# Validate jsonb input too: syntactically valid JSON may contain unsupported Unicode/numbers.
FINAL_ANSWER_COMPLETION_SQL = """
    SELECT step -> 'meta' AS meta, step -> 'seq' AS seq
    FROM jsonb_array_elements(
      CASE WHEN pg_input_is_valid(r.trace_json, 'jsonb') AND r.trace_json IS JSON ARRAY
           THEN r.trace_json::jsonb ELSE '[]'::jsonb END
    ) WITH ORDINALITY AS trace(step, position)
    WHERE step -> 'meta' ->> 'step_type' = 'final_answer'
    ORDER BY position DESC LIMIT 1
"""


def completion_signals(row) -> dict[str, str]:
    signals = {}
    stop = row.get("agent_stop_reason")
    if isinstance(stop, str) and stop in TOOL_STOP_REASONS:
        signals["agent_stop_reason"] = stop
    finish = normalize_finish_reason(row.get("provider_finish_reason"))
    if finish is not None:
        signals["provider_finish_reason"] = finish
    return signals


def answer_completion_snapshot(row) -> dict | None:
    snapshot = completion_signals(row)
    seq = row.get("answer_seq")
    # The SQL projection returns only numeric JSON as bounded text. Never coerce bools/floats.
    if isinstance(seq, str) and seq.isascii() and seq.isdigit() and len(seq) <= 16:
        value = int(seq)
        if value <= 9_007_199_254_740_991:
            snapshot["seq"] = value
    return snapshot or None


def with_tool_stop_context(prompt: str, reason: str | None) -> str:
    if reason not in TOOL_STOP_REASONS:
        return prompt
    return (f"{prompt}\n\nRuntime tool-stage stop reason: {reason}.\n"
            "Answer using only the available evidence. Distinguish supported findings from unresolved parts.\n"
            "A stopped tool stage does not prove the user's objective was fulfilled.\n"
            + ("Explain the execution limit or invalid/repeated decision when it leaves the request unresolved. "
               "Do not claim missing checks or actions were completed."
               if reason != "no_tools" else
               "The planner requested no further tools; do not treat this as proof that every requirement is satisfied."))
