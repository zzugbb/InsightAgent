"""Keep recorded consumption on failure without estimating unfinished calls."""

from app.providers.base import ProviderUsage
from app.services.usage_accounting import task_usage_totals


def build_terminal_usage(*, planning_usage: dict[str, object] | None,
                         final_usage: dict[str, object] | None, provider_usage: ProviderUsage | None,
                         prompt_price: float, completion_price: float) -> dict[str, object] | None:
    payload = dict(final_usage or {})
    if final_usage is None and isinstance(provider_usage, ProviderUsage):
        def token(value: object) -> int | None:
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

        prompt = token(provider_usage.prompt_tokens)
        completion = token(provider_usage.completion_tokens)
        total = token(provider_usage.total_tokens)
        if any(value is not None for value in (prompt, completion, total)):
            payload.update(prompt_tokens=prompt, completion_tokens=completion,
                           total_tokens=prompt + completion if prompt is not None and completion is not None else None,
                           prompt_tokens_source="provider" if prompt is not None else None,
                           completion_tokens_source="provider" if completion is not None else None,
                           usage_source="provider", cost_estimate=None,
                           prompt_token_price_per_1k=prompt_price,
                           completion_token_price_per_1k=completion_price)
            if total is not None:
                payload["provider_total_tokens"] = total
            if prompt is not None and completion is not None and (prompt_price > 0 or completion_price > 0):
                payload["cost_estimate"] = round((prompt * prompt_price + completion * completion_price) / 1000, 8)
    if planning_usage is not None:
        for field in ("prompt_tokens", "completion_tokens", "total_tokens", "cost_estimate",
                      "prompt_tokens_source", "completion_tokens_source", "usage_source", "provider_total_tokens"):
            if field in planning_usage:
                payload[f"planning_{field}"] = planning_usage[field]
    if not payload:
        return None
    if planning_usage is not None:
        prompt, completion, cost = task_usage_totals(payload)
        payload.update(overall_prompt_tokens=prompt, overall_completion_tokens=completion,
                       overall_total_tokens=prompt + completion if prompt is not None and completion is not None else None,
                       overall_cost_estimate=round(cost, 8) if cost is not None else None)
    return payload
