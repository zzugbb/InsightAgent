"""Read whole-task totals while preserving final/planning breakdowns in storage."""

from math import isfinite


def usage_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if isfinite(number) and number >= 0 else None


def task_usage_totals(payload: dict[str, object]) -> tuple[float | None, float | None, float | None]:
    def total(field: str) -> float | None:
        overall = usage_number(payload.get(f"overall_{field}"))
        if overall is not None:
            return overall
        final = usage_number(payload.get(field))
        planning = usage_number(payload.get(f"planning_{field}"))
        if final is None and planning is None:
            return None
        return usage_number((final or 0) + (planning or 0))

    return total("prompt_tokens"), total("completion_tokens"), total("cost_estimate")


def task_usage_source(payload: dict[str, object]) -> str:
    def source(prefix: str) -> str:
        def label(field: str) -> str | None:
            value = payload.get(prefix + field)
            normalized = value.strip().lower() if isinstance(value, str) else None
            return normalized if normalized in {"provider", "estimated"} else None

        prompt, completion = label("prompt_tokens_source"), label("completion_tokens_source")
        if prompt is not None and completion is not None and prompt != completion:
            return "mixed"
        return label("usage_source") or prompt or completion or "legacy"

    stages = [source(prefix) for prefix in ("", "planning_")
              if any(usage_number(payload.get(prefix + field)) is not None
                     for field in ("prompt_tokens", "completion_tokens", "cost_estimate"))]
    if not stages:
        return source("")
    if "mixed" in stages or {"provider", "estimated"}.issubset(stages):
        return "mixed"
    if "legacy" in stages:
        return "legacy"
    return stages[0]
