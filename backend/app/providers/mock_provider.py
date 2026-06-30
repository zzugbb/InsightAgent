import json
import re
import time
from typing import Iterator

from app.providers.base import ProviderResponse, ProviderUsage


class MockLLMProvider:
    def __init__(self, model: str = "mock-gpt", provider: str = "mock"):
        self.model = model
        self.provider = provider
        self._last_usage: ProviderUsage | None = None

    def generate(self, prompt: str) -> ProviderResponse:
        normalized_prompt = prompt.strip() or "empty prompt"
        if "[mock-error]" in normalized_prompt:
            raise RuntimeError("Mock provider forced error for SSE contract testing.")
        base_prompt, tool_observations = _split_tool_observations_prompt(normalized_prompt)
        prompt_preview = base_prompt or "empty prompt"
        content = "This is a mock response from InsightAgent. "
        if tool_observations:
            observation_summary = _summarize_tool_observations(tool_observations)
            if observation_summary:
                content += f"Summary: {observation_summary} "
            else:
                content += f"Tool context: {' | '.join(tool_observations)} "
        content += f"Prompt received: {prompt_preview}"
        usage = ProviderUsage(
            prompt_tokens=_mock_estimate_token_count(normalized_prompt),
            completion_tokens=_mock_estimate_token_count(content),
            total_tokens=_mock_estimate_token_count(normalized_prompt)
            + _mock_estimate_token_count(content),
        )
        self._last_usage = usage
        return ProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
        )

    def stream_generate(self, prompt: str) -> Iterator[str]:
        result = self.generate(prompt)
        self._last_usage = result.usage
        delay_sec = _mock_stream_delay_seconds(prompt)
        for token in result.content.split():
            if delay_sec > 0:
                time.sleep(delay_sec)
            yield f"{token} "

    def get_last_usage(self) -> ProviderUsage | None:
        return self._last_usage


def _mock_estimate_token_count(text: str) -> int:
    normalized = text.strip()
    if not normalized:
        return 0
    cjk_units = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", normalized))
    return max(1, cjk_units + latin_words)


def _split_tool_observations_prompt(prompt: str) -> tuple[str, list[str]]:
    separator_pattern = re.compile(r"\n+Tool observations:\n", re.MULTILINE)
    parts = separator_pattern.split(prompt, maxsplit=1)
    if len(parts) != 2:
        return prompt.strip(), []
    base_prompt = parts[0].strip()
    observations = [
        line.strip()
        for line in parts[1].splitlines()
        if line.strip()
    ]
    return base_prompt, observations


def _summarize_tool_observations(observations: list[str]) -> str | None:
    summaries: list[str] = []
    for observation in observations:
        summary = _summarize_tool_observation(observation)
        if summary:
            summaries.append(summary)
    if not summaries:
        return None
    return " ".join(summaries)


def _summarize_tool_observation(observation: str) -> str | None:
    label, payload = _parse_tool_observation(observation)
    if payload is None:
        return None

    plan = payload.get("plan")
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_plan_steps(payload.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = payload.get("expression")
    result = payload.get("result")
    if isinstance(expression, str) and expression.strip() and result is not None:
        return f"Calculated {expression.strip()} = {result}."

    hit_count = payload.get("hit_count")
    knowledge_base_id = payload.get("knowledge_base_id")
    if isinstance(hit_count, int) and hit_count >= 0:
        hit_label = "hit" if hit_count == 1 else "hits"
        if isinstance(knowledge_base_id, str) and knowledge_base_id.strip():
            return (
                f"Retrieved {hit_count} {hit_label} from knowledge base "
                f"{knowledge_base_id.strip()}."
            )
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = payload.get("documents_total")
    if isinstance(documents_total, int) and documents_total >= 0:
        document_label = "document" if documents_total == 1 else "documents"
        request_id = payload.get("request_id")
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}."

    generic_payload_summary = _summarize_generic_tool_payload(payload)
    if generic_payload_summary:
        if label:
            return f"{label} output - {generic_payload_summary}."
        return f"Tool output - {generic_payload_summary}."

    if label:
        return f"{label} completed."
    return None


def _parse_tool_observation(observation: str) -> tuple[str, dict[str, object] | None]:
    label, separator, raw_payload = observation.partition(":")
    if not separator:
        return observation.strip(), None
    normalized_label = label.strip()
    normalized_payload = raw_payload.strip()
    if not normalized_payload:
        return normalized_label, None
    try:
        payload = json.loads(normalized_payload)
    except json.JSONDecodeError:
        return normalized_label, None
    if not isinstance(payload, dict):
        return normalized_label, None
    return normalized_label, payload


def _normalize_plan_steps(raw_steps: object) -> list[str]:
    if not isinstance(raw_steps, list):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, str):
            continue
        step = raw_step.strip()
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _summarize_generic_tool_payload(payload: dict[str, object]) -> str | None:
    parts: list[str] = []
    for key, value in payload.items():
        normalized_key = key.strip()
        if not normalized_key:
            continue
        if isinstance(value, bool):
            parts.append(f"{normalized_key}={'true' if value else 'false'}")
            continue
        if isinstance(value, (int, float)):
            parts.append(f"{normalized_key}={value}")
            continue
        if isinstance(value, str):
            normalized_value = value.strip()
            if normalized_value:
                parts.append(f"{normalized_key}={normalized_value}")
            continue
    if not parts:
        return None
    return ", ".join(parts[:3])


def _mock_stream_delay_seconds(prompt: str) -> float:
    normalized = prompt.strip()
    if not normalized:
        return 0.0

    explicit_ms = re.search(r"\[mock-slow-ms=(\d{1,4})\]", normalized)
    if explicit_ms:
        return min(int(explicit_ms.group(1)), 1000) / 1000.0

    generic_slow = re.search(r"\[mock-slow(?:=(\d{1,4}))?\]", normalized)
    if not generic_slow:
        return 0.0

    ms_raw = generic_slow.group(1)
    if ms_raw is None:
        return 0.015
    return min(int(ms_raw), 1000) / 1000.0
