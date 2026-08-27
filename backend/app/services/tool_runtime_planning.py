from __future__ import annotations

import json
import re
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from collections.abc import Mapping
from dataclasses import replace

from app.config import get_settings
from app.providers.base import ProviderUsage
from app.providers.response_utils import (
    coerce_provider_usage,
    extract_response_text,
    normalize_response_text,
)


def _runtime_module():
    from app.services import tool_runtime

    return tool_runtime


def ToolPlanArtifacts(*args, **kwargs):  # noqa: N802
    return _runtime_module().ToolPlanArtifacts(*args, **kwargs)


def _annotate_task_plan_tool_input(*args, **kwargs):
    return _runtime_module()._annotate_task_plan_tool_input(*args, **kwargs)


def _coerce_tool_execution_string_like_value(*args, **kwargs):
    return _runtime_module()._coerce_tool_execution_string_like_value(*args, **kwargs)


def _coerce_tool_registry_spec_payload(*args, **kwargs):
    return _runtime_module()._coerce_tool_registry_spec_payload(*args, **kwargs)


def _get_enabled_planning_optional_tool_names(*args, **kwargs):
    return _runtime_module()._get_enabled_planning_optional_tool_names(*args, **kwargs)


def _get_enabled_planning_primary_tool_name(*args, **kwargs):
    return _runtime_module()._get_enabled_planning_primary_tool_name(*args, **kwargs)


def _get_first_enabled_planning_tool_name_for_kind(*args, **kwargs):
    return _runtime_module()._get_first_enabled_planning_tool_name_for_kind(*args, **kwargs)


def _is_non_text_sequence(*args, **kwargs):
    return _runtime_module()._is_non_text_sequence(*args, **kwargs)


def _resolve_provider_tool_name(*args, **kwargs):
    return _runtime_module()._resolve_provider_tool_name(*args, **kwargs)


def get_enabled_planning_tool_labels(*args, **kwargs):
    return _runtime_module().get_enabled_planning_tool_labels(*args, **kwargs)


def get_enabled_planning_tool_names(*args, **kwargs):
    return _runtime_module().get_enabled_planning_tool_names(*args, **kwargs)


def get_tool_display_name(*args, **kwargs):
    return _runtime_module().get_tool_display_name(*args, **kwargs)


def get_tool_semantic_kind(*args, **kwargs):
    return _runtime_module().get_tool_semantic_kind(*args, **kwargs)


def resolve_tool_registration(*args, **kwargs):
    return _runtime_module().resolve_tool_registration(*args, **kwargs)


def _extract_calc_expression(prompt: str) -> str | None:
    tagged = re.search(r"\[calc:(.+?)\]", prompt, flags=re.IGNORECASE)
    if tagged:
        expr = tagged.group(1).strip()
        return expr or None

    plain = re.search(r"(?:计算|calc)\s*[:：]?\s*([0-9+\-*/().%\s]{3,})", prompt)
    if plain:
        expr = plain.group(1).strip()
        return expr or None

    return None


def _safe_eval_expression(expr: str) -> float:
    tree = parse(expr, mode="eval")

    def _eval(node: object) -> float:
        if isinstance(node, Expression):
            return _eval(node.body)
        if isinstance(node, BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, Add):
                return left + right
            if isinstance(node.op, Sub):
                return left - right
            if isinstance(node.op, Mult):
                return left * right
            if isinstance(node.op, Div):
                return left / right
            if isinstance(node.op, Mod):
                return left % right
            if isinstance(node.op, Pow):
                return left**right
            raise ValueError("unsupported binary operator")
        if isinstance(node, UnaryOp):
            value = _eval(node.operand)
            if isinstance(node.op, UAdd):
                return value
            if isinstance(node.op, USub):
                return -value
            raise ValueError("unsupported unary operator")
        if isinstance(node, int | float):
            return float(node)
        if hasattr(node, "value") and isinstance(getattr(node, "value"), (int, float)):
            return float(getattr(node, "value"))
        raise ValueError("unsupported expression node")

    return _eval(tree)


def _extract_knowledge_base_id(prompt: str) -> str | None:
    tagged = re.search(r"\[kb:([a-zA-Z0-9_-]{1,64})\]", prompt)
    if not tagged:
        return None
    value = tagged.group(1).strip()
    return value or None


