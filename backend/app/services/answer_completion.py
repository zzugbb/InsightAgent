"""Explicit tool-stop context for the final answer; no inference of goal completion."""

TOOL_STOP_REASONS = frozenset({"no_tools", "max_rounds", "max_tool_calls", "observation_limit",
                              "repeated_action", "invalid_decision"})


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
