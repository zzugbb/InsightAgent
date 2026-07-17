import json
import re
import time
from typing import Iterator

from app.providers.base import ProviderResponse, ProviderUsage


_MOCK_REQUEST_ID_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"((?:\"|')?\b(?:authorization|api[_-]?key|credential|password|secret|"
    r"(?:access|refresh|session|id)?[_-]?token)"
    r"\b(?:\"|')?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;<>}]+)",
    re.IGNORECASE,
)
_MOCK_SENSITIVE_KEY_RE = re.compile(
    r"(?:authorization|api[_-]?key|credential|password|secret|"
    r"(?:access|refresh|session|id)?[_-]?token)",
    re.IGNORECASE,
)
_MOCK_SENSITIVE_FIELD_PATH_RE = re.compile(
    r"\b(?:headers|query_params|json_body|result_fields)"
    r"(?:\.[A-Za-z0-9_\-\[\]]+)+"
)
_MOCK_BARE_BEARER_TOKEN_RE = re.compile(r"\bbearer\s+\S+", re.IGNORECASE)


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
                safe_observations = [
                    _redact_mock_observation_text(observation)
                    for observation in tool_observations
                ]
                content += f"Tool context: {' | '.join(safe_observations)} "
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


def _normalize_mock_tool_semantic_kind(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    if not normalized:
        return None
    if (
        normalized == "knowledge_retrieval"
        or normalized.endswith("knowledge_retrieval")
        or normalized.endswith("_retrieval")
    ):
        return "knowledge_retrieval"
    if normalized == "task_planner" or normalized.endswith("_planner"):
        return "task_planner"
    if (
        normalized == "local_calculator"
        or normalized.endswith("_calculator")
        or normalized.endswith("_calc")
    ):
        return "local_calculator"
    return normalized


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


def _normalize_mock_observation_label(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    normalized = raw_value.strip()
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", normalized)
    return " ".join(normalized.lower().replace("_", " ").split())


def _label_implies_local_knowledge_retrieval(label: str) -> bool:
    normalized = _normalize_mock_observation_label(label)
    return normalized in {
        "knowledge retrieval",
        "hot retrieval",
        "task retrieve",
        "mock retrieve",
    }


def _label_implies_real_calc_summary(label: str) -> bool:
    normalized = _normalize_mock_observation_label(label)
    return normalized in {
        "provider math",
        "hosted math",
        "provider calc",
        "provider calculator",
        "hosted calc",
        "hosted calculator",
    }


def _label_implies_real_retrieval_summary(label: str) -> bool:
    normalized = _normalize_mock_observation_label(label)
    return normalized in {
        "provider search",
        "hosted search",
        "provider retrieval",
    }


def _get_safe_mock_request_id_display_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        return None
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in normalized):
        return None
    redacted = _MOCK_REQUEST_ID_SENSITIVE_ASSIGNMENT_RE.sub("[redacted]", normalized)
    if redacted != normalized:
        return None
    return normalized


def _redact_mock_sensitive_assignment_text(value: str) -> str:
    redacted = _MOCK_REQUEST_ID_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        value,
    )
    redacted = _MOCK_SENSITIVE_FIELD_PATH_RE.sub("[redacted]", redacted)
    return _MOCK_BARE_BEARER_TOKEN_RE.sub("[redacted]", redacted)


def _redact_mock_observation_text(value: str) -> str:
    return _redact_mock_sensitive_assignment_text(value.strip())


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
        _, separator, raw_payload = observation.partition(":")
        if separator and raw_payload.strip():
            return _redact_mock_observation_text(raw_payload)
        return None

    structured_summary = _summarize_structured_mock_tool_payload(
        label=label,
        payload=payload,
    )
    if structured_summary:
        return structured_summary

    nested_payload = _resolve_nested_mock_observation_payload(payload)
    if nested_payload is not None:
        nested_summary = _summarize_structured_mock_tool_payload(
            label=label,
            payload=nested_payload,
        )
        if nested_summary:
            return nested_summary

    generic_payload_summary = _summarize_generic_tool_payload(payload)
    if generic_payload_summary:
        if label:
            return f"{label} output - {generic_payload_summary}."
        return f"Tool output - {generic_payload_summary}."

    if label:
        return f"{label} completed."
    return None