def _build_rule_based_tool_plan(
    prompt: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]]:
    normalized = prompt.strip().lower()
    settings = get_settings()
    knowledge_base_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
    primary_planner_name = _get_enabled_planning_primary_tool_name(
        registry_provider=registry_provider,
    )
    retrieval_tool_name = _get_first_enabled_planning_tool_name_for_kind(
        "knowledge_retrieval",
        registry_provider=registry_provider,
    )
    calculator_tool_name = _get_first_enabled_planning_tool_name_for_kind(
        "local_calculator",
        registry_provider=registry_provider,
    )
    plan: list[dict[str, object]] = []
    if primary_planner_name is not None:
        plan.append(
            {
                "name": primary_planner_name,
                "input": {
                    "prompt_preview": prompt.strip()[:120],
                },
            }
        )

    if (
        retrieval_tool_name is not None
        and (
            "rag" in normalized
            or "知识" in normalized
            or "检索" in normalized
            or "context" in normalized
            or "[multi-tool]" in normalized
            or "[mock-multi-tool]" in normalized
        )
    ):
        plan.append(
            {
                "name": retrieval_tool_name,
                "input": {
                    "query": prompt.strip()[:80] or "default query",
                    "top_k": settings.rag_default_top_k,
                    "knowledge_base_id": knowledge_base_id,
                },
            }
        )

    calc_expr = _extract_calc_expression(prompt)
    if calc_expr and calculator_tool_name is not None:
        plan.append(
            {
                "name": calculator_tool_name,
                "input": {
                    "expression": calc_expr,
                },
            }
        )

    return plan


