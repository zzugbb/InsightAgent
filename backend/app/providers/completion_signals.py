"""Only recorded, recognized completion reasons may describe generation endings."""

FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "content_filter", "function_call"})


def normalize_finish_reason(value: object) -> str | None:
    return value if isinstance(value, str) and value in FINISH_REASONS else None


def extract_finish_reason(payload: object) -> str | None:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return normalize_finish_reason(choices[0].get("finish_reason"))
    return None