def _summarize_structured_mock_tool_payload(
    *, label: str, payload: dict[str, object]
) -> str | None:
    plan = payload.get("plan")
    if isinstance(plan, str) and plan.strip():
        safe_plan = _redact_mock_sensitive_assignment_text(plan.strip())
        return f"Planned steps - {safe_plan}."
    steps = _normalize_plan_steps(payload.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = payload.get("expression")
    result = payload.get("result")
    request_id = _get_safe_mock_request_id_display_value(payload.get("request_id"))
    if isinstance(expression, str) and expression.strip() and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Calculated {expression.strip()} = {result} "
                f"(request id {request_id.strip()})."
            )
        return f"Calculated {expression.strip()} = {result}."

    explicit_semantic_kind = _normalize_mock_tool_semantic_kind(
        payload.get("semantic_kind")
    )
    fallback_runtime_kind = _normalize_mock_tool_semantic_kind(
        payload.get("tool_kind") or payload.get("kind")
    )
    semantic_kind = explicit_semantic_kind or fallback_runtime_kind
    semantic_family = _normalize_mock_tool_semantic_kind(
        payload.get("semantic_family")
    )
    if (
        semantic_family == "local_calculator"
        or semantic_kind == "local_calculator"
        or (
            result is not None
            and semantic_family is None
            and semantic_kind is None
            and _label_implies_real_calc_summary(label)
        )
    ):
        if result is not None:
            if isinstance(request_id, str) and request_id.strip():
                return f"Calculated result = {result} (request id {request_id.strip()})."
            return f"Calculated result = {result}."

    hit_count = payload.get("hit_count")
    knowledge_base_id = payload.get("knowledge_base_id")
    if isinstance(hit_count, int) and hit_count >= 0:
        hit_label = "hit" if hit_count == 1 else "hits"
        if (
            (
                explicit_semantic_kind == "knowledge_retrieval"
                or (
                    explicit_semantic_kind is None
                    and (
                        semantic_family == "knowledge_retrieval"
                        or (
                            semantic_family is None
                            and _label_implies_local_knowledge_retrieval(label)
                        )
                    )
                )
            )
            and isinstance(knowledge_base_id, str)
            and knowledge_base_id.strip()
        ):
            if isinstance(request_id, str) and request_id.strip():
                return (
                    f"Retrieved {hit_count} {hit_label} from knowledge base "
                    f"{knowledge_base_id.strip()} (request id {request_id.strip()})."
                )
            return (
                f"Retrieved {hit_count} {hit_label} from knowledge base "
                f"{knowledge_base_id.strip()}."
            )
        if (
            semantic_kind != "knowledge_retrieval"
            and semantic_family == "knowledge_retrieval"
        ):
            if isinstance(request_id, str) and request_id.strip():
                return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
            return f"Retrieved {hit_count} {hit_label}."
        if isinstance(request_id, str) and request_id.strip():
            return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = payload.get("documents_total")
    if isinstance(documents_total, int) and documents_total >= 0:
        document_label = "document" if documents_total == 1 else "documents"
        source_suffix = ""
        if isinstance(knowledge_base_id, str) and knowledge_base_id.strip():
            if explicit_semantic_kind == "knowledge_retrieval":
                source_suffix = f" from knowledge base {knowledge_base_id.strip()}"
            elif (
                semantic_kind != "knowledge_retrieval"
                and semantic_family == "knowledge_retrieval"
            ):
                source_suffix = f" from {knowledge_base_id.strip()}"
            elif (
                semantic_kind is None
                and semantic_family is None
                and _label_implies_real_retrieval_summary(label)
            ):
                source_suffix = f" from {knowledge_base_id.strip()}"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label}{source_suffix} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}{source_suffix}."

    return None


def _coerce_mock_json_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        payload: object = json.loads(normalized)
    except json.JSONDecodeError:
        if not (
            len(normalized) >= 2
            and normalized[0] == normalized[-1] == '"'
        ):
            return None
        nested_payload = normalized[1:-1].strip()
        if not nested_payload.startswith("{"):
            return None
        try:
            payload = json.loads(nested_payload)
        except json.JSONDecodeError:
            return None
    if isinstance(payload, str):
        nested_payload = payload.strip()
        if not nested_payload.startswith("{"):
            return None
        try:
            payload = json.loads(nested_payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    return payload


def _resolve_nested_mock_observation_payload(
    payload: dict[str, object],
) -> dict[str, object] | None:
    for output_key in ("safe_output", "output", "output_preview", "result_preview"):
        nested_payload = _coerce_mock_json_mapping(payload.get(output_key))
        if nested_payload is None:
            continue
        normalized_payload = dict(nested_payload)
        for context_key in (
            "semantic_kind",
            "semantic_family",
            "tool_kind",
            "kind",
            "request_id",
            "knowledge_base_id",
        ):
            if context_key not in normalized_payload and context_key in payload:
                normalized_payload[context_key] = payload[context_key]
        return normalized_payload
    return None


def _parse_tool_observation(observation: str) -> tuple[str, dict[str, object] | None]:
    label, separator, raw_payload = observation.partition(":")
    if not separator:
        return observation.strip(), None
    normalized_label = label.strip()
    normalized_payload = raw_payload.strip()
    if not normalized_payload:
        return normalized_label, None
    payload = _coerce_mock_json_mapping(normalized_payload)
    if payload is None:
        return normalized_label, None
    return normalized_label, payload


def _normalize_plan_steps(raw_steps: object) -> list[str]:
    if not isinstance(raw_steps, (list, tuple)):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, str):
            continue
        step = _redact_mock_sensitive_assignment_text(raw_step.strip())
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _summarize_generic_tool_payload(payload: dict[str, object]) -> str | None:
    parts: list[str] = []
    for key, value in payload.items():
        normalized_key = key.strip()
        if not normalized_key:
            continue
        if _MOCK_SENSITIVE_KEY_RE.search(normalized_key):
            continue
        if normalized_key == "request_id":
            safe_request_id = _get_safe_mock_request_id_display_value(value)
            if safe_request_id is None:
                continue
            parts.append(f"{normalized_key}={safe_request_id}")
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
                normalized_value = _redact_mock_sensitive_assignment_text(
                    normalized_value
                )
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
