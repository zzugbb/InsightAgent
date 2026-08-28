from __future__ import annotations

import codecs
import gzip
import inspect
import json
import math
import re
import zlib
from collections import UserString
from collections.abc import Callable, Iterator, Mapping, Sequence
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlencode, urlparse
from urllib.request import Request


def _runtime_module():
    from app.services import tool_runtime

    return tool_runtime


def _proxy(name: str):
    return getattr(_runtime_module(), name)


def _call_runtime(attr_name: str, *args, **kwargs):
    return _proxy(attr_name)(*args, **kwargs)


MockToolExecutionError = _proxy("MockToolExecutionError")
ToolRegistration = _proxy("ToolRegistration")
_HttpJsonScalarFallbackOutput = _proxy("_HttpJsonScalarFallbackOutput")
_HTTP_JSON_ALLOWED_METHODS = _proxy("_HTTP_JSON_ALLOWED_METHODS")
_HTTP_JSON_BARE_BEARER_TOKEN_RE = _proxy("_HTTP_JSON_BARE_BEARER_TOKEN_RE")
_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH = _proxy("_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH")
_HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE = _proxy("_HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE")
_HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE = _proxy("_HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE")
_HTTP_JSON_HEADER_NAME_RE = _proxy("_HTTP_JSON_HEADER_NAME_RE")
_HTTP_JSON_HEADER_VALUE_CONTROL_RE = _proxy("_HTTP_JSON_HEADER_VALUE_CONTROL_RE")
_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS = _proxy("_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS")
_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH = _proxy("_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH")
_HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE = _proxy("_HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE")
_HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE = _proxy("_HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE")
_HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS = _proxy("_HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS")
_HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES = _proxy("_HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES")
_HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS = _proxy("_HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS")
_HTTP_JSON_URL_CONTROL_OR_SPACE_RE = _proxy("_HTTP_JSON_URL_CONTROL_OR_SPACE_RE")
_HTTP_JSON_URL_TEXT_RE = _proxy("_HTTP_JSON_URL_TEXT_RE")
_TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE = _proxy("_TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE")
_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_FIELD_PATH_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_FIELD_PATH_RE")
_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_MAPPING_PATH_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_MAPPING_PATH_RE")
_TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE")
_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_BRACKET_SEGMENT_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_BRACKET_SEGMENT_RE")
_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_DOT_SEGMENT_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_DOT_SEGMENT_RE")
_TOOL_REGISTRY_DIAGNOSTIC_MAPPING_PATH_RE = _proxy("_TOOL_REGISTRY_DIAGNOSTIC_MAPPING_PATH_RE")
_TOOL_TIMEOUT_MAX_MS = _proxy("_TOOL_TIMEOUT_MAX_MS")


def _coerce_tool_registry_spec_payload(*args, **kwargs):
    return _call_runtime("_coerce_tool_registry_spec_payload", *args, **kwargs)


def _empty_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_runtime("_empty_tool_registry_file_diagnostics", *args, **kwargs)


def _normalize_named_tool_registry_component_name(*args, **kwargs):
    return _call_runtime("_normalize_named_tool_registry_component_name", *args, **kwargs)


def _parse_tool_registry_json_object_setting(*args, **kwargs):
    return _call_runtime("_parse_tool_registry_json_object_setting", *args, **kwargs)


def build_tool_registry(*args, **kwargs):
    return _call_runtime("build_tool_registry", *args, **kwargs)


def build_tool_registry_extra_tools_from_specs(*args, **kwargs):
    return _call_runtime("build_tool_registry_extra_tools_from_specs", *args, **kwargs)


def get_default_tool_registry(*args, **kwargs):
    return _call_runtime("get_default_tool_registry", *args, **kwargs)


def load_tool_registry_file_payload(*args, **kwargs):
    return _call_runtime("load_tool_registry_file_payload", *args, **kwargs)


def normalize_tool_registry_name(*args, **kwargs):
    return _call_runtime("normalize_tool_registry_name", *args, **kwargs)


def urlopen(*args, **kwargs):
    return _call_runtime("urlopen", *args, **kwargs)


def _normalize_result_preview_keys(raw_value: object) -> tuple[str, ...]:
    if not isinstance(raw_value, Sequence) or isinstance(
        raw_value,
        (str, bytes, bytearray, memoryview),
    ):
        return ()
    normalized_keys: list[str] = []
    seen_keys: set[str] = set()
    for raw_key in raw_value:
        raw_key = _coerce_tool_execution_string_like_value(raw_key)
        key = str(raw_key).strip()
        if not key or key in seen_keys:
            continue
        normalized_keys.append(key)
        seen_keys.add(key)
    return tuple(normalized_keys)


def _normalize_result_output_keys(raw_value: object) -> tuple[str, ...]:
    return _normalize_result_preview_keys(raw_value)


def _is_sensitive_result_key(raw_value: object) -> bool:
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(str(raw_value).strip()) is not None