def _build_provider_tool_plan_prompt(
    prompt: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str:
    allowed_tool_names = _get_enabled_planning_optional_tool_names(
        registry_provider=registry_provider,
    )
    allowed_tool_names_text = ", ".join(allowed_tool_names) if allowed_tool_names else "none"
    allowed_tool_labels = [
        get_tool_display_name(name, registry_provider=registry_provider)
        for name in allowed_tool_names
    ]
    allowed_tool_labels_text = ", ".join(allowed_tool_labels) if allowed_tool_labels else "none"
    input_lines: list[str] = []
    for tool_name in allowed_tool_names:
        registration = resolve_tool_registration(
            tool_name,
            registry_provider=registry_provider,
        )
        if registration is None:
            continue
        semantic_kind = get_tool_semantic_kind(
            name=tool_name,
            registration=registration,
        )
        if semantic_kind == "knowledge_retrieval":
            input_lines.append(
                f"For {tool_name} input, include query, optional top_k, optional knowledge_base_id.\n"
            )
            continue
        if semantic_kind == "local_calculator":
            input_lines.append(
                f"For {tool_name} input, include expression.\n"
            )
    return (
        "You are the Task Planner for InsightAgent.\n"
        "Return JSON only with shape {\"tools\": [...]}.\n"
        f"Allowed tool names: {allowed_tool_names_text}.\n"
        f"Allowed tool labels: {allowed_tool_labels_text}.\n"
        "Do not include planner tools in the JSON; planner is added automatically.\n"
        + "".join(input_lines)
        + "If no extra tools are needed, return {\"tools\": []}.\n"
        + f"User request:\n{prompt.strip() or 'empty prompt'}"
    )


_PROVIDER_TOOL_PLAN_PAYLOAD_ATTRS = (
    "response",
    "data",
    "result",
    "tools",
    "plan",
    "output",
    "content",
    "choices",
    "candidates",
    "parts",
    "message",
    "delta",
    "tool_calls",
    "toolUse",
    "tool_use",
    "toolUseId",
    "tool_use_id",
    "function_call",
    "functionCall",
    "function",
    "name",
    "tool",
    "tool_name",
    "function_name",
    "input",
    "arguments",
    "args",
    "parameters",
    "type",
    "text",
    "output_text",
)


def _coerce_provider_tool_plan_payload(raw_value: object) -> object:
    raw_value = _coerce_tool_registry_spec_payload(raw_value)
    if isinstance(raw_value, Mapping):
        return {
            key: _coerce_provider_tool_plan_payload(value)
            for key, value in raw_value.items()
        }
    if _is_non_text_sequence(raw_value):
        return [_coerce_provider_tool_plan_payload(value) for value in raw_value]
    if isinstance(raw_value, (str, bytes, bytearray, memoryview)):
        return raw_value
    attrs: dict[str, object] = {}
    for attr_name in _PROVIDER_TOOL_PLAN_PAYLOAD_ATTRS:
        try:
            attr_value = getattr(raw_value, attr_name)
        except Exception:  # noqa: BLE001
            continue
        if attr_value is None:
            continue
        attrs[attr_name] = _coerce_provider_tool_plan_payload(attr_value)
    return attrs or raw_value


def _extract_provider_tool_plan_items_from_payload(
    payload: object,
) -> list[object] | None:
    payload = _coerce_provider_tool_plan_payload(payload)
    if _is_non_text_sequence(payload):
        extracted_items: list[object] = []
        expanded_nested_item = False
        for raw_item in payload:
            item = _coerce_provider_tool_plan_payload(raw_item)
            nested_items = _extract_provider_tool_plan_items_from_payload(item)
            if nested_items is not None:
                extracted_items.extend(nested_items)
                expanded_nested_item = True
                continue
            extracted_items.append(raw_item)
        return extracted_items if expanded_nested_item else list(payload)
    if not isinstance(payload, Mapping):
        return None
    tools = payload.get("tools", payload.get("plan"))
    tools = _coerce_tool_registry_spec_payload(tools)
    if _is_non_text_sequence(tools):
        return list(tools)
    tool_calls = _coerce_tool_registry_spec_payload(payload.get("tool_calls"))
    if _is_non_text_sequence(tool_calls):
        return list(tool_calls)
    tool_use = _coerce_tool_registry_spec_payload(
        payload.get("toolUse", payload.get("tool_use"))
    )
    if isinstance(tool_use, Mapping):
        return [tool_use]
    function_call = _coerce_tool_registry_spec_payload(payload.get("function_call"))
    if isinstance(function_call, Mapping):
        return [function_call]
    function_call = _coerce_tool_registry_spec_payload(payload.get("functionCall"))
    if isinstance(function_call, Mapping):
        return [function_call]
    output_items = _coerce_tool_registry_spec_payload(payload.get("output"))
    if _is_non_text_sequence(output_items):
        extracted_output_items: list[object] = []
        for raw_output_item in output_items:
            output_item = _coerce_provider_tool_plan_payload(raw_output_item)
            output_item_items = _extract_provider_tool_plan_items_from_payload(
                output_item
            )
            if output_item_items is not None:
                extracted_output_items.extend(output_item_items)
                continue
            if not isinstance(output_item, Mapping):
                continue
            content_items = _coerce_tool_registry_spec_payload(
                output_item.get("content")
            )
            if not _is_non_text_sequence(content_items):
                continue
            for raw_content_item in content_items:
                content_item = _coerce_provider_tool_plan_payload(raw_content_item)
                content_item_items = _extract_provider_tool_plan_items_from_payload(
                    content_item
                )
                if content_item_items is not None:
                    extracted_output_items.extend(content_item_items)
                    continue
                if not isinstance(content_item, Mapping):
                    continue
                for text_key in ("text", "output_text"):
                    text_items = _extract_provider_tool_plan_items(
                        content_item.get(text_key)
                    )
                    if text_items is not None:
                        extracted_output_items.extend(text_items)
                        break
        if extracted_output_items:
            return extracted_output_items
    content = _coerce_tool_registry_spec_payload(payload.get("content"))
    if _is_non_text_sequence(content):
        extracted_content_items: list[object] = []
        for raw_content_item in content:
            content_item = _coerce_provider_tool_plan_payload(raw_content_item)
            content_item_items = _extract_provider_tool_plan_items_from_payload(
                content_item
            )
            if content_item_items is not None:
                extracted_content_items.extend(content_item_items)
                continue
            if not isinstance(content_item, Mapping):
                continue
            for text_key in ("text", "output_text"):
                text_items = _extract_provider_tool_plan_items(
                    content_item.get(text_key)
                )
                if text_items is not None:
                    extracted_content_items.extend(text_items)
                    break
        if extracted_content_items:
            return extracted_content_items
    elif content is not None:
        content_items = (
            _extract_provider_tool_plan_items_from_payload(content)
            if isinstance(content, Mapping)
            else _extract_provider_tool_plan_items(content)
        )
        if content_items is not None:
            return content_items
    parts = _coerce_tool_registry_spec_payload(payload.get("parts"))
    if _is_non_text_sequence(parts):
        extracted_part_items: list[object] = []
        for raw_part in parts:
            part = _coerce_provider_tool_plan_payload(raw_part)
            part_items = _extract_provider_tool_plan_items_from_payload(part)
            if part_items is not None:
                extracted_part_items.extend(part_items)
                continue
            if not isinstance(part, Mapping):
                continue
            for text_key in ("text", "output_text"):
                text_items = _extract_provider_tool_plan_items(part.get(text_key))
                if text_items is not None:
                    extracted_part_items.extend(text_items)
                    break
        if extracted_part_items:
            return extracted_part_items
    choices = _coerce_tool_registry_spec_payload(payload.get("choices"))
    if _is_non_text_sequence(choices):
        for raw_choice in choices:
            choice = _coerce_provider_tool_plan_payload(raw_choice)
            if not isinstance(choice, Mapping):
                continue
            message = _coerce_provider_tool_plan_payload(
                choice.get("message", choice.get("delta"))
            )
            choice_items = _extract_provider_tool_plan_items_from_payload(message)
            if choice_items is not None:
                return choice_items
            if isinstance(message, Mapping):
                content_items = _extract_provider_tool_plan_items(
                    message.get("content")
                )
                if content_items is not None:
                    return content_items
    candidates = _coerce_tool_registry_spec_payload(payload.get("candidates"))
    if _is_non_text_sequence(candidates):
        for raw_candidate in candidates:
            candidate = _coerce_provider_tool_plan_payload(raw_candidate)
            candidate_items = _extract_provider_tool_plan_items_from_payload(candidate)
            if candidate_items is not None:
                return candidate_items
    raw_name = payload.get(
        "name",
        payload.get(
            "tool",
            payload.get(
                "tool_name",
                payload.get("function_name", payload.get("function")),
            ),
        ),
    )
    raw_name = _coerce_tool_execution_string_like_value(raw_name)
    if isinstance(raw_name, str) and raw_name.strip():
        return [payload]
    for wrapper_key in ("response", "data", "result"):
        wrapped_payload = _coerce_tool_registry_spec_payload(payload.get(wrapper_key))
        wrapped_items = _extract_provider_tool_plan_items_from_payload(wrapped_payload)
        if wrapped_items is not None:
            return wrapped_items
    return None


def _extract_provider_tool_plan_items(provider_content: object) -> list[object] | None:
    provider_content = _coerce_provider_tool_plan_payload(provider_content)
    direct_items = _extract_provider_tool_plan_items_from_payload(provider_content)
    if direct_items is not None:
        return direct_items
    if not isinstance(provider_content, str):
        return None
    raw = provider_content.strip()
    if not raw:
        return None
    candidates = [raw]
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(item.strip() for item in fenced if item.strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        items = _extract_provider_tool_plan_items_from_payload(payload)
        if items is not None:
            return items
    return None


def _extract_provider_response_content(response: object) -> object:
    normalized_response = _coerce_provider_tool_plan_payload(response)
    if isinstance(normalized_response, Mapping):
        response = normalized_response
        if any(
            key in response
            for key in (
                "tools",
                "plan",
                "name",
                "tool",
                "tool_calls",
                "function_call",
                "choices",
                "tool_name",
                "function_name",
                "function",
            )
        ):
            return response
        if "content" in response:
            content = response.get("content")
            normalized_text = normalize_response_text(content)
            if normalized_text:
                return normalized_text
            return content
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        text = response.get("text")
        if isinstance(text, str) and text.strip():
            return text
        normalized_text = extract_response_text(response)
        if normalized_text:
            return normalized_text
        return response
    content = getattr(response, "content", response)
    normalized_text = normalize_response_text(content)
    if normalized_text:
        return normalized_text
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    normalized_text = extract_response_text(response)
    if normalized_text:
        return normalized_text
    return content


def _coerce_provider_tool_plan_input_mapping(raw_value: object) -> object:
    raw_value = _coerce_provider_tool_plan_payload(raw_value)
    if not isinstance(raw_value, str):
        return raw_value
    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value
    parsed_value = _coerce_tool_registry_spec_payload(parsed_value)
    return parsed_value if isinstance(parsed_value, Mapping) else raw_value


def _normalize_provider_tool_plan_item(
    raw_item: object,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> tuple[str, dict[str, object]] | None:
    raw_item = _coerce_provider_tool_plan_payload(raw_item)
    if isinstance(raw_item, str):
        tool_name = _resolve_provider_tool_name(
            raw_item,
            registry_provider=registry_provider,
        )
        if not tool_name:
            return None
        return tool_name, {}
    if not isinstance(raw_item, Mapping):
        return None
    raw_function = _coerce_provider_tool_plan_payload(raw_item.get("function"))
    if isinstance(raw_function, Mapping):
        merged_item = dict(raw_item)
        for key, value in raw_function.items():
            merged_item.setdefault(str(key), value)
        raw_item = merged_item
    raw_name = raw_item.get(
        "name",
        raw_item.get(
            "tool",
            raw_item.get(
                "tool_name",
                raw_item.get("function_name", raw_item.get("function", "")),
            ),
        ),
    )
    tool_name = _resolve_provider_tool_name(
        raw_name,
        registry_provider=registry_provider,
    )
    if not tool_name:
        return None
    tool_input = _coerce_provider_tool_plan_input_mapping(raw_item.get("input"))
    if not isinstance(tool_input, Mapping):
        tool_input = _coerce_provider_tool_plan_input_mapping(
            raw_item.get("arguments")
        )
    if not isinstance(tool_input, Mapping):
        tool_input = _coerce_provider_tool_plan_input_mapping(raw_item.get("args"))
    if not isinstance(tool_input, Mapping):
        tool_input = _coerce_provider_tool_plan_input_mapping(
            raw_item.get("parameters")
        )
    if not isinstance(tool_input, Mapping):
        tool_input = {
            key: value
            for key, value in raw_item.items()
            if key
            not in {
                "name",
                "tool",
                "tool_name",
                "function_name",
                "function",
                "input",
                "arguments",
                "args",
                "parameters",
            }
        }
    tool_input = _coerce_provider_tool_plan_payload(tool_input)
    if not isinstance(tool_input, Mapping):
        tool_input = {}
    return tool_name, dict(tool_input)


def _normalize_provider_tool_plan(
    raw_items: list[object],
    *,
    prompt: str,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]] | None:
    settings = get_settings()
    prompt_preview = prompt.strip()[:120]
    default_query = prompt.strip()[:80] or "default query"
    default_kb_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
    fallback_calc_expression = _extract_calc_expression(prompt)
    primary_planner_name = _get_enabled_planning_primary_tool_name(
        registry_provider=registry_provider,
    )
    enabled_optional_tool_names = set(
        _get_enabled_planning_optional_tool_names(
            registry_provider=registry_provider,
        )
    )
    normalized_plan: list[dict[str, object]] = []
    seen_names: set[str] = set()
    saw_planner_tool = False
    if primary_planner_name is not None:
        normalized_plan.append(
            {
                "name": primary_planner_name,
                "input": {
                    "prompt_preview": prompt_preview,
                },
            }
        )
        seen_names.add(primary_planner_name)

    for raw_item in raw_items:
        normalized_item = _normalize_provider_tool_plan_item(
            raw_item,
            registry_provider=registry_provider,
        )
        if normalized_item is None:
            continue
        tool_name, tool_input = normalized_item
        if tool_name in seen_names or tool_name not in enabled_optional_tool_names:
            continue
        registration = resolve_tool_registration(
            tool_name,
            registry_provider=registry_provider,
        )
        tool_kind = (
            get_tool_semantic_kind(
                name=tool_name,
                registration=registration,
            )
            if registration is not None
            else None
        )
        if tool_kind == "task_planner":
            saw_planner_tool = True
            continue
        if tool_kind == "knowledge_retrieval":
            top_k = tool_input.get("top_k")
            if isinstance(top_k, bool):
                top_k = None
            if not isinstance(top_k, int) or top_k <= 0:
                top_k = settings.rag_default_top_k
            query = str(tool_input.get("query") or default_query)
            knowledge_base_id = str(
                tool_input.get("knowledge_base_id") or default_kb_id
            )
            normalized_plan.append(
                {
                    "name": tool_name,
                    "input": {
                        "query": query,
                        "top_k": top_k,
                        "knowledge_base_id": knowledge_base_id,
                    },
                }
            )
            seen_names.add(tool_name)
            continue
        if tool_kind == "local_calculator":
            expression = _coerce_tool_execution_string_like_value(
                tool_input.get("expression")
            )
            if not isinstance(expression, str) or not expression.strip():
                expression = fallback_calc_expression
            if not isinstance(expression, str) or not expression.strip():
                continue
            try:
                _safe_eval_expression(expression)
            except Exception:  # noqa: BLE001
                continue
            normalized_plan.append(
                {
                    "name": tool_name,
                    "input": {
                        "expression": expression,
                    },
                }
            )
            seen_names.add(tool_name)

    if not raw_items:
        return normalized_plan
    if primary_planner_name is not None and len(normalized_plan) == 1:
        if saw_planner_tool:
            return normalized_plan
        return None
    if primary_planner_name is None and not normalized_plan:
        return None
    return normalized_plan


def _build_provider_tool_plan(
    prompt: str,
    *,
    provider: object,
    registry_provider: ToolRegistryProvider | None = None,
) -> ToolPlanArtifacts | None:
    provider_name = str(getattr(provider, "provider", "")).strip().lower()
    generate = getattr(provider, "generate", None)
    if provider_name == "mock" or not callable(generate):
        return None
    planning_prompt = _build_provider_tool_plan_prompt(
        prompt,
        registry_provider=registry_provider,
    )
    response = generate(planning_prompt)
    raw_usage = (
        response.get("usage")
        if isinstance(response, dict)
        else getattr(response, "usage", None)
    )
    provider_usage = coerce_provider_usage(raw_usage)
    if provider_usage is None and isinstance(raw_usage, dict):
        provider_usage = ProviderUsage()
    if provider_usage is None:
        get_last_usage = getattr(provider, "get_last_usage", None)
        if callable(get_last_usage):
            provider_usage = coerce_provider_usage(get_last_usage())
    content = _extract_provider_response_content(response)
    if content is None:
        return ToolPlanArtifacts(
            tool_plan=[],
            planning_prompt=planning_prompt,
            provider_usage=provider_usage,
            planning_provider_attempted=True,
            planning_provider_used=False,
        )
    items = _extract_provider_tool_plan_items(content)
    if items is None:
        return ToolPlanArtifacts(
            tool_plan=[],
            planning_prompt=planning_prompt,
            provider_usage=provider_usage,
            planning_provider_attempted=True,
            planning_provider_used=False,
        )
    normalized_plan = _normalize_provider_tool_plan(
        items,
        prompt=prompt,
        registry_provider=registry_provider,
    )
    return ToolPlanArtifacts(
        tool_plan=normalized_plan or [],
        planning_prompt=planning_prompt,
        provider_usage=provider_usage,
        planning_provider_attempted=True,
        planning_provider_used=normalized_plan is not None,
    )


def build_tool_plan_artifacts(
    prompt: str,
    *,
    provider: object | None = None,
    registry_provider: ToolRegistryProvider | None = None,
) -> ToolPlanArtifacts:
    allowed_tool_names = get_enabled_planning_tool_names(
        registry_provider=registry_provider,
    )
    allowed_tool_labels = get_enabled_planning_tool_labels(
        registry_provider=registry_provider,
    )
    fallback_plan = _annotate_task_plan_tool_input(
        _build_rule_based_tool_plan(
            prompt,
            registry_provider=registry_provider,
        ),
        registry_provider=registry_provider,
    )
    if provider is None:
        return ToolPlanArtifacts(
            tool_plan=fallback_plan,
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    try:
        provider_plan = _build_provider_tool_plan(
            prompt,
            provider=provider,
            registry_provider=registry_provider,
        )
    except Exception:  # noqa: BLE001
        provider_plan = None
    if provider_plan is None:
        return ToolPlanArtifacts(
            tool_plan=fallback_plan,
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    if provider_plan.planning_provider_used:
        return replace(
            provider_plan,
            tool_plan=_annotate_task_plan_tool_input(
                provider_plan.tool_plan,
                registry_provider=registry_provider,
            ),
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    return ToolPlanArtifacts(
        tool_plan=fallback_plan,
        allowed_tool_names=allowed_tool_names,
        allowed_tool_labels=allowed_tool_labels,
        planning_prompt=provider_plan.planning_prompt,
        provider_usage=provider_plan.provider_usage,
        planning_provider_attempted=provider_plan.planning_provider_attempted,
        planning_provider_used=False,
    )


def build_tool_plan(
    prompt: str,
    *,
    provider: object | None = None,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]]:
    return build_tool_plan_artifacts(
        prompt,
        provider=provider,
        registry_provider=registry_provider,
    ).tool_plan