def _normalize_safe_explicit_result_keys(
    raw_value: object,
    *,
    fallback_keys: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(raw_value, Sequence) or isinstance(
        raw_value,
        (str, bytes, bytearray, memoryview),
    ):
        return fallback_keys
    normalized_keys = _normalize_result_preview_keys(raw_value)
    if not normalized_keys:
        return fallback_keys
    return tuple(key for key in normalized_keys if not _is_sensitive_result_key(key))


def _normalize_runtime_semantic_kind(raw_value: object) -> str | None:
    if isinstance(raw_value, UserString):
        raw_value = str(raw_value)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def _normalize_tool_execution_kind(raw_value: object) -> str | None:
    if isinstance(raw_value, UserString):
        raw_value = str(raw_value)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    return normalized or None


def _build_tool_execution_runtime_template_context(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        return {}
    context: dict[str, object] = {}
    for attr_name, context_key in (
        ("mode", "settings_mode"),
        ("provider", "settings_provider"),
        ("model", "settings_model"),
        ("base_url", "settings_base_url"),
        ("api_key", "settings_api_key"),
        ("tool_registry_provider_source", "tool_registry_provider_source"),
        ("tool_registry_profile", "tool_registry_profile"),
    ):
        raw_value = getattr(settings, attr_name, None)
        if not isinstance(raw_value, str):
            continue
        normalized = raw_value.strip()
        if not normalized:
            continue
        context[context_key] = normalized
    return context


_SUPPORTED_TOOL_EXECUTION_RUNTIME_TEMPLATE_KEYS = frozenset(
    {
        "settings_mode",
        "settings_provider",
        "settings_model",
        "settings_base_url",
        "settings_api_key",
        "tool_registry_provider_source",
        "tool_registry_profile",
    }
)
_TOOL_EXECUTION_RUNTIME_TEMPLATE_RESERVED_PREFIXES = ("settings_", "tool_registry_")


_TOOL_EXECUTION_TEMPLATE_MISSING = object()


def _stringify_tool_execution_template_interpolation_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _clone_tool_execution_settings(
    *,
    settings: object,
    **updates: object,
) -> object:
    if isinstance(settings, dict):
        merged_values = dict(settings)
    elif hasattr(settings, "model_dump"):
        merged_values = dict(getattr(settings, "model_dump")())
    else:
        merged_values = dict(vars(settings))
    merged_values.update(updates)
    return SimpleNamespace(**merged_values)


def _render_tool_execution_template(
    value: object,
    *,
    context: dict[str, object],
) -> object:
    if isinstance(value, UserString):
        value = str(value)
    if isinstance(value, str):
        raw = value.strip()
        if "${" in value:
            missing_placeholder = False

            def replace_placeholder(match: re.Match[str]) -> str:
                nonlocal missing_placeholder
                lookup_key = match.group(1).strip()
                if not lookup_key or lookup_key not in context:
                    missing_placeholder = True
                    return ""
                return _stringify_tool_execution_template_interpolation_value(
                    context[lookup_key]
                )

            rendered_value = re.sub(r"\$\{([^{}]+)\}", replace_placeholder, value)
            if missing_placeholder:
                return _TOOL_EXECUTION_TEMPLATE_MISSING
            return rendered_value
        if raw.startswith("$") and len(raw) > 1:
            lookup_key = raw[1:]
            return (
                context[lookup_key]
                if lookup_key in context
                else _TOOL_EXECUTION_TEMPLATE_MISSING
            )
        return value
    if isinstance(value, Mapping):
        rendered_mapping: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            normalized_key = raw_key.strip()
            rendered_value = _render_tool_execution_template(
                raw_value,
                context=context,
            )
            if rendered_value is _TOOL_EXECUTION_TEMPLATE_MISSING or rendered_value is None:
                continue
            rendered_mapping[normalized_key] = rendered_value
        return rendered_mapping
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        rendered_items: list[object] = []
        for item in value:
            rendered_item = _render_tool_execution_template(item, context=context)
            if rendered_item is _TOOL_EXECUTION_TEMPLATE_MISSING:
                continue
            rendered_items.append(rendered_item)
        return rendered_items
    return value


def _iter_missing_tool_execution_template_variables(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> tuple[tuple[str, str], ...]:
    if isinstance(value, UserString):
        value = str(value)
    if isinstance(value, str):
        missing: list[tuple[str, str]] = []
        raw = value.strip()
        if raw.startswith("$") and len(raw) > 1 and not raw.startswith("${"):
            lookup_key = raw[1:]
            if lookup_key not in context:
                missing.append((path, lookup_key))
        for match in re.finditer(r"\$\{([^{}]+)\}", value):
            lookup_key = match.group(1).strip()
            if lookup_key and lookup_key not in context:
                missing.append((path, lookup_key))
        return tuple(missing)
    if isinstance(value, Mapping):
        missing: list[tuple[str, str]] = []
        for raw_key, raw_item in value.items():
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            child_path = f"{path}.{raw_key.strip()}" if path else raw_key.strip()
            missing.extend(
                _iter_missing_tool_execution_template_variables(
                    raw_item,
                    context=context,
                    path=child_path,
                )
            )
        return tuple(missing)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        missing: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            missing.extend(
                _iter_missing_tool_execution_template_variables(
                    item,
                    context=context,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(missing)
    return ()


def _render_required_tool_execution_template(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> object:
    missing_references = _iter_missing_tool_execution_template_variables(
        value,
        context=context,
        path=path,
    )
    if missing_references:
        formatted_references = tuple(
            dict.fromkeys(
                f"{_format_safe_tool_execution_template_variable_name(variable_name)} "
                f"in {_format_safe_tool_execution_diagnostic_path(reference_path)}"
                for reference_path, variable_name in missing_references
            )
        )
        qualifier = "variable" if len(formatted_references) == 1 else "variables"
        joined_references = "; ".join(formatted_references)
        raise MockToolExecutionError(
            "HTTP JSON tool request template references missing runtime template "
            f"{qualifier} {joined_references}.",
            fatal=True,
        )
    return _render_tool_execution_template(value, context=context)


def _render_tool_execution_template_for_static_analysis(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    analysis_context = context or {}
    missing_references = _iter_missing_tool_execution_template_variables(
        value,
        context=analysis_context,
        path=path,
    )
    if missing_references:
        return _TOOL_EXECUTION_TEMPLATE_MISSING
    return _render_tool_execution_template(value, context=analysis_context)


def _is_tool_execution_mapping_path_template(value: object) -> bool:
    value = _coerce_http_json_mapping_path_value(value)
    if not isinstance(value, str):
        return False
    raw = value.strip()
    return (
        bool(_TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE.fullmatch(raw))
        or "${" in value
    )


def _iter_tool_execution_mapping_path_template_variable_references(
    value: object,
    *,
    path: str,
) -> tuple[tuple[str, str], ...]:
    value = _coerce_http_json_mapping_path_value(value)
    if isinstance(value, str):
        references: list[tuple[str, str]] = []
        root_reference = _TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE.fullmatch(
            value.strip()
        )
        if root_reference:
            references.append((path, root_reference.group(1)))
        references.extend(
            (path, match.group(1).strip())
            for match in re.finditer(r"\$\{([^{}]+)\}", value)
            if match.group(1).strip()
        )
        return tuple(references)
    if isinstance(value, Mapping):
        references: list[tuple[str, str]] = []
        for raw_key, raw_item in value.items():
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            child_path = f"{path}.{raw_key.strip()}" if path else raw_key.strip()
            references.extend(
                _iter_tool_execution_mapping_path_template_variable_references(
                    raw_item,
                    path=child_path,
                )
            )
        return tuple(references)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        references: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            references.extend(
                _iter_tool_execution_mapping_path_template_variable_references(
                    item,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(references)
    return ()


def _iter_missing_tool_execution_mapping_path_template_variables(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (reference_path, variable_name)
        for reference_path, variable_name in (
            _iter_tool_execution_mapping_path_template_variable_references(
                value,
                path=path,
            )
        )
        if variable_name not in context
    )


def _render_required_tool_execution_mapping_path_template(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> object:
    missing_references = _iter_missing_tool_execution_mapping_path_template_variables(
        value,
        context=context,
        path=path,
    )
    if missing_references:
        formatted_references = tuple(
            dict.fromkeys(
                f"{_format_safe_tool_execution_template_variable_name(variable_name)} "
                f"in {_format_safe_tool_execution_diagnostic_path(reference_path)}"
                for reference_path, variable_name in missing_references
            )
        )
        qualifier = "variable" if len(formatted_references) == 1 else "variables"
        joined_references = "; ".join(formatted_references)
        raise MockToolExecutionError(
            "HTTP JSON tool request template references missing runtime template "
            f"{qualifier} {joined_references}.",
            fatal=True,
        )
    return _render_tool_execution_template(value, context=context)


def _render_tool_execution_mapping_path_template_for_static_analysis(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    analysis_context = context or {}
    missing_references = _iter_missing_tool_execution_mapping_path_template_variables(
        value,
        context=analysis_context,
        path=path,
    )
    if missing_references:
        return _TOOL_EXECUTION_TEMPLATE_MISSING
    return _render_tool_execution_template(value, context=analysis_context)


def _coerce_http_json_mapping_path_value(raw_value: object) -> object:
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, UserString):
        return str(raw_value)
    return raw_value


def _coerce_http_json_mapping_field_name(raw_value: object) -> object:
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, UserString):
        return str(raw_value)
    return raw_value


def _coerce_tool_execution_string_like_value(raw_value: object) -> object:
    if isinstance(raw_value, UserString):
        return str(raw_value)
    return raw_value


def _iter_http_json_mapping_field_names(raw_mapping: object) -> tuple[str, ...]:
    if not isinstance(raw_mapping, Mapping):
        return ()
    field_names: list[str] = []
    for raw_key in raw_mapping:
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        field_names.append(raw_key.strip())
    return tuple(field_names)


def _resolve_tool_execution_mapping_path_for_static_validation(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    if not _is_tool_execution_mapping_path_template(value):
        return _coerce_http_json_mapping_path_value(value)
    rendered_value = _render_tool_execution_mapping_path_template_for_static_analysis(
        value,
        context=context,
        path=path,
    )
    if rendered_value is _TOOL_EXECUTION_TEMPLATE_MISSING:
        return _TOOL_EXECUTION_TEMPLATE_MISSING
    return _coerce_http_json_mapping_path_value(rendered_value)


def _resolve_tool_execution_template_value_for_static_validation(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    if not _iter_tool_execution_template_variable_references(value, path=path):
        return value
    rendered_value = _render_tool_execution_template_for_static_analysis(
        value,
        context=context,
        path=path,
    )
    if rendered_value is _TOOL_EXECUTION_TEMPLATE_MISSING:
        return value
    return rendered_value


def _coerce_tool_execution_value_for_static_validation(value: object) -> object:
    try:
        return _coerce_http_json_json_compatible_body(value)
    except TypeError:
        return value


def _iter_tool_execution_template_variable_references(
    value: object,
    *,
    path: str,
) -> tuple[tuple[str, str], ...]:
    if isinstance(value, UserString):
        value = str(value)
    if isinstance(value, str):
        references: list[tuple[str, str]] = []
        raw = value.strip()
        if raw.startswith("$") and len(raw) > 1 and not raw.startswith("${"):
            references.append((path, raw[1:]))
        references.extend(
            (path, match.group(1).strip())
            for match in re.finditer(r"\$\{([^{}]+)\}", value)
            if match.group(1).strip()
        )
        return tuple(references)
    if isinstance(value, Mapping):
        references: list[tuple[str, str]] = []
        for raw_key, raw_item in value.items():
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            child_path = f"{path}.{raw_key.strip()}" if path else raw_key.strip()
            references.extend(
                _iter_tool_execution_template_variable_references(
                    raw_item,
                    path=child_path,
                )
            )
        return tuple(references)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        references: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            references.extend(
                _iter_tool_execution_template_variable_references(
                    item,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(references)
    return ()


def _is_tool_execution_root_template_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.strip()
    return bool(_TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE.fullmatch(raw))


def _collect_tool_execution_runtime_template_validation_errors(
    *,
    execution_spec: object,
) -> tuple[str, ...]:
    if not isinstance(execution_spec, dict):
        return ()
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind != "http_json":
        return ()
    references: list[tuple[str, str]] = []
    for field_name in (
        "url",
        "method",
        "timeout_ms",
        "headers",
        "query_params",
        "json_body",
    ):
        if field_name not in execution_spec:
            continue
        references.extend(
            _iter_tool_execution_template_variable_references(
                execution_spec.get(field_name),
                path=field_name,
            )
        )
    if "response_path" in execution_spec:
        references.extend(
            _iter_tool_execution_mapping_path_template_variable_references(
                execution_spec.get("response_path"),
                path="response_path",
            )
        )
    if "result_fields" in execution_spec:
        raw_result_fields = execution_spec.get("result_fields")
        if _is_tool_execution_root_template_reference(raw_result_fields):
            references.extend(
                _iter_tool_execution_template_variable_references(
                    raw_result_fields,
                    path="result_fields",
                )
            )
        elif isinstance(raw_result_fields, Mapping):
            references.extend(
                _iter_tool_execution_mapping_path_template_variable_references(
                    raw_result_fields,
                    path="result_fields",
                )
            )
    messages: list[str] = []
    for path, variable_name in references:
        if not variable_name.startswith(_TOOL_EXECUTION_RUNTIME_TEMPLATE_RESERVED_PREFIXES):
            continue
        if variable_name in _SUPPORTED_TOOL_EXECUTION_RUNTIME_TEMPLATE_KEYS:
            continue
        messages.append(
            "http_json execution references unsupported runtime template "
            "variable "
            f"{_format_safe_tool_execution_template_variable_name(variable_name)} "
            f"in {_format_safe_tool_execution_diagnostic_path(path)}"
        )
    return tuple(dict.fromkeys(messages))


def _normalize_tool_execution_http_method(raw_value: object) -> str:
    raw_value = _coerce_tool_execution_string_like_value(raw_value)
    if not isinstance(raw_value, str):
        return "GET"
    normalized = raw_value.strip().upper()
    if normalized in _HTTP_JSON_ALLOWED_METHODS:
        return normalized
    return "GET"


def _describe_tool_execution_http_method_validation_error(
    raw_value: object,
) -> str | None:
    raw_value = _coerce_tool_execution_string_like_value(raw_value)
    if not isinstance(raw_value, str):
        return (
            "http_json execution method must be one of "
            f"{', '.join(_HTTP_JSON_ALLOWED_METHODS)}"
        )
    normalized = raw_value.strip().upper()
    if normalized in _HTTP_JSON_ALLOWED_METHODS:
        return None
    return (
        "http_json execution method must be one of "
        f"{', '.join(_HTTP_JSON_ALLOWED_METHODS)}"
    )


def _is_supported_tool_timeout_ms(raw_value: object) -> bool:
    raw_value = _coerce_tool_execution_string_like_value(raw_value)
    if isinstance(raw_value, bool):
        return False
    if isinstance(raw_value, int):
        return 0 < raw_value <= _TOOL_TIMEOUT_MAX_MS
    if isinstance(raw_value, float):
        return (
            math.isfinite(raw_value)
            and raw_value.is_integer()
            and 1 <= raw_value <= _TOOL_TIMEOUT_MAX_MS
        )
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            coerced_timeout_ms = int(raw_value.strip())
        except ValueError:
            return False
        return 0 < coerced_timeout_ms <= _TOOL_TIMEOUT_MAX_MS
    return False


def _coerce_tool_execution_timeout_ms(
    raw_value: object,
    *,
    default_timeout_ms: int,
) -> int:
    if raw_value is None:
        return default_timeout_ms
    raw_value = _coerce_tool_execution_string_like_value(raw_value)
    if _is_supported_tool_timeout_ms(raw_value):
        return int(raw_value)
    return default_timeout_ms


def _describe_tool_execution_timeout_ms_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_timeout_ms(raw_value):
        return None
    return "http_json execution timeout_ms must be a positive number of milliseconds"


def _coerce_tool_default_timeout_ms(
    raw_value: object,
    *,
    fallback_timeout_ms: int,
) -> int:
    if _is_supported_tool_timeout_ms(raw_value):
        coerced_timeout_ms = int(raw_value)
        return coerced_timeout_ms
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            coerced_timeout_ms = int(raw_value.strip())
        except ValueError:
            return fallback_timeout_ms
        return (
            coerced_timeout_ms
            if _is_supported_tool_timeout_ms(coerced_timeout_ms)
            else fallback_timeout_ms
        )
    return fallback_timeout_ms


def _describe_tool_default_timeout_ms_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_timeout_ms(raw_value):
        return None
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            if _is_supported_tool_timeout_ms(int(raw_value.strip())):
                return None
        except ValueError:
            pass
    return "tool default_timeout_ms must be a positive number of milliseconds"


def _normalize_tool_execution_http_headers(raw_value: object) -> dict[str, str]:
    if not isinstance(raw_value, Mapping):
        return {}
    headers: dict[str, str] = {}
    for raw_key, raw_item in raw_value.items():
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        if raw_item is None:
            continue
        headers[raw_key.strip()] = str(raw_item)
    return headers


def _normalize_tool_execution_http_query_params(
    raw_value: object,
) -> dict[str, object]:
    if not isinstance(raw_value, Mapping):
        return {}
    query_params: dict[str, object] = {}
    for raw_key, raw_item in raw_value.items():
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        if raw_item is None:
            continue
        normalized_key = raw_key.strip()
        if isinstance(raw_item, Sequence) and not isinstance(
            raw_item, (str, bytes, bytearray, memoryview)
        ):
            query_params[normalized_key] = list(raw_item)
            continue
        query_params[normalized_key] = raw_item
    return query_params


def _is_supported_tool_execution_http_url(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    if _HTTP_JSON_URL_CONTROL_OR_SPACE_RE.search(raw_value):
        return False
    parsed_url = urlparse(raw_value.strip())
    try:
        parsed_url.port
    except ValueError:
        return False
    query_error = _describe_tool_execution_http_url_query_validation_error(
        parsed_url.query
    )
    path_error = _describe_tool_execution_http_url_path_validation_error(
        parsed_url.path
    )
    return (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
        and parsed_url.username is None
        and parsed_url.password is None
        and not parsed_url.fragment
        and query_error is None
        and path_error is None
    )


def _describe_tool_execution_http_url_path_validation_error(
    raw_value: object,
) -> str | None:
    if not isinstance(raw_value, str) or not raw_value:
        return None
    decoded_path = unquote(raw_value)
    if _HTTP_JSON_HEADER_VALUE_CONTROL_RE.search(decoded_path):
        return "http_json execution url path must not contain encoded control characters"
    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        return "http_json execution url path must not include dot segments"
    return None


def _describe_tool_execution_http_url_query_validation_error(
    raw_value: object,
) -> str | None:
    if not isinstance(raw_value, str) or not raw_value:
        return None
    seen_query_param_names: set[str] = set()
    for query_param_name, _query_param_value in parse_qsl(
        raw_value,
        keep_blank_values=True,
    ):
        if not _is_supported_tool_execution_http_query_param_name(query_param_name):
            return (
                "http_json execution url query parameters must use safe query "
                "parameter names"
            )
        if _http_header_value_contains_control_character(_query_param_value):
            return (
                "http_json execution url query parameter values must not contain "
                "control characters"
            )
        if query_param_name in seen_query_param_names:
            return (
                "http_json execution url query must not define duplicate parameter "
                "names"
            )
        seen_query_param_names.add(query_param_name)
    return None


def _iter_tool_execution_http_url_query_param_names(
    raw_url: object,
) -> tuple[str, ...]:
    if not isinstance(raw_url, str) or not raw_url.strip():
        return ()
    parsed_url = urlparse(raw_url.strip())
    if not parsed_url.query:
        return ()
    return tuple(
        query_param_name
        for query_param_name, _query_param_value in parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
    )


def _describe_tool_execution_http_duplicate_query_param_validation_error(
    *,
    url: object,
    query_params: object,
) -> str | None:
    if not isinstance(query_params, Mapping) or not query_params:
        return None
    url_query_param_names = {
        query_param_name
        for query_param_name in _iter_tool_execution_http_url_query_param_names(url)
        if _is_supported_tool_execution_http_query_param_name(query_param_name)
    }
    if not url_query_param_names:
        return None
    for raw_key in query_params:
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if (
            isinstance(raw_key, str)
            and _is_supported_tool_execution_http_query_param_name(raw_key)
            and raw_key in url_query_param_names
        ):
            return (
                "http_json execution url query and query_params must not define "
                "duplicate parameter names"
            )
    return None


def _describe_tool_execution_http_url_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_execution_http_url(raw_value):
        return None
    if isinstance(raw_value, str) and raw_value.strip():
        if _HTTP_JSON_URL_CONTROL_OR_SPACE_RE.search(raw_value):
            return "http_json execution url must not contain control characters or spaces"
        parsed_url = urlparse(raw_value.strip())
        if (
            parsed_url.scheme in {"http", "https"}
            and parsed_url.netloc
            and (parsed_url.username is not None or parsed_url.password is not None)
        ):
            return "http_json execution url must not include credentials"
        try:
            parsed_url.port
        except ValueError:
            return (
                "http_json execution url must include a valid port when port is provided"
            )
        if (
            parsed_url.scheme in {"http", "https"}
            and parsed_url.netloc
            and parsed_url.fragment
        ):
            return "http_json execution url must not include fragments"
        if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
            path_error = _describe_tool_execution_http_url_path_validation_error(
                parsed_url.path
            )
            if path_error:
                return path_error
            query_error = _describe_tool_execution_http_url_query_validation_error(
                parsed_url.query
            )
            if query_error:
                return query_error
    return "http_json execution url must be an absolute http(s) URL"


def _format_safe_tool_execution_http_url_origin(parsed_url: object) -> str | None:
    scheme = getattr(parsed_url, "scheme", "")
    hostname = getattr(parsed_url, "hostname", None)
    if scheme not in {"http", "https"} or not isinstance(hostname, str) or not hostname:
        return None
    try:
        port = getattr(parsed_url, "port", None)
    except ValueError:
        return None
    if isinstance(port, int):
        return f"{scheme}://{hostname}:{port}"
    return f"{scheme}://{hostname}"


def _format_safe_tool_execution_http_url_path(parsed_url: object) -> str | None:
    path = getattr(parsed_url, "path", "")
    if not isinstance(path, str) or not path:
        return None
    path = unquote(path)
    path = _redact_http_json_url_text(path)
    safe_segments: list[str] = []
    redact_next_segment = False
    for segment in path.split("/"):
        if not segment:
            safe_segments.append(segment)
            continue
        if redact_next_segment:
            safe_segments.append("[redacted]")
            redact_next_segment = False
            continue
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.fullmatch(segment):
            safe_segments.append("[redacted]")
            redact_next_segment = True
            continue
        redacted_segment = _redact_http_json_diagnostic_text(segment)
        safe_segments.append(redacted_segment)
    return "/".join(safe_segments)


def _format_safe_tool_execution_summary_field_name(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(normalized):
        return "[redacted]"
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        normalized,
    )


def _format_safe_tool_execution_diagnostic_path(raw_value: object) -> str:
    raw_path = str(raw_value).strip()
    if not raw_path:
        return ""
    path_segments = raw_path.split(".")
    root_segment = path_segments[0]
    safe_segments: list[str] = []
    for index, segment in enumerate(path_segments):
        if not segment:
            continue
        if index == 0:
            safe_segments.append(segment)
            continue
        bracket_index = segment.find("[")
        if bracket_index == -1:
            field_name = segment
            suffix = ""
        else:
            field_name = segment[:bracket_index]
            suffix = segment[bracket_index:]
        if not field_name:
            safe_segments.append(segment)
            continue
        if (
            not (root_segment == "headers" and field_name.lower() == "authorization")
            and _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(field_name)
        ):
            safe_segments.append(f"[redacted]{suffix}")
            continue
        safe_segments.append(segment)
    return ".".join(safe_segments)


def _format_safe_tool_execution_template_variable_name(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    return _format_safe_tool_execution_summary_field_name(normalized)


def _format_safe_tool_execution_kind(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    return _format_safe_tool_execution_summary_field_name(normalized)


def _raise_http_json_rendered_url_validation_error(raw_value: object) -> None:
    validation_error = _describe_tool_execution_http_url_validation_error(raw_value)
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_method_validation_error(raw_value: object) -> None:
    validation_error = _describe_tool_execution_http_method_validation_error(raw_value)
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_timeout_ms_validation_error(raw_value: object) -> None:
    validation_error = _describe_tool_execution_timeout_ms_validation_error(raw_value)
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_duplicate_query_param_validation_error(
    *,
    url: object,
    query_params: object,
) -> None:
    validation_error = (
        _describe_tool_execution_http_duplicate_query_param_validation_error(
            url=url,
            query_params=query_params,
        )
    )
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _is_supported_tool_execution_http_scalar_value(raw_value: object) -> bool:
    if raw_value is None:
        return False
    if isinstance(raw_value, bool):
        return True
    if isinstance(raw_value, int):
        return True
    if isinstance(raw_value, float):
        return math.isfinite(raw_value)
    return isinstance(raw_value, str)


def _is_supported_tool_execution_http_query_value(raw_value: object) -> bool:
    if _is_supported_tool_execution_http_scalar_value(raw_value):
        return True
    if isinstance(raw_value, Sequence) and not isinstance(
        raw_value, (str, bytes, bytearray, memoryview)
    ):
        return all(
            _is_supported_tool_execution_http_scalar_value(item)
            for item in raw_value
        )
    return False


def _is_supported_tool_execution_http_query_param_name(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or raw_value != raw_value.strip():
        return False
    return bool(raw_value) and not _HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE.search(
        raw_value
    )


def _is_supported_tool_execution_http_header_name(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or raw_value != raw_value.strip():
        return False
    return bool(_HTTP_JSON_HEADER_NAME_RE.fullmatch(raw_value))


def _http_header_value_contains_line_break(raw_value: object) -> bool:
    return isinstance(raw_value, str) and ("\r" in raw_value or "\n" in raw_value)


def _http_header_value_contains_control_character(raw_value: object) -> bool:
    return isinstance(raw_value, str) and bool(
        _HTTP_JSON_HEADER_VALUE_CONTROL_RE.search(raw_value)
    )


def _http_headers_contain_duplicate_names(headers: object) -> bool:
    if not isinstance(headers, Mapping):
        return False
    seen_header_names: set[str] = set()
    for raw_key in headers:
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        normalized_key = raw_key.strip().lower()
        if normalized_key in seen_header_names:
            return True
        seen_header_names.add(normalized_key)
    return False


def _get_tool_execution_http_header_value(
    headers: object,
    header_name: str,
) -> object | None:
    if not isinstance(headers, Mapping):
        return None
    normalized_header_name = header_name.strip().lower()
    for raw_key, raw_value in headers.items():
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if (
            isinstance(raw_key, str)
            and raw_key.strip().lower() == normalized_header_name
        ):
            return raw_value
    return None


def _is_supported_http_json_media_type(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    media_type = _split_http_json_header_parameters(raw_value)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _get_http_json_media_type_parameter_values(
    raw_value: object,
    parameter_name: str,
) -> tuple[str, ...]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ()
    parameter_values: list[str] = []
    for raw_part in _split_http_json_header_parameters(raw_value)[1:]:
        raw_name, separator, raw_parameter_value = raw_part.partition("=")
        if raw_name.strip().lower() != parameter_name:
            continue
        if separator != "=":
            parameter_values.append("")
            continue
        parameter_value = raw_parameter_value.strip().strip("\"'")
        parameter_values.append(parameter_value if parameter_value else "")
    return tuple(parameter_values)


def _http_json_header_value_has_balanced_quoted_parameters(raw_value: object) -> bool:
    if not isinstance(raw_value, str):
        return True
    quote_char: str | None = None
    escaped = False
    for char in raw_value:
        if escaped:
            escaped = False
            continue
        if quote_char is not None:
            if char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in ("'", '"'):
            quote_char = char
    return quote_char is None


def _is_supported_http_json_accept_header(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    for item in _split_http_json_header_values(raw_value):
        raw_parts = _split_http_json_header_parameters(item)
        if not raw_parts:
            continue
        media_type = raw_parts[0].strip().lower()
        json_compatible = (
            media_type in {"application/json", "application/*", "*/*"}
            or media_type.endswith("+json")
        )
        q_values: list[float] = []
        for raw_part in raw_parts[1:]:
            parameter_name, separator, parameter_value = raw_part.partition("=")
            if parameter_name.strip().lower() != "q":
                continue
            if separator != "=":
                q_values.append(0.0)
                continue
            try:
                q_values.append(float(parameter_value.strip().strip("\"'")))
            except ValueError:
                q_values.append(0.0)
        if not q_values:
            q_values = [1.0]
        if any(
            not math.isfinite(q_value) or q_value <= 0 or q_value > 1
            for q_value in q_values
        ):
            if json_compatible:
                return False
            continue
        if json_compatible:
            return True
    return False


def _format_http_json_request_content_type_validation_error(
    raw_value: object,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Content-Type must be application/json or "
        "a +json media type when json_body is defined: "
        f"{safe_content_type}"
    )


def _format_http_json_request_content_type_charset_validation_error(
    raw_value: object,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Content-Type charset must be utf-8 when "
        "json_body is defined: "
        f"{safe_content_type}"
    )


def _format_http_json_request_header_quote_validation_error(
    *,
    header_name: str,
    raw_value: object,
) -> str:
    safe_value = _format_http_json_error_body_preview(raw_value)
    return (
        f"http_json execution headers.{header_name} must use balanced quoted "
        f"parameters: {safe_value}"
    )


def _describe_http_json_request_content_type_validation_errors(
    *,
    headers: object,
) -> tuple[str, ...]:
    raw_content_type = _get_tool_execution_http_header_value(headers, "Content-Type")
    if raw_content_type is None:
        return ()
    if _iter_tool_execution_template_variable_references(
        raw_content_type,
        path="headers.Content-Type",
    ):
        return ()
    if isinstance(
        raw_content_type, str
    ) and not _http_json_header_value_has_balanced_quoted_parameters(raw_content_type):
        return (
            _format_http_json_request_header_quote_validation_error(
                header_name="Content-Type",
                raw_value=raw_content_type,
            ),
        )
    if not (
        isinstance(raw_content_type, str)
        and _is_supported_http_json_media_type(raw_content_type)
    ):
        return (_format_http_json_request_content_type_validation_error(raw_content_type),)
    charset_values = _get_http_json_media_type_parameter_values(
        raw_content_type,
        "charset",
    )
    normalized_charsets = {
        charset.lower().replace("_", "-")
        for charset in charset_values
    }
    if normalized_charsets and not normalized_charsets <= {"utf-8", "utf8"}:
        return (
            _format_http_json_request_content_type_charset_validation_error(
                raw_content_type
            ),
        )
    return ()


def _raise_http_json_rendered_request_content_type_validation_error(
    *,
    headers: object,
) -> None:
    validation_errors = _describe_http_json_request_content_type_validation_errors(
        headers=headers
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _ensure_http_json_request_content_type_header(
    headers: dict[str, str],
) -> None:
    if _get_tool_execution_http_header_value(headers, "Content-Type") is None:
        headers["Content-Type"] = "application/json"


def _format_http_json_request_accept_validation_error(raw_value: object) -> str:
    safe_accept = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Accept must allow application/json or "
        "a +json media type: "
        f"{safe_accept}"
    )


def _describe_http_json_request_accept_validation_errors(
    *,
    headers: object,
) -> tuple[str, ...]:
    raw_accept = _get_tool_execution_http_header_value(headers, "Accept")
    if raw_accept is None:
        return ()
    if _iter_tool_execution_template_variable_references(
        raw_accept,
        path="headers.Accept",
    ):
        return ()
    if isinstance(
        raw_accept, str
    ) and not _http_json_header_value_has_balanced_quoted_parameters(raw_accept):
        return (
            _format_http_json_request_header_quote_validation_error(
                header_name="Accept",
                raw_value=raw_accept,
            ),
        )
    if isinstance(raw_accept, str) and _is_supported_http_json_accept_header(
        raw_accept
    ):
        return ()
    return (_format_http_json_request_accept_validation_error(raw_accept),)


def _raise_http_json_rendered_request_accept_validation_error(
    *,
    headers: object,
) -> None:
    validation_errors = _describe_http_json_request_accept_validation_errors(
        headers=headers
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _ensure_http_json_request_accept_header(headers: dict[str, str]) -> None:
    if _get_tool_execution_http_header_value(headers, "Accept") is None:
        headers["Accept"] = "application/json"


def _describe_tool_execution_http_value_validation_errors(
    *,
    field_name: str,
    raw_mapping: object,
) -> tuple[str, ...]:
    if not isinstance(raw_mapping, Mapping):
        return ()
    validation_errors: list[str] = []
    if field_name == "headers" and _http_headers_contain_duplicate_names(
        raw_mapping
    ):
        validation_errors.append(
            "http_json execution headers must not include duplicate HTTP header names"
        )
    for raw_key, raw_item in raw_mapping.items():
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        normalized_key = raw_key.strip()
        safe_path = _format_safe_tool_execution_diagnostic_path(
            f"{field_name}.{normalized_key}"
        )
        if field_name == "headers":
            if not _is_supported_tool_execution_http_header_name(raw_key):
                validation_errors.append(
                    "http_json execution headers must use valid HTTP header names"
                )
                continue
            if not _is_supported_tool_execution_http_scalar_value(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must be a "
                    "string, number, or boolean"
                )
                continue
            if _http_header_value_contains_line_break(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must not contain CR or LF"
                )
                continue
            if _http_header_value_contains_control_character(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must not contain control characters"
                )
            continue
        if field_name == "query_params":
            if not _is_supported_tool_execution_http_query_param_name(raw_key):
                validation_errors.append(
                    f"http_json execution {safe_path} must use safe query parameter names"
                )
                continue
            if not _is_supported_tool_execution_http_query_value(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must be a "
                    "string, number, boolean, or list of those values"
                )
    return tuple(validation_errors)


def _format_tool_execution_json_body_child_path(path: str, raw_key: str) -> str:
    normalized_key = raw_key.strip()
    if re.fullmatch(r"[A-Za-z_][0-9A-Za-z_]*", normalized_key):
        return _format_safe_tool_execution_diagnostic_path(f"{path}.{normalized_key}")
    return f"{path}.<field>"


def _describe_tool_execution_json_body_validation_errors(
    raw_value: object,
    *,
    path: str = "json_body",
) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, bool):
        return ()
    if isinstance(raw_value, int):
        return ()
    if isinstance(raw_value, float):
        if math.isfinite(raw_value):
            return ()
        return (f"http_json execution {path} must be valid JSON",)
    if isinstance(raw_value, str):
        return ()
    if isinstance(raw_value, Mapping):
        validation_errors: list[str] = []
        for raw_key, raw_item in raw_value.items():
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(raw_key, str) or not raw_key.strip():
                if path != "json_body":
                    validation_errors.append(
                        f"http_json execution {path} must use non-empty string object field names"
                    )
                continue
            validation_errors.extend(
                _describe_tool_execution_json_body_validation_errors(
                    raw_item,
                    path=_format_tool_execution_json_body_child_path(path, raw_key),
                )
            )
        return tuple(validation_errors)
    if isinstance(raw_value, Sequence) and not isinstance(
        raw_value, (str, bytes, bytearray, memoryview)
    ):
        validation_errors = []
        for index, raw_item in enumerate(raw_value):
            validation_errors.extend(
                _describe_tool_execution_json_body_validation_errors(
                    raw_item,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(validation_errors)
    return (f"http_json execution {path} must be valid JSON",)


def _raise_http_json_rendered_value_validation_error(
    *,
    field_name: str,
    raw_mapping: object,
) -> None:
    validation_errors = _describe_tool_execution_http_value_validation_errors(
        field_name=field_name,
        raw_mapping=raw_mapping,
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_json_body_validation_error(raw_value: object) -> None:
    validation_errors = _describe_tool_execution_json_body_validation_errors(raw_value)
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_response_path_validation_error(raw_value: object) -> None:
    if raw_value is None:
        return
    if not isinstance(raw_value, str):
        raise MockToolExecutionError(
            "HTTP JSON tool response_path must resolve to a string.",
            fatal=True,
        )
    if not raw_value.strip():
        raise MockToolExecutionError(
            "HTTP JSON tool response_path must be a non-empty string when provided.",
            fatal=True,
        )
    if not _is_supported_tool_execution_response_path(raw_value):
        raise MockToolExecutionError(
            "HTTP JSON tool response_path must use dot fields and numeric indexes.",
            fatal=True,
        )


def _render_http_json_response_path(
    raw_value: object,
    *,
    context: dict[str, object],
) -> object:
    if raw_value is not None and _is_tool_execution_mapping_path_template(raw_value):
        raw_value = _render_required_tool_execution_mapping_path_template(
            raw_value,
            context=context,
            path="response_path",
        )
    raw_value = _coerce_http_json_mapping_path_value(raw_value)
    _raise_http_json_rendered_response_path_validation_error(raw_value)
    return raw_value


def _raise_http_json_rendered_result_field_validation_error(
    *,
    diagnostic_path: str,
    raw_value: object,
) -> None:
    safe_path = _format_safe_tool_execution_diagnostic_path(diagnostic_path)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise MockToolExecutionError(
            f"HTTP JSON tool {safe_path} must be a non-empty string path.",
            fatal=True,
        )
    if not _is_supported_tool_execution_response_path(raw_value):
        raise MockToolExecutionError(
            f"HTTP JSON tool {safe_path} must use dot fields and numeric indexes.",
            fatal=True,
        )


def _render_http_json_result_fields(
    raw_value: object,
    *,
    context: dict[str, object],
) -> dict[str, object] | None:
    if raw_value is None:
        return None
    if _is_tool_execution_root_template_reference(raw_value):
        raw_value = _render_required_tool_execution_template(
            raw_value,
            context=context,
            path="result_fields",
        )
        try:
            raw_value = _coerce_http_json_json_compatible_body(raw_value)
        except TypeError as exc:
            raise MockToolExecutionError(
                "HTTP JSON tool result_fields must resolve to an object.",
                fatal=True,
            ) from exc
    if not isinstance(raw_value, Mapping):
        raise MockToolExecutionError(
            "HTTP JSON tool result_fields must be an object.",
            fatal=True,
        )
    rendered_result_fields: dict[str, object] = {}
    has_blank_result_field_name = False
    for raw_key, raw_path in raw_value.items():
        raw_key = _coerce_http_json_mapping_field_name(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            has_blank_result_field_name = True
            continue
        normalized_key = raw_key.strip()
        rendered_path = raw_path
        diagnostic_path = f"result_fields.{normalized_key}"
        if _is_tool_execution_mapping_path_template(rendered_path):
            rendered_path = _render_required_tool_execution_mapping_path_template(
                rendered_path,
                context=context,
                path=diagnostic_path,
            )
        rendered_path = _coerce_http_json_mapping_path_value(rendered_path)
        _raise_http_json_rendered_result_field_validation_error(
            diagnostic_path=diagnostic_path,
            raw_value=rendered_path,
        )
        rendered_result_fields[normalized_key] = rendered_path
    if not raw_value:
        raise MockToolExecutionError(
            "HTTP JSON tool result_fields must include at least one field mapping.",
            fatal=True,
        )
    if has_blank_result_field_name and rendered_result_fields:
        raise MockToolExecutionError(
            "HTTP JSON tool result_fields must not include blank field names.",
            fatal=True,
        )
    if raw_value and not rendered_result_fields:
        raise MockToolExecutionError(
            "HTTP JSON tool result_fields must include at least one non-empty field name.",
            fatal=True,
        )
    return rendered_result_fields


def _parse_tool_execution_response_path_quoted_key(raw_value: str) -> str | None:
    raw_value = raw_value.strip()
    if len(raw_value) < 2 or raw_value[0] not in ("'", '"'):
        return None
    quote = raw_value[0]
    if raw_value[-1] != quote:
        return None
    if quote == '"':
        try:
            parsed_value = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed_value, str):
            return None
        key = parsed_value
    else:
        key = raw_value[1:-1]
        if "\\" in key:
            return None
    if not key or any(ord(char) < 32 or ord(char) == 127 for char in key):
        return None
    return key


def _parse_tool_execution_response_path_tokens(raw_value: object) -> list[object] | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if normalized == "$":
        return []
    if normalized.startswith("$"):
        normalized = normalized[1:]
    if normalized.startswith("."):
        normalized = normalized[1:]
    if not normalized:
        return None
    parts: list[object] = []
    index = 0
    expect_token = True
    while index < len(normalized):
        char = normalized[index]
        if char == ".":
            if expect_token:
                return None
            expect_token = True
            index += 1
            if index >= len(normalized):
                return None
            continue
        if char == "[":
            closing_index = normalized.find("]", index + 1)
            if closing_index == -1:
                return None
            raw_segment = normalized[index + 1 : closing_index]
            if raw_segment.isdigit():
                parts.append(int(raw_segment))
            else:
                key = _parse_tool_execution_response_path_quoted_key(raw_segment)
                if key is None:
                    return None
                parts.append(key)
            expect_token = False
            index = closing_index + 1
            continue
        start_index = index
        while index < len(normalized) and normalized[index] not in ".[]":
            index += 1
        if start_index == index:
            return None
        parts.append(normalized[start_index:index])
        expect_token = False
    if expect_token:
        return None
    return parts


def _is_supported_tool_execution_response_path_segment(segment: str) -> bool:
    if not isinstance(segment, str) or not segment:
        return False
    return _parse_tool_execution_response_path_tokens(segment) is not None


def _is_supported_tool_execution_response_path(raw_value: object) -> bool:
    return _parse_tool_execution_response_path_tokens(raw_value) is not None


def _normalize_tool_execution_response_path(raw_value: object) -> list[object]:
    return _parse_tool_execution_response_path_tokens(raw_value) or []


def _extract_tool_execution_response_value(
    payload: object,
    *,
    path: object,
) -> object:
    path_tokens = _normalize_tool_execution_response_path(path)
    if not path_tokens:
        return payload
    current = payload
    for token in path_tokens:
        if isinstance(token, int):
            if not isinstance(current, (list, tuple)) or token >= len(current):
                return _TOOL_EXECUTION_TEMPLATE_MISSING
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            return _TOOL_EXECUTION_TEMPLATE_MISSING
        current = current[token]
    return current


def _normalize_nonnegative_int_count_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if value >= 0:
            return value
        return None
    if isinstance(value, float):
        if value >= 0 and value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        normalized_value = value.strip()
        if normalized_value.isdigit():
            return int(normalized_value)
        if "," in normalized_value:
            parts = normalized_value.split(",")
            if (
                parts
                and parts[0].isdigit()
                and 1 <= len(parts[0]) <= 3
                and all(len(part) == 3 and part.isdigit() for part in parts[1:])
            ):
                return int("".join(parts))
        if "." in normalized_value:
            whole_part, fractional_part = normalized_value.split(".", 1)
            if (
                whole_part.isdigit()
                and fractional_part
                and all(char == "0" for char in fractional_part)
            ):
                return int(whole_part)
    return None


_HTTP_JSON_RETRIEVAL_COUNT_ALIAS_FIELDS = (
    "@odata.count",
    "odata_count",
    "odataCount",
    "documents_total_count",
    "documents_count",
    "documentsCount",
    "documentsTotal",
    "total_documents",
    "totalDocuments",
    "document_count",
    "documentCount",
    "doc_count",
    "docCount",
    "docs_count",
    "docsCount",
    "records_total",
    "recordsTotal",
    "record_total",
    "recordTotal",
    "records_count",
    "recordsCount",
    "record_count",
    "recordCount",
    "estimated_total_hits",
    "estimatedTotalHits",
    "nb_hits",
    "nbHits",
    "total_hits",
    "totalHits",
    "total_records",
    "totalRecords",
    "hit_count",
    "hitCount",
    "total_count",
    "totalCount",
    "number_of_results",
    "numberOfResults",
    "total_estimated_matches",
    "totalEstimatedMatches",
    "total_results",
    "totalResults",
    "total-results",
    "total",
    "count",
)
_HTTP_JSON_RETRIEVAL_COUNT_CONTAINER_FIELDS = (
    "search_information",
    "searchInformation",
    "metadata",
    "meta",
    "pageInfo",
    "page_info",
    "page",
    "pagination",
    "paging",
)
_HTTP_JSON_RETRIEVAL_LIST_CONTAINER_FIELDS = (
    "edges",
    "nodes",
    "documents",
    "items",
    "result",
    "results",
    "hits",
    "matches",
    "organic",
    "organic_results",
    "organicResults",
    "search_results",
    "searchResults",
    "citations",
    "citation_results",
    "citationResults",
    "points",
    "source_nodes",
    "sourceNodes",
    "data",
    "records",
    "value",
    "idlist",
    "idList",
)
_HTTP_JSON_RETRIEVAL_NESTED_CONTAINER_FIELDS = (
    "data",
    "payload",
    "result",
    "response",
    "message",
    "esearchresult",
    "eSearchResult",
    "resultList",
    "result_list",
    "web",
    "webPages",
    "web_pages",
    "queries",
    "Get",
    "get",
)


def _flatten_http_json_retrieval_sequence(
    raw_value: Sequence[object],
) -> Sequence[object]:
    flattened_items: list[object] = []
    saw_nested_sequence = False
    for raw_item in raw_value:
        if isinstance(raw_item, (str, bytes, bytearray, memoryview)):
            flattened_items.append(raw_item)
            continue
        if isinstance(raw_item, (list, tuple)):
            saw_nested_sequence = True
            flattened_items.extend(raw_item)
            continue
        flattened_items.append(raw_item)
    if not saw_nested_sequence:
        return raw_value
    return tuple(flattened_items)


def _extract_http_json_retrieval_list_from_container(
    raw_value: object,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> Sequence[object] | None:
    if depth > 4:
        return None
    if isinstance(raw_value, (str, bytes, bytearray, memoryview)):
        return None
    if isinstance(raw_value, (list, tuple)):
        return _flatten_http_json_retrieval_sequence(raw_value)
    if not isinstance(raw_value, Mapping):
        return None
    if visited is None:
        visited = set()
    value_id = id(raw_value)
    if value_id in visited:
        return None
    visited.add(value_id)
    for field_name in _HTTP_JSON_RETRIEVAL_LIST_CONTAINER_FIELDS:
        nested_value = raw_value.get(field_name)
        if isinstance(nested_value, (list, tuple)):
            return _flatten_http_json_retrieval_sequence(nested_value)
    for field_name in _HTTP_JSON_RETRIEVAL_NESTED_CONTAINER_FIELDS:
        nested_value = raw_value.get(field_name)
        if not isinstance(nested_value, Mapping):
            continue
        nested_list = _extract_http_json_retrieval_list_from_container(
            nested_value,
            depth=depth + 1,
            visited=visited,
        )
        if nested_list is not None:
            return nested_list
    if len(raw_value) == 1:
        nested_value = next(iter(raw_value.values()))
        if isinstance(nested_value, (list, tuple)):
            return _flatten_http_json_retrieval_sequence(nested_value)
        if isinstance(nested_value, Mapping):
            return _extract_http_json_retrieval_list_from_container(
                nested_value,
                depth=depth + 1,
                visited=visited,
            )
    return None


def _extract_http_json_retrieval_count_from_container(raw_value: object) -> int | None:
    if not isinstance(raw_value, Mapping):
        return None
    nested_list = _extract_http_json_retrieval_list_from_container(raw_value)
    if nested_list is None:
        return None
    alias_count = _extract_http_json_retrieval_count_alias_from_mapping(raw_value)
    if alias_count is not None:
        return alias_count
    return len(nested_list)


def _extract_http_json_retrieval_count_from_nested_containers(
    raw_value: object,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> int | None:
    if depth > 4 or not isinstance(raw_value, Mapping):
        return None
    if visited is None:
        visited = set()
    value_id = id(raw_value)
    if value_id in visited:
        return None
    visited.add(value_id)
    has_direct_list_container = any(
        isinstance(raw_value.get(field_name), (list, tuple))
        for field_name in _HTTP_JSON_RETRIEVAL_LIST_CONTAINER_FIELDS
    )
    if has_direct_list_container:
        nested_count = _extract_http_json_retrieval_count_from_container(raw_value)
        if nested_count is not None:
            return nested_count
    for nested_value in raw_value.values():
        if not isinstance(nested_value, Mapping):
            continue
        nested_count = _extract_http_json_retrieval_count_from_nested_containers(
            nested_value,
            depth=depth + 1,
            visited=visited,
        )
        if nested_count is not None:
            return nested_count
    nested_count = _extract_http_json_retrieval_count_from_container(raw_value)
    if nested_count is not None:
        return nested_count
    return None


def _extract_http_json_retrieval_count_alias_from_mapping(
    raw_value: Mapping,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> int | None:
    if depth > 4:
        return None
    if visited is None:
        visited = set()
    value_id = id(raw_value)
    if value_id in visited:
        return None
    visited.add(value_id)
    for alias_name in _HTTP_JSON_RETRIEVAL_COUNT_ALIAS_FIELDS:
        alias_value = raw_value.get(alias_name)
        alias_count = _normalize_nonnegative_int_count_value(alias_value)
        if alias_count is None and isinstance(alias_value, Mapping):
            for nested_alias_name in ("value", "count", "total", "totalCount"):
                alias_count = _normalize_nonnegative_int_count_value(
                    alias_value.get(nested_alias_name)
                )
                if alias_count is not None:
                    break
        if alias_count is not None:
            return alias_count
    for container_name in _HTTP_JSON_RETRIEVAL_COUNT_CONTAINER_FIELDS:
        nested_container = raw_value.get(container_name)
        if isinstance(nested_container, Mapping):
            alias_count = _extract_http_json_retrieval_count_alias_from_mapping(
                nested_container,
                depth=depth + 1,
                visited=visited,
            )
        elif isinstance(nested_container, (list, tuple)):
            alias_count = None
            for nested_item in nested_container:
                if not isinstance(nested_item, Mapping):
                    continue
                alias_count = _extract_http_json_retrieval_count_alias_from_mapping(
                    nested_item,
                    depth=depth + 1,
                    visited=visited,
                )
                if alias_count is not None:
                    break
        else:
            alias_count = None
        if alias_count is not None:
            return alias_count
    for container_name in _HTTP_JSON_RETRIEVAL_NESTED_CONTAINER_FIELDS:
        nested_container = raw_value.get(container_name)
        if not isinstance(nested_container, Mapping):
            continue
        alias_count = _extract_http_json_retrieval_count_alias_from_mapping(
            nested_container,
            depth=depth + 1,
            visited=visited,
        )
        if alias_count is not None:
            return alias_count
        for nested_value in nested_container.values():
            if isinstance(nested_value, Mapping):
                alias_count = _extract_http_json_retrieval_count_alias_from_mapping(
                    nested_value,
                    depth=depth + 1,
                    visited=visited,
                )
            elif isinstance(nested_value, (list, tuple)):
                alias_count = None
                for nested_item in nested_value:
                    if not isinstance(nested_item, Mapping):
                        continue
                    alias_count = _extract_http_json_retrieval_count_alias_from_mapping(
                        nested_item,
                        depth=depth + 1,
                        visited=visited,
                    )
                    if alias_count is not None:
                        break
            else:
                alias_count = None
            if alias_count is not None:
                return alias_count
    return None


def _http_json_output_implies_retrieval_count(output: dict[str, object]) -> bool:
    semantic_hints = (
        output.get("tool_kind"),
        output.get("semantic_kind"),
        output.get("semantic_family"),
        output.get("kind"),
    )
    for hint in semantic_hints:
        if not isinstance(hint, str):
            continue
        normalized_hint = hint.strip().lower()
        if any(
            token in normalized_hint
            for token in ("retrieval", "search", "knowledge", "document")
        ):
            return True
    return any(
        key in output
        for key in (
            "knowledge_base_id",
            "documents",
            "items",
            "hits",
            "results",
            "matches",
            "organic",
            "resultList",
            "result_list",
        )
    ) or any(
        isinstance(output.get(key), Mapping)
        and _extract_http_json_retrieval_list_from_container(output.get(key))
        is not None
        for key in ("data", "result", "resultList", "result_list", "response")
    )


def _http_json_output_implies_calculator_result(output: dict[str, object]) -> bool:
    semantic_hints = (
        output.get("tool_kind"),
        output.get("semantic_kind"),
        output.get("semantic_family"),
        output.get("kind"),
    )
    for hint in semantic_hints:
        if not isinstance(hint, str):
            continue
        normalized_hint = hint.strip().lower()
        if any(token in normalized_hint for token in ("calc", "calculator", "math")):
            return True
    return "expression" in output


def _get_safe_http_json_request_id_alias(output: dict[str, object]) -> str | None:
    for alias_name in (
        "requestId",
        "requestID",
        "request-id",
        "trace_id",
        "traceId",
        "correlation_id",
        "correlationId",
        "x_request_id",
        "x-request-id",
    ):
        safe_request_id = _get_safe_http_json_request_id_display_value(
            output.get(alias_name)
        )
        if safe_request_id is not None:
            return safe_request_id
    for container_name in (
        "search_metadata",
        "searchMetadata",
        "metadata",
        "meta",
        "extensions",
    ):
        nested_container = output.get(container_name)
        if not isinstance(nested_container, Mapping):
            continue
        for alias_name in ("request_id", "requestId", "requestID", "id", "traceId"):
            safe_request_id = _get_safe_http_json_request_id_display_value(
                nested_container.get(alias_name)
            )
            if safe_request_id is not None:
                return safe_request_id
    return None


def _normalize_http_json_output_shape(output: dict[str, object]) -> dict[str, object]:
    normalized_output = dict(output)
    if "request_id" in normalized_output:
        safe_request_id = _get_safe_http_json_request_id_display_value(
            normalized_output.get("request_id")
        )
        if safe_request_id is None:
            normalized_output.pop("request_id", None)
        else:
            normalized_output["request_id"] = safe_request_id
    else:
        safe_request_id = _get_safe_http_json_request_id_alias(normalized_output)
        if safe_request_id is not None:
            normalized_output["request_id"] = safe_request_id
    if (
        "result" not in normalized_output
        and _http_json_output_implies_calculator_result(normalized_output)
    ):
        for alias_name in (
            "value",
            "answer",
            "result_value",
            "resultValue",
            "computed_value",
            "computedValue",
        ):
            if alias_name in normalized_output:
                normalized_output["result"] = normalized_output[alias_name]
                break
    raw_documents_total = normalized_output.get("documents_total")
    had_documents_total = "documents_total" in normalized_output
    documents_total = _normalize_nonnegative_int_count_value(raw_documents_total)
    if documents_total is not None:
        normalized_output["documents_total"] = documents_total
    else:
        if had_documents_total:
            normalized_output.pop("documents_total", None)
        if _http_json_output_implies_retrieval_count(normalized_output):
            root_count = _extract_http_json_retrieval_count_alias_from_mapping(
                normalized_output
            )
            if root_count is not None:
                normalized_output["documents_total"] = root_count
        list_alias_names = ("documents", "items")
        if _http_json_output_implies_retrieval_count(normalized_output):
            list_alias_names = (*list_alias_names, "data", "records")
        for alias_name in list_alias_names:
            if "documents_total" in normalized_output:
                break
            alias_value = normalized_output.get(alias_name)
            if isinstance(alias_value, (list, tuple)):
                normalized_output["documents_total"] = len(
                    _flatten_http_json_retrieval_sequence(alias_value)
                )
                break
            nested_count = _extract_http_json_retrieval_count_from_nested_containers(
                alias_value
            )
            if nested_count is not None:
                normalized_output["documents_total"] = nested_count
                break
            connection_count = _extract_http_json_retrieval_count_from_container(
                alias_value
            )
            if connection_count is not None:
                normalized_output["documents_total"] = connection_count
                break
        if (
            "documents_total" not in normalized_output
            and _http_json_output_implies_retrieval_count(normalized_output)
        ):
            for alias_name in _HTTP_JSON_RETRIEVAL_COUNT_ALIAS_FIELDS:
                alias_count = _normalize_nonnegative_int_count_value(
                    normalized_output.get(alias_name)
                )
                if alias_count is not None:
                    normalized_output["documents_total"] = alias_count
                    break
        if "documents_total" not in normalized_output and had_documents_total:
            normalized_output["documents_total"] = raw_documents_total
    hit_count = _normalize_nonnegative_int_count_value(
        normalized_output.get("hit_count")
    )
    if hit_count is not None:
        normalized_output["hit_count"] = hit_count
    else:
        hit_list_alias_names = ("hits", "results", "matches")
        if _http_json_output_implies_retrieval_count(normalized_output):
            hit_list_alias_names = (
                *hit_list_alias_names,
                "data",
                "records",
                "organic",
                "resultList",
                "result_list",
            )
        for alias_name in hit_list_alias_names:
            alias_value = normalized_output.get(alias_name)
            if isinstance(alias_value, (list, tuple)):
                normalized_output["hit_count"] = len(
                    _flatten_http_json_retrieval_sequence(alias_value)
                )
                break
            nested_list = _extract_http_json_retrieval_list_from_container(alias_value)
            if nested_list is not None:
                normalized_output["hit_count"] = len(nested_list)
                break
        if "hit_count" not in normalized_output:
            for alias_name in (
                "hits_count",
                "hitsCount",
                "hitCount",
                "hit_total",
                "hitTotal",
                "total_hits",
                "totalHits",
                "total_matches",
                "totalMatches",
                "results_count",
                "resultsCount",
                "result_count",
                "resultCount",
                "matches_count",
                "matchesCount",
                "match_count",
                "matchCount",
            ):
                alias_count = _normalize_nonnegative_int_count_value(
                    normalized_output.get(alias_name)
                )
                if alias_count is not None:
                    normalized_output["hit_count"] = alias_count
                    break
    return normalized_output


from app.services.tool_runtime_http_json_response import (
    _redact_http_json_sensitive_payload_text,
    _format_safe_http_json_payload_key,
    _redact_http_json_sensitive_payload_value,
    _normalize_http_json_safe_output_shape,
    _normalize_tool_result_projection_output,
    _redact_http_json_diagnostic_text,
    _format_safe_http_json_url_query,
    _format_safe_http_json_url_fragment,
    _format_safe_http_json_url_text,
    _redact_http_json_url_text,
    _redact_tool_registry_diagnostic_mapping_paths,
    _redact_tool_registry_diagnostic_bracket_field_paths,
    _format_safe_tool_execution_bracket_jsonpath,
    _redact_tool_registry_diagnostic_bracket_mapping_paths,
    _redact_tool_registry_diagnostic_value,
    _redact_http_json_raw_fallback_value,
    _redact_http_json_error_body_value,
    _coerce_http_json_error_body_preview_text,
    _format_http_json_error_body_preview,
    _coerce_http_json_body_preview_bytes,
    _format_http_json_response_body_preview,
    _append_http_json_response_header_diagnostic_hints,
    _format_http_json_http_error,
    _coerce_http_json_response_status_code,
    _http_json_response_status_value_is_present,
    _format_http_json_invalid_status_response,
    _get_http_json_adapter_attr,
    _call_http_json_adapter_method,
    _call_http_json_getheader_adapter,
    _get_http_json_response_status_code,
    _coerce_http_json_response_text,
    _get_http_json_response_reason,
    _get_http_json_response_url,
    _HTTP_JSON_UNRESERVED_URL_CHARS,
    _normalize_http_json_unreserved_percent_encoding,
    _normalize_http_json_query_for_drift_check,
    _normalize_http_json_url_for_drift_check,
    _http_json_response_url_matches_request_url,
    _format_http_json_redirected_response_url_error,
    _format_http_json_unexpected_status_response,
    _format_http_json_unexpected_status_response_body_decode_error,
    _format_http_json_empty_response,
    _coerce_http_json_response_body_bytes,
    _HTTP_JSON_BODY_DUMP_MISSING,
    _HttpJsonJsonBodyDumpMethodUnavailable,
    _HttpJsonJsonBodyDumpJsonMethodUnavailable,
    _HttpJsonResponseBodyAttrUnavailable,
    _is_http_json_parsed_body_attr,
    _read_http_json_response_body_attr,
    _coerce_http_json_json_compatible_body,
    _coerce_http_json_json_compatible_mapping_key,
    _call_http_json_json_body_dump_method,
    _http_json_callable_accepts_call,
    _call_http_json_json_body_dump_json_method,
    _coerce_http_json_json_body_dump_json_compatible,
    _read_http_json_json_body_dump_json_bytes,
    _coerce_http_json_response_json_body_bytes,
    _HttpJsonResponseBodyInitialReadTypeError,
    _read_http_json_response_body_chunked,
    _HttpJsonResponseBodyInitialIteratorTypeError,
    _HttpJsonResponseBodyIteratorUnavailable,
    _read_http_json_response_body_chunks,
    _read_http_json_response_body_iterator,
    _read_http_json_response_body_bytes,
    _close_http_json_response,
    _format_http_json_invalid_json_response,
    _format_http_json_invalid_charset_response,
    _coerce_http_json_header_text,
    _coerce_http_json_header_name_text,
    _get_http_json_header_items,
    _get_http_json_header_value_from_method,
    _get_http_json_header_text_from_mapping,
    _get_http_json_response_header_text,
    _format_http_json_response_header_diagnostic_hints,
    _get_http_json_response_request_id,
    _is_safe_http_json_request_id_value,
    _get_safe_http_json_request_id_display_value,
    _attach_http_json_response_request_id,
    _get_http_json_response_content_type,
    _get_http_json_response_content_encoding,
    _split_http_json_header_value,
    _split_http_json_header_values,
    _split_http_json_header_parameters,
    _get_http_json_response_charset,
    _decode_http_json_response_text,
    _normalize_http_json_content_encodings,
    _decompress_http_json_deflate_body,
    _decode_http_json_response_body_for_content_encoding,
    _is_supported_http_json_response_content_type,
    _format_http_json_invalid_content_type_response,
    _format_http_json_transport_error,
    _format_http_json_mapping_path_for_error,
    _format_http_json_mapping_payload_shape_key_for_error,
    _format_http_json_mapping_payload_shape_keys_for_error,
    _format_http_json_mapping_payload_shape_for_error,
    _format_http_json_result_field_mapping_error,
    _format_http_json_missing_result_field_mappings,
)



def _build_http_json_tool_runner(
    *,
    execution_spec: dict[str, object],
    default_timeout_ms: int,
    template_context: dict[str, object] | None = None,
) -> ToolRunner:
    raw_method = execution_spec.get(
        "method",
        "POST" if execution_spec.get("json_body") else "GET",
    )
    raw_headers = execution_spec.get("headers")
    raw_query_params = execution_spec.get("query_params")
    raw_json_body = execution_spec.get("json_body")
    raw_response_path = execution_spec.get("response_path")
    raw_result_fields = execution_spec.get("result_fields")
    raw_timeout_ms = execution_spec.get("timeout_ms")

    def runner(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
        raw_url = _coerce_tool_execution_string_like_value(execution_spec.get("url"))
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise MockToolExecutionError(
                "HTTP JSON tool requires a non-empty url.",
                fatal=True,
            )
        context = {
            **(template_context or {}),
            **tool_input,
            "prompt": prompt,
            "user_id": user_id,
        }
        rendered_url = _render_required_tool_execution_template(
            raw_url,
            context=context,
            path="url",
        )
        rendered_url = _coerce_tool_execution_string_like_value(rendered_url)
        if not isinstance(rendered_url, str) or not rendered_url.strip():
            raise MockToolExecutionError(
                "HTTP JSON tool could not resolve a valid url.",
                fatal=True,
            )
        _raise_http_json_rendered_url_validation_error(rendered_url)
        rendered_method = _render_required_tool_execution_template(
            raw_method,
            context=context,
            path="method",
        )
        _raise_http_json_rendered_method_validation_error(rendered_method)
        method = _normalize_tool_execution_http_method(rendered_method)
        rendered_timeout_ms: object = default_timeout_ms
        if raw_timeout_ms is not None:
            rendered_timeout_ms = _render_required_tool_execution_template(
                raw_timeout_ms,
                context=context,
                path="timeout_ms",
            )
            _raise_http_json_rendered_timeout_ms_validation_error(
                rendered_timeout_ms
            )
        timeout_ms = _coerce_tool_execution_timeout_ms(
            rendered_timeout_ms,
            default_timeout_ms=default_timeout_ms,
        )
        rendered_response_path = _render_http_json_response_path(
            raw_response_path,
            context=context,
        )
        rendered_result_fields = _render_http_json_result_fields(
            raw_result_fields,
            context=context,
        )
        rendered_headers_value: object = {}
        if raw_headers is not None:
            rendered_headers_value = _render_required_tool_execution_template(
                raw_headers,
                context=context,
                path="headers",
            )
            try:
                rendered_headers_value = _coerce_http_json_json_compatible_body(
                    rendered_headers_value
                )
            except TypeError as exc:
                raise MockToolExecutionError(
                    "HTTP JSON tool headers must resolve to an object.",
                    fatal=True,
                ) from exc
            if not isinstance(rendered_headers_value, Mapping):
                raise MockToolExecutionError(
                    "HTTP JSON tool headers must resolve to an object.",
                    fatal=True,
                )
        _raise_http_json_rendered_value_validation_error(
            field_name="headers",
            raw_mapping=rendered_headers_value,
        )
        rendered_headers = _normalize_tool_execution_http_headers(
            rendered_headers_value
        )
        rendered_query_params_value: object = {}
        if raw_query_params is not None:
            rendered_query_params_value = _render_required_tool_execution_template(
                raw_query_params,
                context=context,
                path="query_params",
            )
            try:
                rendered_query_params_value = _coerce_http_json_json_compatible_body(
                    rendered_query_params_value
                )
            except TypeError as exc:
                raise MockToolExecutionError(
                    "HTTP JSON tool query_params must resolve to an object.",
                    fatal=True,
                ) from exc
            if not isinstance(rendered_query_params_value, Mapping):
                raise MockToolExecutionError(
                    "HTTP JSON tool query_params must resolve to an object.",
                    fatal=True,
                )
        _raise_http_json_rendered_value_validation_error(
            field_name="query_params",
            raw_mapping=rendered_query_params_value,
        )
        rendered_query_params = _normalize_tool_execution_http_query_params(
            rendered_query_params_value
        )
        _raise_http_json_rendered_duplicate_query_param_validation_error(
            url=rendered_url,
            query_params=rendered_query_params,
        )
        _raise_http_json_rendered_request_accept_validation_error(
            headers=rendered_headers
        )
        query_string = urlencode(rendered_query_params, doseq=True)
        full_url = rendered_url.strip()
        if query_string:
            separator = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{separator}{query_string}"
        request_data: bytes | None = None
        if raw_json_body is not None and method != "GET":
            rendered_json_body = _render_required_tool_execution_template(
                raw_json_body,
                context=context,
                path="json_body",
            )
            try:
                rendered_json_body = _coerce_http_json_json_compatible_body(
                    rendered_json_body
                )
            except TypeError as exc:
                raise MockToolExecutionError(
                    "HTTP JSON tool json_body must be valid JSON.",
                    fatal=True,
                ) from exc
            if not isinstance(rendered_json_body, Mapping):
                raise MockToolExecutionError(
                    "HTTP JSON tool json_body must resolve to an object.",
                    fatal=True,
                )
            rendered_json_body = dict(rendered_json_body)
            _raise_http_json_rendered_request_content_type_validation_error(
                headers=rendered_headers
            )
            _raise_http_json_rendered_json_body_validation_error(rendered_json_body)
            try:
                request_data = json.dumps(
                    rendered_json_body,
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise MockToolExecutionError(
                    "HTTP JSON tool json_body must be valid JSON.",
                    fatal=True,
            ) from exc
            _ensure_http_json_request_content_type_header(rendered_headers)
        if raw_json_body is not None and method == "GET":
            raise MockToolExecutionError(
                "HTTP JSON tool GET method must not define json_body; "
                "use query_params or a body-capable method.",
                fatal=True,
            )
        _ensure_http_json_request_accept_header(rendered_headers)
        request = Request(
            full_url,
            data=request_data,
            headers=rendered_headers,
            method=method,
        )
        response_request_id: str | None = None
        try:
            with urlopen(
                request,
                timeout=max(0.1, timeout_ms / 1000),
            ) as response:
                response_content_encoding = _get_http_json_response_content_encoding(
                    response
                )
                response_status_code, invalid_response_status = (
                    _get_http_json_response_status_code(response)
                )
                response_reason = _get_http_json_response_reason(response)
                response_content_type = _get_http_json_response_content_type(response)
                response_url = _get_http_json_response_url(response)
                response_request_id = _get_http_json_response_request_id(response)
                if (
                    invalid_response_status is None
                    and (
                        response_status_code is None
                        or 200 <= response_status_code <= 299
                    )
                    and response_url is not None
                    and not _http_json_response_url_matches_request_url(
                        response_url=response_url,
                        request_url=full_url,
                    )
                ):
                    raise MockToolExecutionError(
                        _format_http_json_redirected_response_url_error(response),
                        fatal=False,
                    )
                try:
                    response_body = _read_http_json_response_body_bytes(response)
                except TypeError as exc:
                    if invalid_response_status is not None:
                        raise MockToolExecutionError(
                            _format_http_json_invalid_status_response(
                                raw_status=invalid_response_status,
                                raw_body=exc,
                                content_type=response_content_type,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    if (
                        response_status_code is not None
                        and not 200 <= response_status_code <= 299
                    ):
                        raise MockToolExecutionError(
                            _format_http_json_unexpected_status_response_body_decode_error(
                                status_code=response_status_code,
                                reason=response_reason,
                                error=exc,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    raise MockToolExecutionError(
                        _format_http_json_transport_error(exc, response=response),
                        fatal=False,
                    ) from exc
                if invalid_response_status is not None:
                    raise MockToolExecutionError(
                        _format_http_json_invalid_status_response(
                            raw_status=invalid_response_status,
                            raw_body=response_body,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    )
                try:
                    response_body = _decode_http_json_response_body_for_content_encoding(
                        raw_body=response_body,
                        content_encoding=response_content_encoding,
                        content_type=response_content_type,
                    )
                except ValueError as exc:
                    if (
                        response_status_code is not None
                        and not 200 <= response_status_code <= 299
                    ):
                        raise MockToolExecutionError(
                            _format_http_json_unexpected_status_response_body_decode_error(
                                status_code=response_status_code,
                                reason=response_reason,
                                error=exc,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    message = f"HTTP JSON tool failed: {exc}"
                    message = _append_http_json_response_header_diagnostic_hints(
                        message,
                        response,
                    )
                    raise MockToolExecutionError(
                        message,
                        fatal=False,
                    ) from exc
                if (
                    response_status_code is not None
                    and not 200 <= response_status_code <= 299
                ):
                    raise MockToolExecutionError(
                        _format_http_json_unexpected_status_response(
                            status_code=response_status_code,
                            reason=response_reason,
                            raw_body=response_body,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    )
                if (
                    response_content_type
                    and not _is_supported_http_json_response_content_type(
                        response_content_type
                    )
                ):
                    raise MockToolExecutionError(
                        _format_http_json_invalid_content_type_response(
                            content_type=response_content_type,
                            raw_body=response_body,
                            response=response,
                        ),
                        fatal=False,
                    )
                if not response_body.strip():
                    raise MockToolExecutionError(
                        _format_http_json_empty_response(
                            status_code=response_status_code,
                            reason=response_reason,
                            response=response,
                        ),
                        fatal=False,
                    )
                try:
                    response_text = _decode_http_json_response_text(
                        raw_body=response_body,
                        content_type=response_content_type,
                        response=response,
                    )
                    response_payload = json.loads(response_text)
                except json.JSONDecodeError as exc:
                    raise MockToolExecutionError(
                        _format_http_json_invalid_json_response(
                            raw_body=response_body,
                            error=exc,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    ) from exc
        except HTTPError as exc:
            try:
                message = _format_http_json_http_error(exc)
            finally:
                _close_http_json_response(exc)
            raise MockToolExecutionError(
                message,
                fatal=False,
            ) from exc
        except (URLError, OSError, TypeError, ValueError) as exc:
            raise MockToolExecutionError(
                _format_http_json_transport_error(exc),
                fatal=False,
            ) from exc
        except Exception as exc:
            if isinstance(exc, MockToolExecutionError):
                raise
            raise MockToolExecutionError(
                _format_http_json_transport_error(exc),
                fatal=False,
            ) from exc

        scoped_payload = _extract_tool_execution_response_value(
            response_payload,
            path=rendered_response_path,
        )
        if scoped_payload is _TOOL_EXECUTION_TEMPLATE_MISSING:
            if (
                isinstance(rendered_response_path, str)
                and rendered_response_path.strip()
            ):
                safe_response_path = _format_http_json_mapping_path_for_error(
                    rendered_response_path
                )
                payload_shape = _format_http_json_mapping_payload_shape_for_error(
                    response_payload
                )
                message = (
                    "HTTP JSON tool response_path could not resolve any payload at "
                    f"{safe_response_path}; {payload_shape}."
                )
                message = _append_http_json_response_header_diagnostic_hints(
                    message,
                    response,
                )
                raise MockToolExecutionError(
                    message,
                    fatal=True,
                )
            scoped_payload = response_payload
        if isinstance(rendered_result_fields, dict):
            mapped_output: dict[str, object] = {}
            missing_result_fields: list[str] = []
            for raw_key, raw_path in rendered_result_fields.items():
                if not isinstance(raw_key, str) or not raw_key.strip():
                    continue
                normalized_key = raw_key.strip()
                mapped_value = _extract_tool_execution_response_value(
                    scoped_payload,
                    path=raw_path,
                )
                if mapped_value is _TOOL_EXECUTION_TEMPLATE_MISSING:
                    missing_result_fields.append(
                        _format_http_json_result_field_mapping_error(
                            field_name=normalized_key,
                            raw_path=raw_path,
                        )
                    )
                    continue
                mapped_output[normalized_key] = mapped_value
            if missing_result_fields and not mapped_output:
                formatted_mappings = _format_http_json_missing_result_field_mappings(
                    missing_result_fields
                )
                payload_shape = _format_http_json_mapping_payload_shape_for_error(
                    scoped_payload
                )
                message = (
                    "HTTP JSON tool result_fields could not resolve any configured "
                    f"mapping: {formatted_mappings}; {payload_shape}."
                )
                message = _append_http_json_response_header_diagnostic_hints(
                    message,
                    response,
                )
                raise MockToolExecutionError(
                    message,
                    fatal=True,
                )
            _attach_http_json_response_request_id(
                mapped_output,
                response_request_id,
            )
            return _normalize_http_json_safe_output_shape(mapped_output)
        if isinstance(scoped_payload, dict):
            output = dict(scoped_payload)
            _attach_http_json_response_request_id(output, response_request_id)
            return _normalize_http_json_safe_output_shape(output)
        output = _HttpJsonScalarFallbackOutput(
            {
                "value": _redact_http_json_sensitive_payload_value(scoped_payload),
            }
        )
        _attach_http_json_response_request_id(output, response_request_id)
        return output

    return runner


def _build_invalid_tool_execution_runner(
    *,
    message: str,
) -> ToolRunner:
    def runner(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
        del tool_input, prompt, user_id
        raise MockToolExecutionError(message, fatal=True)

    return runner


def _build_tool_runner_from_execution_spec(
    *,
    execution_spec: object,
    fallback_runner: ToolRunner,
    default_timeout_ms: int,
    template_context: dict[str, object] | None = None,
) -> ToolRunner:
    if execution_spec is None:
        return fallback_runner
    validation_errors = _describe_tool_execution_spec_validation_errors(
        execution_spec,
        template_context=template_context,
    )
    if validation_errors:
        return _build_invalid_tool_execution_runner(
            message=f"{validation_errors[0][:1].upper()}{validation_errors[0][1:]}",
        )
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind == "http_json":
        return _build_http_json_tool_runner(
            execution_spec=execution_spec,
            default_timeout_ms=default_timeout_ms,
            template_context=template_context,
        )
    if execution_kind is None:
        return _build_invalid_tool_execution_runner(
            message="Invalid tool execution spec: execution.kind is required.",
        )
    return _build_invalid_tool_execution_runner(
        message=(
            "Unsupported tool execution kind: "
            f"{_format_safe_tool_execution_kind(execution_kind)}"
        ),
    )


def _resolve_tool_execution_kind_from_spec(execution_spec: object) -> str | None:
    if not isinstance(execution_spec, dict):
        return None
    return _normalize_tool_execution_kind(execution_spec.get("kind"))


def _build_tool_execution_summary_from_spec(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if not isinstance(execution_spec, dict):
        return None
    execution_kind = _normalize_tool_execution_kind(execution_spec.get("kind"))
    if execution_kind != "http_json":
        return None

    raw_summary_method = execution_spec.get(
        "method",
        "POST" if execution_spec.get("json_body") is not None else "GET",
    )
    method_for_summary = _resolve_tool_execution_string_like_summary_value(
        raw_summary_method,
        context=template_context,
        path="method",
    )
    summary: dict[str, object] = {
        "method": _normalize_tool_execution_http_method(method_for_summary)
    }
    raw_url = execution_spec.get("url")
    summary_url: object = _resolve_tool_execution_string_like_summary_value(
        raw_url,
        context=template_context,
        path="url",
    )
    if (
        summary_url is _TOOL_EXECUTION_TEMPLATE_MISSING
        and not _is_supported_tool_execution_http_url(
            _coerce_tool_execution_string_like_value(raw_url)
        )
    ):
        summary_url = None
    if isinstance(summary_url, str) and summary_url.strip():
        parsed_url = urlparse(summary_url.strip())
        safe_origin = _format_safe_tool_execution_http_url_origin(parsed_url)
        if safe_origin:
            summary["url_origin"] = safe_origin
        safe_path = _format_safe_tool_execution_http_url_path(parsed_url)
        if safe_path:
            summary["url_path"] = safe_path
    raw_headers = execution_spec.get("headers")
    headers_for_summary = _resolve_tool_execution_summary_value(
        raw_headers,
        context=template_context,
        path="headers",
    )
    header_names = _iter_http_json_mapping_field_names(headers_for_summary)
    if header_names:
        summary["header_count"] = len(header_names)
    raw_query_params = execution_spec.get("query_params")
    query_params_for_summary = _resolve_tool_execution_summary_value(
        raw_query_params,
        context=template_context,
        path="query_params",
    )
    query_param_names = _iter_http_json_mapping_field_names(query_params_for_summary)
    if query_param_names:
        summary["query_param_count"] = len(query_param_names)
    raw_json_body = execution_spec.get("json_body")
    json_body_for_summary = _resolve_tool_execution_summary_value(
        raw_json_body,
        context=template_context,
        path="json_body",
    )
    json_body_field_names = _iter_http_json_mapping_field_names(json_body_for_summary)
    if json_body_field_names:
        summary["json_body_field_count"] = len(json_body_field_names)
    raw_response_path = execution_spec.get("response_path")
    response_path_for_summary = _resolve_tool_execution_mapping_path_for_static_validation(
        raw_response_path,
        context=template_context,
        path="response_path",
    )
    if (
        isinstance(response_path_for_summary, str)
        and response_path_for_summary.strip()
    ):
        summary["response_path"] = _format_http_json_mapping_path_for_error(
            response_path_for_summary
        )
    raw_result_fields = execution_spec.get("result_fields")
    result_fields_for_summary = _resolve_tool_execution_summary_value(
        raw_result_fields,
        context=template_context,
        path="result_fields",
    )
    result_field_names = _iter_http_json_mapping_field_names(result_fields_for_summary)
    if result_field_names:
        result_field_names = tuple(
            _format_safe_tool_execution_summary_field_name(raw_key)
            for raw_key in result_field_names
        )
        if result_field_names:
            summary["result_field_names"] = list(result_field_names)
    return summary


def _resolve_tool_execution_summary_value(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    return _coerce_tool_execution_value_for_static_validation(
        _resolve_tool_execution_template_value_for_static_validation(
            value,
            context=context,
            path=path,
        )
    )


def _resolve_tool_execution_string_like_summary_value(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    rendered_value = _resolve_tool_execution_template_value_for_static_validation(
        value,
        context=context,
        path=path,
    )
    return _coerce_tool_execution_string_like_value(rendered_value)


def _format_safe_tool_execution_summary_url_path(raw_value: object) -> str:
    raw_path = str(raw_value).strip()
    if not raw_path:
        return ""
    path = _redact_http_json_url_text(unquote(raw_path))
    path, fragment_separator, fragment = path.partition("#")
    path, query_separator, query = path.partition("?")
    safe_segments: list[str] = []
    redact_next_segment = False
    for segment in path.split("/"):
        if not segment:
            safe_segments.append(segment)
            continue
        if redact_next_segment:
            safe_segments.append("[redacted]")
            redact_next_segment = False
            continue
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.fullmatch(segment):
            safe_segments.append("[redacted]")
            redact_next_segment = True
            continue
        safe_segments.append(_redact_http_json_diagnostic_text(segment))
    safe_path = "/".join(safe_segments)
    if query_separator:
        safe_query = _format_safe_http_json_url_query(query)
        if safe_query:
            safe_path = f"{safe_path}?{safe_query}"
    if fragment_separator:
        safe_fragment = _format_safe_http_json_url_fragment(fragment)
        if safe_fragment:
            safe_path = f"{safe_path}#{safe_fragment}"
    return safe_path


def _sanitize_tool_execution_summary_value(key: str, value: object) -> object:
    normalized_key = key.strip()
    value = _coerce_tool_execution_string_like_value(value)
    if normalized_key == "url_path" and isinstance(value, str):
        return _format_safe_tool_execution_summary_url_path(value)
    if normalized_key == "response_path" and isinstance(value, str):
        return _format_http_json_mapping_path_for_error(value)
    if normalized_key == "result_field_names" and isinstance(
        value,
        Sequence,
    ) and not isinstance(value, (str, bytes, bytearray, memoryview)):
        return [
            safe_field_name
            for safe_field_name in (
                _format_safe_tool_execution_summary_field_name(item)
                for item in value
            )
            if safe_field_name
        ]
    if isinstance(value, str):
        return _redact_tool_registry_diagnostic_value(value)
    return value


def sanitize_tool_execution_summary(
    execution_summary: object,
) -> dict[str, object] | None:
    if not isinstance(execution_summary, Mapping) or not execution_summary:
        return None
    sanitized_summary: dict[str, object] = {}
    for raw_key, raw_value in execution_summary.items():
        raw_key = _coerce_tool_execution_string_like_value(raw_key)
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        safe_value = _sanitize_tool_execution_summary_value(raw_key, raw_value)
        if safe_value in ("", [], ()):
            continue
        sanitized_summary[raw_key.strip()] = safe_value
    return sanitized_summary or None


def sanitize_tool_execution_diagnostics(diagnostics: object) -> tuple[str, ...]:
    if not isinstance(diagnostics, Sequence) or isinstance(
        diagnostics,
        (str, bytes, bytearray, memoryview),
    ):
        return ()
    safe_diagnostics: list[str] = []
    for diagnostic in diagnostics:
        diagnostic = _coerce_tool_execution_string_like_value(diagnostic)
        if not isinstance(diagnostic, str):
            continue
        safe_diagnostic = _redact_tool_registry_diagnostic_value(diagnostic)
        if safe_diagnostic:
            safe_diagnostics.append(safe_diagnostic)
    return tuple(dict.fromkeys(safe_diagnostics))


def _describe_tool_execution_spec_validation_error(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> str | None:
    validation_errors = _describe_tool_execution_spec_validation_errors(
        execution_spec,
        template_context=template_context,
    )
    return validation_errors[0] if validation_errors else None


def _describe_tool_execution_spec_validation_errors(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> tuple[str, ...]:
    if execution_spec is None:
        return ()
    if not isinstance(execution_spec, dict):
        return ("invalid tool execution spec: expected an object",)
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind is None:
        return ("invalid tool execution spec: execution.kind is required",)
    if execution_kind != "http_json":
        return (
            "unsupported tool execution kind "
            f"{_format_safe_tool_execution_kind(execution_kind)}",
        )
    raw_url = _coerce_tool_execution_string_like_value(execution_spec.get("url"))
    if not isinstance(raw_url, str) or not raw_url.strip():
        return ("http_json execution requires a non-empty url",)
    validation_errors: list[str] = []
    url_for_validation: object | None = raw_url
    if _iter_tool_execution_template_variable_references(raw_url, path="url"):
        rendered_url = _render_tool_execution_template_for_static_analysis(
            raw_url,
            context=template_context,
            path="url",
        )
        url_for_validation = (
            None
            if rendered_url is _TOOL_EXECUTION_TEMPLATE_MISSING
            else _coerce_tool_execution_string_like_value(rendered_url)
        )
    if url_for_validation is not None:
        url_error = _describe_tool_execution_http_url_validation_error(url_for_validation)
        if url_error:
            validation_errors.append(url_error)
    normalized_method: str | None = None
    if "method" in execution_spec:
        raw_method = execution_spec.get("method")
        method_for_validation: object | None = _coerce_tool_execution_string_like_value(
            raw_method
        )
        if _iter_tool_execution_template_variable_references(
            raw_method,
            path="method",
        ):
            rendered_method = _render_tool_execution_template_for_static_analysis(
                raw_method,
                context=template_context,
                path="method",
            )
            method_for_validation = (
                None
                if rendered_method is _TOOL_EXECUTION_TEMPLATE_MISSING
                else _coerce_tool_execution_string_like_value(rendered_method)
            )
        if method_for_validation is not None:
            method_error = _describe_tool_execution_http_method_validation_error(
                method_for_validation
            )
            if method_error:
                validation_errors.append(method_error)
            else:
                normalized_method = _normalize_tool_execution_http_method(
                    method_for_validation
                )
    if "timeout_ms" in execution_spec:
        raw_timeout_ms = execution_spec.get("timeout_ms")
        timeout_ms_for_validation: object | None = raw_timeout_ms
        if _iter_tool_execution_template_variable_references(
            raw_timeout_ms,
            path="timeout_ms",
        ):
            rendered_timeout_ms = _render_tool_execution_template_for_static_analysis(
                raw_timeout_ms,
                context=template_context,
                path="timeout_ms",
            )
            timeout_ms_for_validation = (
                None
                if rendered_timeout_ms is _TOOL_EXECUTION_TEMPLATE_MISSING
                else rendered_timeout_ms
            )
        if timeout_ms_for_validation is not None:
            timeout_error = _describe_tool_execution_timeout_ms_validation_error(
                timeout_ms_for_validation
            )
            if timeout_error:
                validation_errors.append(timeout_error)
    raw_headers = execution_spec.get("headers")
    headers_for_validation = _coerce_tool_execution_value_for_static_validation(
        _resolve_tool_execution_template_value_for_static_validation(
            raw_headers,
            context=template_context,
            path="headers",
        )
    )
    if (
        raw_headers is not None
        and not isinstance(headers_for_validation, Mapping)
        and not _is_tool_execution_root_template_reference(raw_headers)
    ):
        validation_errors.append("http_json execution headers must be an object")
    raw_query_params = execution_spec.get("query_params")
    query_params_for_validation = _coerce_tool_execution_value_for_static_validation(
        _resolve_tool_execution_template_value_for_static_validation(
            raw_query_params,
            context=template_context,
            path="query_params",
        )
    )
    if (
        raw_query_params is not None
        and not isinstance(query_params_for_validation, Mapping)
        and not _is_tool_execution_root_template_reference(raw_query_params)
    ):
        validation_errors.append("http_json execution query_params must be an object")
    raw_json_body = execution_spec.get("json_body")
    json_body_for_validation = _coerce_tool_execution_value_for_static_validation(
        _resolve_tool_execution_template_value_for_static_validation(
            raw_json_body,
            context=template_context,
            path="json_body",
        )
    )
    if (
        raw_json_body is not None
        and not isinstance(json_body_for_validation, Mapping)
        and not _is_tool_execution_root_template_reference(raw_json_body)
    ):
        validation_errors.append("http_json execution json_body must be an object")
    if normalized_method == "GET" and raw_json_body is not None:
        validation_errors.append(
            "http_json execution GET method must not define json_body; "
            "use query_params or a body-capable method"
        )
    effective_method = (
        normalized_method
        if normalized_method is not None
        else ("POST" if raw_json_body is not None else "GET")
    )
    if raw_json_body is not None and effective_method != "GET":
        validation_errors.extend(
            _describe_http_json_request_content_type_validation_errors(
                headers=headers_for_validation,
            )
        )
    validation_errors.extend(
        _describe_http_json_request_accept_validation_errors(
            headers=headers_for_validation,
        )
    )
    duplicate_query_param_error = (
        _describe_tool_execution_http_duplicate_query_param_validation_error(
            url=url_for_validation,
            query_params=query_params_for_validation,
        )
    )
    if duplicate_query_param_error:
        validation_errors.append(duplicate_query_param_error)
    raw_response_path = execution_spec.get("response_path")
    if raw_response_path is not None:
        response_path_for_validation = (
            _resolve_tool_execution_mapping_path_for_static_validation(
                raw_response_path,
                context=template_context,
                path="response_path",
            )
        )
        if response_path_for_validation is _TOOL_EXECUTION_TEMPLATE_MISSING:
            pass
        elif not isinstance(response_path_for_validation, str):
            validation_errors.append("http_json execution response_path must be a string")
        elif not response_path_for_validation.strip():
            validation_errors.append(
                "http_json execution response_path must be a non-empty string when provided"
            )
        elif not _is_supported_tool_execution_response_path(
            response_path_for_validation
        ):
            validation_errors.append(
                "http_json execution response_path must use dot fields and "
                "numeric indexes"
            )
    raw_result_fields = execution_spec.get("result_fields")
    result_fields_for_validation = raw_result_fields
    if _is_tool_execution_root_template_reference(raw_result_fields):
        rendered_result_fields = _render_tool_execution_template_for_static_analysis(
            raw_result_fields,
            context=template_context,
            path="result_fields",
        )
        if rendered_result_fields is _TOOL_EXECUTION_TEMPLATE_MISSING:
            result_fields_for_validation = _TOOL_EXECUTION_TEMPLATE_MISSING
        else:
            try:
                result_fields_for_validation = _coerce_http_json_json_compatible_body(
                    rendered_result_fields
                )
            except TypeError:
                result_fields_for_validation = rendered_result_fields
    if (
        result_fields_for_validation is not None
        and result_fields_for_validation is not _TOOL_EXECUTION_TEMPLATE_MISSING
        and not isinstance(result_fields_for_validation, Mapping)
    ):
        validation_errors.append("http_json execution result_fields must be an object")
    for field_name, raw_mapping in (
        ("headers", headers_for_validation),
        ("query_params", query_params_for_validation),
        ("json_body", json_body_for_validation),
    ):
        if not isinstance(raw_mapping, Mapping):
            continue
        has_valid_field_name = bool(_iter_http_json_mapping_field_names(raw_mapping))
        has_blank_field_name = False
        for raw_key in raw_mapping:
            raw_key = _coerce_http_json_mapping_field_name(raw_key)
            if isinstance(raw_key, str) and raw_key.strip():
                continue
            has_blank_field_name = True
        if has_blank_field_name:
            validation_errors.append(
                f"http_json execution {field_name} must not include blank field names"
            )
        if raw_mapping and not has_valid_field_name:
            validation_errors.append(
                f"http_json execution {field_name} must include at least one "
                "non-empty field name when provided"
            )
    validation_errors.extend(
        _describe_tool_execution_http_value_validation_errors(
            field_name="headers",
            raw_mapping=headers_for_validation,
        )
    )
    validation_errors.extend(
        _describe_tool_execution_http_value_validation_errors(
            field_name="query_params",
            raw_mapping=query_params_for_validation,
        )
    )
    validation_errors.extend(
        _describe_tool_execution_json_body_validation_errors(json_body_for_validation)
    )
    if isinstance(result_fields_for_validation, Mapping):
        if not result_fields_for_validation:
            validation_errors.append(
                "http_json execution result_fields must include at least one "
                "field mapping"
            )
        has_valid_result_field_name = False
        has_blank_result_field_name = False
        for raw_key, raw_path in result_fields_for_validation.items():
            result_field_name = _coerce_http_json_mapping_field_name(raw_key)
            if not isinstance(result_field_name, str) or not result_field_name.strip():
                has_blank_result_field_name = True
                continue
            has_valid_result_field_name = True
            normalized_result_field_name = result_field_name.strip()
            safe_result_field_path = _format_safe_tool_execution_diagnostic_path(
                f"result_fields.{normalized_result_field_name}"
            )
            path_for_validation = _resolve_tool_execution_mapping_path_for_static_validation(
                raw_path,
                context=template_context,
                path=f"result_fields.{normalized_result_field_name}",
            )
            if path_for_validation is _TOOL_EXECUTION_TEMPLATE_MISSING:
                continue
            if isinstance(path_for_validation, str) and path_for_validation.strip():
                if not _is_supported_tool_execution_response_path(path_for_validation):
                    validation_errors.append(
                        f"http_json execution {safe_result_field_path} must use dot "
                        "fields and numeric indexes"
                    )
                continue
            validation_errors.append(
                f"http_json execution {safe_result_field_path} must be a non-empty "
                "string path"
            )
        if has_blank_result_field_name and has_valid_result_field_name:
            validation_errors.append(
                "http_json execution result_fields must not include blank field names"
            )
        if result_fields_for_validation and not has_valid_result_field_name:
            validation_errors.append(
                "http_json execution result_fields must include at least one "
                "non-empty field name"
            )
    runtime_template_validation_spec = {
        **execution_spec,
        "headers": headers_for_validation,
        "query_params": query_params_for_validation,
        "json_body": json_body_for_validation,
    }
    if result_fields_for_validation is not _TOOL_EXECUTION_TEMPLATE_MISSING:
        runtime_template_validation_spec["result_fields"] = result_fields_for_validation
    validation_errors.extend(
        _collect_tool_execution_runtime_template_validation_errors(
            execution_spec=runtime_template_validation_spec,
        )
    )
    return tuple(dict.fromkeys(validation_errors))


def _build_invalid_tool_execution_diagnostics(
    *,
    messages: object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(messages, (list, tuple)):
        return _empty_tool_registry_file_diagnostics()
    normalized_messages = tuple(
        str(message).strip()
        for message in messages
        if str(message).strip()
    )
    if not normalized_messages:
        return _empty_tool_registry_file_diagnostics()
    diagnostics = _empty_tool_registry_file_diagnostics()
    diagnostics["invalid_tool_executions"] = tuple(dict.fromkeys(normalized_messages))
    return diagnostics


def _group_invalid_tool_execution_messages_by_tool(
    messages: object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(messages, (list, tuple)):
        return {}
    grouped_messages: dict[str, list[str]] = {}
    for raw_message in messages:
        message = str(raw_message).strip()
        if not message:
            continue
        tool_name, separator, detail = message.partition(":")
        if not separator:
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name)
        normalized_detail = _redact_tool_registry_diagnostic_value(detail)
        if not normalized_tool_name or not normalized_detail:
            continue
        grouped_messages.setdefault(normalized_tool_name, [])
        if normalized_detail not in grouped_messages[normalized_tool_name]:
            grouped_messages[normalized_tool_name].append(normalized_detail)
    return {
        tool_name: tuple(messages)
        for tool_name, messages in grouped_messages.items()
    }


def _collect_invalid_tool_execution_messages_from_extra_tool_specs(
    *,
    extra_tool_specs: object,
    settings: object | None = None,
) -> tuple[str, ...]:
    extra_tool_specs = _coerce_tool_registry_spec_payload(extra_tool_specs)
    if not isinstance(extra_tool_specs, dict):
        return ()
    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    messages: list[str] = []
    for tool_name, spec in extra_tool_specs.items():
        if not isinstance(tool_name, str) or not isinstance(spec, dict):
            continue
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                spec.get("default_timeout_ms")
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        if "execution" in spec:
            validation_errors.extend(
                _describe_tool_execution_spec_validation_errors(
                    spec.get("execution"),
                    template_context=runtime_template_context,
                )
            )
        if not validation_errors:
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name) or tool_name.strip()
        messages.extend(
            f"{normalized_tool_name}: {validation_error}"
            for validation_error in validation_errors
        )
    return tuple(dict.fromkeys(messages))


def _collect_invalid_tool_execution_messages_from_override_specs(
    *,
    override_specs: object,
    base_registry: dict[str, ToolRegistration],
    settings: object | None = None,
) -> tuple[str, ...]:
    override_specs = _coerce_tool_registry_spec_payload(override_specs)
    if not isinstance(override_specs, dict):
        return ()
    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    messages: list[str] = []
    for tool_name, spec in override_specs.items():
        if not isinstance(tool_name, str) or not isinstance(spec, dict):
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name)
        if not normalized_tool_name or normalized_tool_name not in base_registry:
            continue
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                spec.get("default_timeout_ms")
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        if "execution" in spec:
            validation_errors.extend(
                _describe_tool_execution_spec_validation_errors(
                    spec.get("execution"),
                    template_context=runtime_template_context,
                )
            )
        if not validation_errors:
            continue
        messages.extend(
            f"{normalized_tool_name}: {validation_error}"
            for validation_error in validation_errors
        )
    return tuple(dict.fromkeys(messages))


def build_tool_registry_settings_execution_diagnostics(
    *,
    settings: object | None = None,
    base_provider: ToolRegistryProvider | None = None,
) -> dict[str, tuple[str, ...]]:
    if settings is None:
        settings = get_settings()
    raw_extra_tools = getattr(settings, "tool_registry_extra_tools_json", None)
    extra_tool_specs: object = None
    parsed_extra_tool_specs = _parse_tool_registry_json_object_setting(raw_extra_tools)
    if parsed_extra_tool_specs is not None:
        extra_tool_specs = parsed_extra_tool_specs

    extra_tool_messages = _collect_invalid_tool_execution_messages_from_extra_tool_specs(
        extra_tool_specs=extra_tool_specs,
        settings=settings,
    )

    known_registrations = (
        dict(base_provider.load_tool_registry())
        if base_provider is not None
        else get_default_tool_registry()
    )
    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=extra_tool_specs,
        settings=settings,
    )
    known_registrations = build_tool_registry(
        base_registry=known_registrations,
        overrides=extra_tools or None,
    )

    raw_overrides = getattr(settings, "tool_registry_overrides_json", None)
    override_specs: object = None
    parsed_override_specs = _parse_tool_registry_json_object_setting(raw_overrides)
    if parsed_override_specs is not None:
        override_specs = parsed_override_specs

    override_messages = _collect_invalid_tool_execution_messages_from_override_specs(
        override_specs=override_specs,
        base_registry=known_registrations,
        settings=settings,
    )
    return _build_invalid_tool_execution_diagnostics(
        messages=(*extra_tool_messages, *override_messages),
    )
