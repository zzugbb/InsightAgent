from __future__ import annotations

import codecs
import gzip
import inspect
import json
import math
import re
import zlib
from collections import UserString
from collections.abc import Mapping, Sequence
from urllib.parse import parse_qsl, unquote, urlparse

from app.services.tool_runtime_http_json import (
    MockToolExecutionError,
    _HTTP_JSON_BARE_BEARER_TOKEN_RE,
    _HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH,
    _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE,
    _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE,
    _HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS,
    _HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH,
    _HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE,
    _HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS,
    _HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES,
    _HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS,
    _HTTP_JSON_URL_TEXT_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_BRACKET_FIELD_PATH_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_BRACKET_MAPPING_PATH_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_BRACKET_SEGMENT_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_DOT_SEGMENT_RE,
    _TOOL_REGISTRY_DIAGNOSTIC_MAPPING_PATH_RE,
    _coerce_tool_execution_string_like_value,
    _format_safe_tool_execution_diagnostic_path,
    _format_safe_tool_execution_http_url_origin,
    _format_safe_tool_execution_http_url_path,
    _format_safe_tool_execution_summary_field_name,
    _http_json_header_value_has_balanced_quoted_parameters,
    _normalize_http_json_output_shape,
    _normalize_tool_execution_kind,
)


def _redact_http_json_sensitive_payload_text(raw_value: str) -> str:
    redacted = _redact_http_json_url_text(raw_value)
    redacted = _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        redacted,
    )

    def redact_path(match: re.Match[str]) -> str:
        raw_path = match.group(0)
        safe_path = _format_safe_tool_execution_diagnostic_path(raw_path)
        return "[redacted]" if "[redacted]" in safe_path else raw_path

    redacted = _TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE.sub(redact_path, redacted)
    redacted = _redact_tool_registry_diagnostic_bracket_field_paths(redacted)
    redacted = _redact_tool_registry_diagnostic_mapping_paths(redacted)
    redacted = _redact_tool_registry_diagnostic_bracket_mapping_paths(redacted)
    return _HTTP_JSON_BARE_BEARER_TOKEN_RE.sub("[redacted]", redacted)


def _format_safe_http_json_payload_key(raw_key: object) -> str:
    normalized_key = str(raw_key)
    safe_key = _redact_tool_registry_diagnostic_value(normalized_key)
    if safe_key != normalized_key and "[redacted]" in safe_key:
        return "[redacted]"
    return normalized_key


def _redact_http_json_sensitive_payload_value(raw_value: object) -> object:
    if isinstance(raw_value, dict):
        redacted: dict[str, object] = {}
        for key, value in raw_value.items():
            normalized_key = str(key)
            safe_key = _format_safe_http_json_payload_key(normalized_key)
            if safe_key == "[redacted]":
                redacted[safe_key] = "[redacted]"
                continue
            if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(normalized_key):
                redacted[safe_key] = "[redacted]"
                continue
            redacted[safe_key] = _redact_http_json_sensitive_payload_value(value)
        return redacted
    if isinstance(raw_value, list):
        return [_redact_http_json_sensitive_payload_value(item) for item in raw_value]
    if isinstance(raw_value, tuple):
        return tuple(_redact_http_json_sensitive_payload_value(item) for item in raw_value)
    if isinstance(raw_value, str):
        return _redact_http_json_sensitive_payload_text(raw_value)
    return raw_value


def _normalize_http_json_safe_output_shape(output: dict[str, object]) -> dict[str, object]:
    normalized_output = _normalize_http_json_output_shape(output)
    redacted_output = _redact_http_json_sensitive_payload_value(normalized_output)
    if isinstance(redacted_output, dict):
        return redacted_output
    return normalized_output


def _normalize_tool_result_projection_output(
    output: dict[str, object],
    *,
    registration: ToolRegistration | None,
) -> dict[str, object]:
    if (
        registration is not None
        and _normalize_tool_execution_kind(registration.execution_kind) == "http_json"
    ):
        return _normalize_http_json_safe_output_shape(output)
    return output


def _redact_http_json_diagnostic_text(raw_value: str) -> str:
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
        "[redacted]",
        raw_value,
    )


def _format_safe_http_json_url_query(raw_query: object) -> str:
    if not isinstance(raw_query, str) or not raw_query:
        return ""
    safe_params: list[str] = []
    for raw_name, raw_value in parse_qsl(raw_query, keep_blank_values=True):
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(raw_name):
            safe_params.append("[redacted]")
            continue
        safe_name = _redact_http_json_diagnostic_text(raw_name)
        safe_value = _redact_http_json_url_text(raw_value)
        safe_value = _redact_http_json_diagnostic_text(safe_value)
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(safe_value):
            safe_value = "[redacted]"
        safe_params.append(f"{safe_name}={safe_value}")
    return "&".join(safe_params)


def _format_safe_http_json_url_fragment(raw_fragment: object) -> str:
    if not isinstance(raw_fragment, str) or not raw_fragment:
        return ""
    safe_fragment = _redact_http_json_url_text(unquote(raw_fragment))
    safe_fragment = _redact_http_json_diagnostic_text(safe_fragment)
    if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(safe_fragment):
        return "[redacted]"
    return safe_fragment


def _format_safe_http_json_url_text(raw_url: str) -> str:
    parsed_url = urlparse(raw_url)
    origin = _format_safe_tool_execution_http_url_origin(parsed_url)
    if origin is None:
        return "[redacted]"
    if (
        getattr(parsed_url, "username", None) is not None
        or getattr(parsed_url, "password", None) is not None
    ):
        origin_prefix = f"{parsed_url.scheme}://"
        if origin.startswith(origin_prefix):
            origin = f"{origin_prefix}[redacted]@{origin[len(origin_prefix):]}"
    path = _format_safe_tool_execution_http_url_path(parsed_url) or ""
    safe_url = f"{origin}{path}"
    query = _format_safe_http_json_url_query(parsed_url.query)
    if query:
        safe_url = f"{safe_url}?{query}"
    fragment = _format_safe_http_json_url_fragment(parsed_url.fragment)
    if fragment:
        safe_url = f"{safe_url}#{fragment}"
    return safe_url


def _redact_http_json_url_text(raw_value: str) -> str:
    def redact_url(match: re.Match[str]) -> str:
        return _format_safe_http_json_url_text(match.group(0))

    return _HTTP_JSON_URL_TEXT_RE.sub(redact_url, raw_value)


def _redact_tool_registry_diagnostic_mapping_paths(raw_value: str) -> str:
    def redact_mapping_path(match: re.Match[str]) -> str:
        context = match.group("context")
        separator = match.group("separator")
        path = match.group("path")
        safe_context = _format_safe_tool_execution_diagnostic_path(context)
        safe_path = _format_safe_tool_execution_diagnostic_path(path)
        if "[redacted]" not in safe_context and "[redacted]" not in safe_path:
            return match.group(0)
        if "[redacted]" in safe_context:
            safe_context = "[redacted]"
        return f"{safe_context}{separator}{safe_path}"

    return _TOOL_REGISTRY_DIAGNOSTIC_MAPPING_PATH_RE.sub(
        redact_mapping_path,
        raw_value,
    )


def _redact_tool_registry_diagnostic_bracket_field_paths(raw_value: str) -> str:
    def redact_field_path(match: re.Match[str]) -> str:
        safe_path = _format_safe_tool_execution_bracket_jsonpath(match.group(0))
        if "[redacted]" in safe_path:
            return "[redacted]"
        return match.group(0)

    return _TOOL_REGISTRY_DIAGNOSTIC_BRACKET_FIELD_PATH_RE.sub(
        redact_field_path,
        raw_value,
    )


def _format_safe_tool_execution_bracket_jsonpath(raw_value: object) -> str:
    raw_path = str(raw_value).strip()
    if not raw_path:
        return ""

    def redact_dot_segment(match: re.Match[str]) -> str:
        field_name = match.group("field")
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(field_name):
            return f"{match.group('prefix')}[redacted]"
        return match.group(0)

    def redact_bracket_segment(match: re.Match[str]) -> str:
        field_name = match.group("field")
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(field_name):
            quote = match.group("quote")
            return f"[{quote}[redacted]{quote}]"
        return match.group(0)

    safe_path = _TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_DOT_SEGMENT_RE.sub(
        redact_dot_segment,
        raw_path,
    )
    return _TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_BRACKET_SEGMENT_RE.sub(
        redact_bracket_segment,
        safe_path,
    )


def _redact_tool_registry_diagnostic_bracket_mapping_paths(raw_value: str) -> str:
    def redact_mapping_path(match: re.Match[str]) -> str:
        context = match.group("context")
        separator = match.group("separator")
        path = match.group("path")
        safe_context = _format_safe_tool_execution_diagnostic_path(context)
        safe_path = _format_safe_tool_execution_bracket_jsonpath(path)
        if "[redacted]" not in safe_context and "[redacted]" not in safe_path:
            return match.group(0)
        if "[redacted]" in safe_context:
            safe_context = "[redacted]"
        return f"{safe_context}{separator}{safe_path}"

    return _TOOL_REGISTRY_DIAGNOSTIC_BRACKET_MAPPING_PATH_RE.sub(
        redact_mapping_path,
        raw_value,
    )


def _redact_tool_registry_diagnostic_value(raw_value: object) -> str:
    text = _redact_http_json_url_text(str(raw_value).strip())
    text = _redact_http_json_diagnostic_text(text)
    if not text:
        return ""

    def redact_path(match: re.Match[str]) -> str:
        safe_path = _format_safe_tool_execution_diagnostic_path(match.group(0))
        if "[redacted]" in safe_path:
            return "[redacted]"
        return safe_path

    text = _TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE.sub(redact_path, text)
    text = _redact_tool_registry_diagnostic_bracket_field_paths(text)
    text = _redact_tool_registry_diagnostic_mapping_paths(text)
    text = _redact_tool_registry_diagnostic_bracket_mapping_paths(text)
    return _HTTP_JSON_BARE_BEARER_TOKEN_RE.sub("[redacted]", text)


def _redact_http_json_raw_fallback_value(raw_value: object) -> object:
    if isinstance(raw_value, dict):
        redacted: dict[str, object] = {}
        for key, value in raw_value.items():
            normalized_key = str(key)
            safe_key = _format_safe_http_json_payload_key(normalized_key)
            if (
                safe_key == "[redacted]"
                or _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(normalized_key)
            ):
                redacted[safe_key] = "[redacted]"
                continue
            redacted[safe_key] = _redact_http_json_raw_fallback_value(value)
        return redacted
    if isinstance(raw_value, list):
        return [_redact_http_json_raw_fallback_value(value) for value in raw_value]
    if isinstance(raw_value, tuple):
        return tuple(_redact_http_json_raw_fallback_value(value) for value in raw_value)
    if isinstance(raw_value, str):
        safe_text = _redact_tool_registry_diagnostic_value(raw_value)
        return _HTTP_JSON_BARE_BEARER_TOKEN_RE.sub("[redacted]", safe_text)
    return raw_value


def _redact_http_json_error_body_value(raw_value: object) -> object:
    if isinstance(raw_value, dict):
        redacted: dict[str, object] = {}
        for key, value in raw_value.items():
            safe_key = _format_safe_tool_execution_summary_field_name(key)
            if safe_key == "[redacted]":
                redacted[safe_key] = "[redacted]"
                continue
            redacted[safe_key] = _redact_http_json_error_body_value(value)
        return redacted
    if isinstance(raw_value, list):
        return [_redact_http_json_error_body_value(item) for item in raw_value]
    if isinstance(raw_value, tuple):
        return tuple(_redact_http_json_error_body_value(item) for item in raw_value)
    if isinstance(raw_value, str):
        safe_value = _redact_http_json_raw_fallback_value(raw_value)
        return safe_value if isinstance(safe_value, str) else "[redacted]"
    return raw_value


def _coerce_http_json_error_body_preview_text(raw_body: object) -> str:
    if isinstance(raw_body, bytes):
        raw_text = raw_body.decode("utf-8", errors="replace")
    else:
        raw_text = str(raw_body)
    try:
        parsed_body = json.loads(raw_text)
    except (TypeError, ValueError):
        safe_text = _redact_http_json_raw_fallback_value(raw_text)
        return safe_text if isinstance(safe_text, str) else "[redacted]"
    redacted_body = _redact_http_json_error_body_value(parsed_body)
    return json.dumps(redacted_body, ensure_ascii=False, separators=(",", ":"))


def _format_http_json_error_body_preview(raw_body: object) -> str:
    normalized = _coerce_http_json_error_body_preview_text(raw_body)
    normalized = " ".join(normalized.strip().split())
    if len(normalized) <= _HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH:
        return normalized
    return f"{normalized[:_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH]}..."


def _coerce_http_json_body_preview_bytes(raw_body: object) -> bytes | None:
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, bytearray):
        return bytes(raw_body)
    if isinstance(raw_body, memoryview):
        return raw_body.tobytes()
    return None


def _format_http_json_response_body_preview(
    raw_body: object,
    *,
    content_type: object = None,
) -> str:
    raw_bytes = _coerce_http_json_body_preview_bytes(raw_body)
    if raw_bytes is None:
        return _format_http_json_error_body_preview(raw_body)
    charset = _get_http_json_response_charset(content_type)
    try:
        codecs.lookup(charset)
        raw_text = raw_bytes.decode(charset)
    except (LookupError, UnicodeError):
        return _format_http_json_error_body_preview(raw_bytes)
    return _format_http_json_error_body_preview(raw_text)


def _append_http_json_response_header_diagnostic_hints(
    message: str,
    response: object,
) -> str:
    header_hints = _format_http_json_response_header_diagnostic_hints(response)
    if not header_hints:
        return message
    return f"{message}; headers: {header_hints}"


def _format_http_json_http_error(exc: HTTPError) -> str:
    message = f"HTTP JSON tool failed: HTTP {exc.code}"
    reason = _format_http_json_error_body_preview(
        getattr(exc, "reason", "") or ""
    )
    if reason:
        message = f"{message} {reason}"
    message = _append_http_json_response_header_diagnostic_hints(message, exc)
    content_type = _get_http_json_response_content_type(exc)
    try:
        body = _read_http_json_response_body_bytes(exc)
        body = _decode_http_json_response_body_for_content_encoding(
            raw_body=body,
            content_encoding=_get_http_json_response_content_encoding(exc),
            content_type=content_type,
        )
        body_preview = _format_http_json_response_body_preview(
            body,
            content_type=content_type,
        )
    except (OSError, TypeError) as exc:
        body_preview = _format_http_json_error_body_preview(exc)
    except ValueError as exc:
        body_preview = _format_http_json_error_body_preview(exc)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _coerce_http_json_response_status_code(raw_value: object) -> int | None:
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float):
        if math.isfinite(raw_value) and raw_value.is_integer():
            return int(raw_value)
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8", errors="replace")
    if isinstance(raw_value, bytearray):
        raw_value = bytes(raw_value).decode("utf-8", errors="replace")
    if isinstance(raw_value, memoryview):
        raw_value = raw_value.tobytes().decode("utf-8", errors="replace")
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        match = re.match(r"^(\d{3})(?:\b|$)", normalized)
        if match:
            return int(match.group(1))
    return None


def _http_json_response_status_value_is_present(raw_value: object) -> bool:
    if raw_value is None:
        return False
    if isinstance(raw_value, str):
        return bool(raw_value.strip())
    if isinstance(raw_value, (bytes, bytearray)):
        return bool(bytes(raw_value).strip())
    if isinstance(raw_value, memoryview):
        return bool(raw_value.tobytes().strip())
    return True


def _format_http_json_invalid_status_response(
    *,
    raw_status: object,
    raw_body: object,
    content_type: object = None,
    response: object | None = None,
) -> str:
    status_preview = _format_http_json_error_body_preview(raw_status)
    message = "HTTP JSON tool failed: invalid HTTP response status"
    if status_preview:
        message = f"{message}: {status_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _get_http_json_adapter_attr(adapter: object, attr_name: str) -> object | None:
    try:
        return getattr(adapter, attr_name, None)
    except Exception:
        return None


def _call_http_json_adapter_method(
    method: object,
    *args: object,
    **kwargs: object,
) -> object | None:
    if not callable(method):
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _call_http_json_getheader_adapter(
    getheader: object,
    header_name: str,
) -> object | None:
    raw_value = _call_http_json_adapter_method(getheader, header_name, None)
    if raw_value is not None:
        return raw_value
    return _call_http_json_adapter_method(getheader, header_name)


def _get_http_json_response_status_code(
    response: object,
) -> tuple[int | None, object | None]:
    for attr_name in ("status", "code", "status_code"):
        raw_status = _get_http_json_adapter_attr(response, attr_name)
        if not _http_json_response_status_value_is_present(raw_status):
            continue
        status_code = _coerce_http_json_response_status_code(raw_status)
        if status_code is None or not 100 <= status_code <= 599:
            return None, raw_status
        return status_code, None
    getcode = _get_http_json_adapter_attr(response, "getcode")
    if callable(getcode):
        raw_status = _call_http_json_adapter_method(getcode)
        if not _http_json_response_status_value_is_present(raw_status):
            return None, None
        status_code = _coerce_http_json_response_status_code(raw_status)
        if status_code is None or not 100 <= status_code <= 599:
            return None, raw_status
        return status_code, None
    return None, None


def _coerce_http_json_response_text(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, bytes):
        normalized = raw_value.decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, bytearray):
        normalized = bytes(raw_value).decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, memoryview):
        normalized = raw_value.tobytes().decode("utf-8", errors="replace").strip()
        return normalized or None
    return None


def _get_http_json_response_reason(response: object) -> object:
    for attr_name in ("reason", "msg"):
        reason = _coerce_http_json_response_text(
            _get_http_json_adapter_attr(response, attr_name)
        )
        if reason is not None:
            return reason
    return ""


def _get_http_json_response_url(response: object) -> str | None:
    geturl = _get_http_json_adapter_attr(response, "geturl")
    if callable(geturl):
        raw_value = _call_http_json_adapter_method(geturl)
        response_url = _coerce_http_json_response_text(raw_value)
        if response_url is not None:
            return response_url
    response_url = _coerce_http_json_response_text(
        _get_http_json_adapter_attr(response, "url")
    )
    if response_url is not None:
        return response_url
    return None


_HTTP_JSON_UNRESERVED_URL_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _normalize_http_json_unreserved_percent_encoding(value: str) -> str:
    def replace_match(match: re.Match[str]) -> str:
        encoded_value = match.group(0)
        decoded_char = chr(int(encoded_value[1:], 16))
        if decoded_char in _HTTP_JSON_UNRESERVED_URL_CHARS:
            return decoded_char
        return encoded_value.upper()

    return re.sub(r"%[0-9A-Fa-f]{2}", replace_match, value)


def _normalize_http_json_query_for_drift_check(
    raw_query: str,
) -> tuple[tuple[str, str], ...] | None:
    try:
        query_pairs = parse_qsl(raw_query, keep_blank_values=True)
    except ValueError:
        return None
    return tuple(sorted(query_pairs))


def _normalize_http_json_url_for_drift_check(
    raw_url: str,
) -> tuple[str, str, str, str, tuple[tuple[str, str], ...]] | None:
    parsed = urlparse(raw_url)
    hostname = parsed.hostname
    if not parsed.scheme or hostname is None:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    normalized_host = hostname.lower()
    default_port = (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    )
    normalized_authority = (
        normalized_host
        if port is None or default_port
        else f"{normalized_host}:{port}"
    )
    normalized_query = _normalize_http_json_query_for_drift_check(parsed.query)
    if normalized_query is None:
        return None
    return (
        scheme,
        normalized_authority,
        _normalize_http_json_unreserved_percent_encoding(parsed.path or "/"),
        _normalize_http_json_unreserved_percent_encoding(parsed.params),
        normalized_query,
    )


def _http_json_response_url_matches_request_url(
    *,
    response_url: str,
    request_url: str,
) -> bool:
    if response_url == request_url:
        return True
    normalized_response_url = _normalize_http_json_url_for_drift_check(response_url)
    normalized_request_url = _normalize_http_json_url_for_drift_check(request_url)
    return (
        normalized_response_url is not None
        and normalized_request_url is not None
        and normalized_response_url == normalized_request_url
    )


def _format_http_json_redirected_response_url_error(
    response: object | None = None,
) -> str:
    message = "HTTP JSON tool failed: redirected response url does not match request url"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    return message


def _format_http_json_unexpected_status_response(
    *,
    status_code: int,
    reason: object,
    raw_body: bytes,
    content_type: object = None,
    response: object | None = None,
) -> str:
    message = f"HTTP JSON tool failed: HTTP {status_code}"
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_unexpected_status_response_body_decode_error(
    *,
    status_code: int,
    reason: object,
    error: Exception,
    response: object | None = None,
) -> str:
    message = f"HTTP JSON tool failed: HTTP {status_code}"
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_error_body_preview(error)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_empty_response(
    *,
    status_code: int | None,
    reason: object,
    response: object | None = None,
) -> str:
    message = "HTTP JSON tool failed: empty JSON response"
    if status_code is not None:
        message = f"{message}: HTTP {status_code}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    return message


def _coerce_http_json_response_body_bytes(raw_body: object) -> bytes:
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, bytearray):
        return bytes(raw_body)
    if isinstance(raw_body, memoryview):
        return raw_body.tobytes()
    if isinstance(raw_body, UserString):
        return str(raw_body).encode("utf-8")
    if isinstance(raw_body, str):
        return raw_body.encode("utf-8")
    raise TypeError("response body must be bytes or text")


_HTTP_JSON_BODY_DUMP_MISSING = object()


class _HttpJsonJsonBodyDumpMethodUnavailable(TypeError):
    pass


class _HttpJsonJsonBodyDumpJsonMethodUnavailable(TypeError):
    pass


class _HttpJsonResponseBodyAttrUnavailable(TypeError):
    pass


def _is_http_json_parsed_body_attr(raw_body: object) -> bool:
    if isinstance(raw_body, Mapping):
        return True
    if isinstance(raw_body, Sequence) and not isinstance(
        raw_body,
        (str, bytes, bytearray, memoryview),
    ):
        return True
    return (
        callable(_get_http_json_adapter_attr(raw_body, "model_dump_json"))
        or callable(_get_http_json_adapter_attr(raw_body, "to_json"))
        or callable(_get_http_json_adapter_attr(raw_body, "json"))
        or callable(_get_http_json_adapter_attr(raw_body, "model_dump"))
        or callable(_get_http_json_adapter_attr(raw_body, "dict"))
        or callable(_get_http_json_adapter_attr(raw_body, "to_dict"))
    )


def _read_http_json_response_body_attr(
    attr_name: str,
    raw_body: object,
) -> bytes | None:
    if callable(raw_body):
        try:
            raw_body = raw_body()
        except TypeError as exc:
            raise _HttpJsonResponseBodyAttrUnavailable(str(exc)) from exc
        except Exception as exc:
            raise TypeError(f"response body {attr_name} failed: {exc}") from exc
    if raw_body is None:
        return None
    try:
        if attr_name in {"body", "data"} and _is_http_json_parsed_body_attr(raw_body):
            return _coerce_http_json_response_json_body_bytes(raw_body)
        return _coerce_http_json_response_body_bytes(raw_body)
    except TypeError as exc:
        raise _HttpJsonResponseBodyAttrUnavailable(str(exc)) from exc


def _coerce_http_json_json_compatible_body(raw_body: object) -> object:
    if isinstance(raw_body, UserString):
        return str(raw_body)
    if isinstance(raw_body, Mapping):
        return {
            _coerce_http_json_json_compatible_mapping_key(key): (
                _coerce_http_json_json_compatible_body(value)
            )
            for key, value in raw_body.items()
        }
    if isinstance(raw_body, Sequence) and not isinstance(
        raw_body,
        (str, bytes, bytearray, memoryview),
    ):
        return [_coerce_http_json_json_compatible_body(value) for value in raw_body]
    dumped_json_body = _coerce_http_json_json_body_dump_json_compatible(raw_body)
    if dumped_json_body is not _HTTP_JSON_BODY_DUMP_MISSING:
        return _coerce_http_json_json_compatible_body(dumped_json_body)
    for method_name in ("model_dump", "dict", "to_dict"):
        model_dump = _get_http_json_adapter_attr(raw_body, method_name)
        if not callable(model_dump):
            continue
        try:
            return _coerce_http_json_json_compatible_body(
                _call_http_json_json_body_dump_method(method_name, model_dump)
            )
        except _HttpJsonJsonBodyDumpMethodUnavailable:
            continue
    return raw_body


def _coerce_http_json_json_compatible_mapping_key(raw_key: object) -> object:
    if isinstance(raw_key, UserString):
        return str(raw_key)
    return raw_key


def _call_http_json_json_body_dump_method(
    method_name: str,
    model_dump: object,
) -> object:
    if method_name == "model_dump":
        accepts_json_mode = _http_json_callable_accepts_call(model_dump, mode="json")
        if accepts_json_mode is not False:
            try:
                return model_dump(mode="json")  # type: ignore[operator]
            except TypeError as exc:
                if accepts_json_mode is None:
                    pass
                else:
                    raise TypeError(
                        f"response json body {method_name} failed: {exc}"
                    ) from exc
            except Exception as exc:
                raise TypeError(
                    f"response json body {method_name} failed: {exc}"
                ) from exc
    accepts_no_args = _http_json_callable_accepts_call(model_dump)
    if accepts_no_args is False:
        raise _HttpJsonJsonBodyDumpMethodUnavailable(
            f"response json body {method_name} signature requires arguments"
        )
    try:
        return model_dump()  # type: ignore[operator]
    except TypeError as exc:
        if accepts_no_args is None:
            raise _HttpJsonJsonBodyDumpMethodUnavailable(str(exc)) from exc
        raise TypeError(f"response json body {method_name} failed: {exc}") from exc
    except Exception as exc:
        raise TypeError(f"response json body {method_name} failed: {exc}") from exc


def _http_json_callable_accepts_call(
    callable_obj: object,
    **kwargs: object,
) -> bool | None:
    try:
        signature = inspect.signature(callable_obj)  # type: ignore[arg-type]
    except Exception:
        return None
    try:
        signature.bind(**kwargs)
    except TypeError:
        return False
    return True


def _call_http_json_json_body_dump_json_method(
    method_name: str,
    model_dump_json: object,
) -> bytes:
    accepts_no_args = _http_json_callable_accepts_call(model_dump_json)
    if accepts_no_args is False:
        raise _HttpJsonJsonBodyDumpJsonMethodUnavailable(
            f"response json body {method_name} signature requires arguments"
        )
    try:
        dumped_body = model_dump_json()  # type: ignore[operator]
    except TypeError as exc:
        if accepts_no_args is None:
            raise _HttpJsonJsonBodyDumpJsonMethodUnavailable(str(exc)) from exc
        raise TypeError(f"response json body {method_name} failed: {exc}") from exc
    except Exception as exc:
        raise TypeError(f"response json body {method_name} failed: {exc}") from exc
    return _coerce_http_json_response_body_bytes(dumped_body)


def _coerce_http_json_json_body_dump_json_compatible(raw_body: object) -> object:
    for method_name in ("model_dump_json", "to_json", "json"):
        model_dump_json = _get_http_json_adapter_attr(raw_body, method_name)
        if not callable(model_dump_json):
            continue
        try:
            dumped_body = _call_http_json_json_body_dump_json_method(
                method_name,
                model_dump_json,
            )
        except _HttpJsonJsonBodyDumpJsonMethodUnavailable:
            continue
        try:
            return json.loads(dumped_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise TypeError(
                f"response json body {method_name} must be valid JSON: {exc}"
            ) from exc
    return _HTTP_JSON_BODY_DUMP_MISSING


def _read_http_json_json_body_dump_json_bytes(raw_body: object) -> bytes | None:
    for method_name in ("model_dump_json", "to_json", "json"):
        model_dump_json = _get_http_json_adapter_attr(raw_body, method_name)
        if not callable(model_dump_json):
            continue
        try:
            return _call_http_json_json_body_dump_json_method(
                method_name,
                model_dump_json,
            )
        except _HttpJsonJsonBodyDumpJsonMethodUnavailable:
            continue
    return None


def _coerce_http_json_response_json_body_bytes(raw_body: object) -> bytes:
    dumped_json_body = _read_http_json_json_body_dump_json_bytes(raw_body)
    if dumped_json_body is not None:
        return dumped_json_body
    for method_name in ("model_dump", "dict", "to_dict"):
        model_dump = _get_http_json_adapter_attr(raw_body, method_name)
        if not callable(model_dump):
            continue
        try:
            raw_body = _call_http_json_json_body_dump_method(method_name, model_dump)
            break
        except _HttpJsonJsonBodyDumpMethodUnavailable:
            continue
    raw_body = _coerce_http_json_json_compatible_body(raw_body)
    try:
        return json.dumps(
            raw_body,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TypeError(f"response json body must be JSON serializable: {exc}") from exc


class _HttpJsonResponseBodyInitialReadTypeError(TypeError):
    pass


def _read_http_json_response_body_chunked(read: object) -> bytes:
    chunks: list[bytes] = []
    while True:
        try:
            raw_chunk = read(_HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE)
        except TypeError as exc:
            if chunks:
                raise
            raise _HttpJsonResponseBodyInitialReadTypeError(str(exc)) from exc
        except Exception as exc:
            type_error = TypeError(f"response read failed: {exc}")
            if chunks:
                raise type_error from exc
            raise _HttpJsonResponseBodyInitialReadTypeError(str(type_error)) from exc
        if raw_chunk is None:
            break
        try:
            chunk = _coerce_http_json_response_body_bytes(raw_chunk)
        except TypeError as exc:
            if chunks:
                raise
            raise _HttpJsonResponseBodyInitialReadTypeError(str(exc)) from exc
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


class _HttpJsonResponseBodyInitialIteratorTypeError(TypeError):
    pass


class _HttpJsonResponseBodyIteratorUnavailable(TypeError):
    pass


def _read_http_json_response_body_chunks(raw_iterator: object) -> bytes:
    chunks: list[bytes] = []
    try:
        for raw_chunk in raw_iterator:
            if raw_chunk is None:
                continue
            chunk = _coerce_http_json_response_body_bytes(raw_chunk)
            if chunk:
                chunks.append(chunk)
    except TypeError as exc:
        if chunks:
            raise
        raise _HttpJsonResponseBodyInitialIteratorTypeError(str(exc)) from exc
    except Exception as exc:
        type_error = TypeError(f"response body iteration failed: {exc}")
        if chunks:
            raise type_error from exc
        raise _HttpJsonResponseBodyInitialIteratorTypeError(str(type_error)) from exc
    return b"".join(chunks)


def _read_http_json_response_body_iterator(iterator_method: object) -> bytes:
    attempts = (
        ((), {}),
        ((_HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE,), {}),
        ((), {"chunk_size": _HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE}),
    )
    type_error: TypeError | None = None
    for args, kwargs in attempts:
        try:
            raw_iterator = iterator_method(*args, **kwargs)
        except TypeError as exc:
            type_error = exc
            continue
        except Exception as exc:
            type_error = TypeError(f"response body iterator failed: {exc}")
            continue
        if raw_iterator is None:
            type_error = TypeError("response body iterator is unavailable")
            continue
        try:
            return _read_http_json_response_body_chunks(raw_iterator)
        except _HttpJsonResponseBodyInitialIteratorTypeError as exc:
            type_error = exc
            continue
    if type_error is not None:
        raise _HttpJsonResponseBodyIteratorUnavailable(str(type_error)) from type_error
    raise _HttpJsonResponseBodyIteratorUnavailable(
        "response body iterator is unavailable"
    )


def _read_http_json_response_body_bytes(response: object) -> bytes:
    read_type_error: TypeError | None = None
    read_body_type_error: TypeError | None = None
    read_empty_body: bytes | None = None
    attr_type_error: TypeError | None = None
    attr_empty_body: bytes | None = None
    iterator_type_error: TypeError | None = None
    iterator_empty_body: bytes | None = None
    json_type_error: TypeError | None = None
    json_body_type_error: TypeError | None = None
    read = _get_http_json_adapter_attr(response, "read")
    if callable(read):
        try:
            raw_body = read()
        except TypeError as exc:
            read_type_error = exc
            try:
                body = _read_http_json_response_body_chunked(read)
                if body:
                    return body
                read_empty_body = body
            except _HttpJsonResponseBodyInitialReadTypeError:
                pass
        except Exception as exc:
            raise TypeError(f"response read failed: {exc}") from exc
        else:
            try:
                body = _coerce_http_json_response_body_bytes(raw_body)
            except TypeError as exc:
                read_body_type_error = exc
                try:
                    body = _read_http_json_response_body_chunked(read)
                    if body:
                        return body
                    read_empty_body = body
                except _HttpJsonResponseBodyInitialReadTypeError:
                    pass
            else:
                if body:
                    return body
                read_empty_body = body
                try:
                    body = _read_http_json_response_body_chunked(read)
                    if body:
                        return body
                    read_empty_body = body
                except _HttpJsonResponseBodyInitialReadTypeError:
                    pass
    for attr_name in ("content", "body", "data", "text"):
        raw_body = _get_http_json_adapter_attr(response, attr_name)
        if raw_body is None:
            continue
        try:
            body = _read_http_json_response_body_attr(attr_name, raw_body)
        except _HttpJsonResponseBodyAttrUnavailable as exc:
            attr_type_error = exc
            continue
        if body:
            return body
        if body is not None:
            attr_empty_body = body
    for method_name in ("iter_bytes", "iter_content", "iter_text", "iter_lines"):
        body_iterator = _get_http_json_adapter_attr(response, method_name)
        if callable(body_iterator):
            try:
                body = _read_http_json_response_body_iterator(body_iterator)
                if body:
                    return body
                iterator_empty_body = body
            except _HttpJsonResponseBodyIteratorUnavailable as exc:
                iterator_type_error = exc
                continue
    json_body = _get_http_json_adapter_attr(response, "json")
    if callable(json_body):
        try:
            raw_json_body = json_body()
        except TypeError as exc:
            json_type_error = exc
        except Exception as exc:
            raise TypeError(f"response json failed: {exc}") from exc
        else:
            try:
                return _coerce_http_json_response_json_body_bytes(raw_json_body)
            except TypeError as exc:
                json_body_type_error = exc
    if json_body is not None and not callable(json_body):
        try:
            return _coerce_http_json_response_json_body_bytes(json_body)
        except TypeError as exc:
            json_body_type_error = exc
    try:
        response_iterator = iter(response)
    except TypeError:
        response_iterator = None
    if response_iterator is not None:
        try:
            body = _read_http_json_response_body_chunks(response_iterator)
            if body:
                return body
            iterator_empty_body = body
        except _HttpJsonResponseBodyInitialIteratorTypeError as exc:
            if iterator_type_error is None:
                iterator_type_error = exc
    if json_body_type_error is not None:
        raise json_body_type_error
    if attr_empty_body is None and attr_type_error is not None:
        raise attr_type_error
    if read_empty_body is None and read_body_type_error is not None:
        raise read_body_type_error
    if iterator_empty_body is not None:
        return iterator_empty_body
    if attr_empty_body is not None:
        return attr_empty_body
    if read_empty_body is not None:
        return read_empty_body
    if read_type_error is not None:
        raise read_type_error
    if attr_type_error is not None:
        raise attr_type_error
    if iterator_type_error is not None:
        raise iterator_type_error
    if json_type_error is not None:
        raise json_type_error
    raise TypeError("response body reader is unavailable")


def _close_http_json_response(response: object) -> None:
    close = _get_http_json_adapter_attr(response, "close")
    if not callable(close):
        return
    try:
        close()
    except Exception:
        return


def _format_http_json_invalid_json_response(
    *,
    raw_body: bytes,
    error: json.JSONDecodeError | UnicodeDecodeError,
    charset: str = "utf-8",
    content_type: object = None,
    response: object | None = None,
) -> str:
    error_message = (
        error.msg
        if isinstance(error, json.JSONDecodeError)
        else f"invalid {_format_http_json_error_body_preview(charset)} response body: {error.reason}"
    )
    message = f"HTTP JSON tool failed: invalid JSON response: {error_message}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_invalid_charset_response(
    *,
    charset: str,
    raw_body: bytes,
    response: object | None = None,
) -> str:
    safe_charset = _format_http_json_error_body_preview(charset)
    message = f"HTTP JSON tool failed: invalid JSON response charset: {safe_charset}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_error_body_preview(raw_body)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _coerce_http_json_header_text(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, bytes):
        normalized = raw_value.decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, bytearray):
        normalized = bytes(raw_value).decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, memoryview):
        normalized = raw_value.tobytes().decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, (list, tuple)):
        values = [
            header_value
            for item in raw_value
            if (header_value := _coerce_http_json_header_text(item)) is not None
        ]
        return ", ".join(values) if values else None
    return None


def _coerce_http_json_header_name_text(raw_value: object) -> str | None:
    header_name = _coerce_http_json_response_text(raw_value)
    return header_name.lower() if header_name is not None else None


def _get_http_json_header_items(headers: object) -> object:
    for method_name in ("items", "raw_items", "multi_items"):
        items = _get_http_json_adapter_attr(headers, method_name)
        if callable(items):
            header_items = _call_http_json_adapter_method(items)
            if header_items is not None:
                return header_items
    if isinstance(headers, (list, tuple)):
        return headers
    return ()


def _get_http_json_header_value_from_method(
    *,
    headers: object,
    method_name: str,
    header_name: str,
) -> str | None:
    method = _get_http_json_adapter_attr(headers, method_name)
    if not callable(method):
        return None
    for candidate_name in (
        header_name,
        header_name.lower(),
        header_name.upper(),
        header_name.encode("ascii"),
        header_name.lower().encode("ascii"),
        header_name.upper().encode("ascii"),
    ):
        raw_value = _call_http_json_adapter_method(
            method,
            candidate_name,
            None,
        )
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
        raw_value = _call_http_json_adapter_method(
            method,
            candidate_name,
        )
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
    return None


def _get_http_json_header_text_from_mapping(
    headers: object,
    header_name: str,
) -> str | None:
    normalized_header_name = header_name.strip().lower()
    header_values: list[str] = []
    header_items = _get_http_json_header_items(headers)
    for raw_item in header_items:
        try:
            raw_key, raw_value = raw_item
        except (TypeError, ValueError):
            continue
        if _coerce_http_json_header_name_text(raw_key) == normalized_header_name:
            header_value = _coerce_http_json_header_text(raw_value)
            if header_value is not None:
                header_values.append(header_value)
    if header_values:
        return ", ".join(header_values)
    for method_name in ("get_all", "getheaders", "get"):
        header_value = _get_http_json_header_value_from_method(
            headers=headers,
            method_name=method_name,
            header_name=header_name,
        )
        if header_value is not None:
            return header_value
    return None


def _get_http_json_response_header_text(
    response: object,
    header_name: str,
) -> str | None:
    getheader = _get_http_json_adapter_attr(response, "getheader")
    if callable(getheader):
        raw_value = _call_http_json_getheader_adapter(getheader, header_name)
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
    for attr_name in ("headers", "hdrs"):
        headers = _get_http_json_adapter_attr(response, attr_name)
        if headers is None:
            continue
        header_value = _get_http_json_header_text_from_mapping(headers, header_name)
        if header_value is not None:
            return header_value
    info = _get_http_json_adapter_attr(response, "info")
    if callable(info):
        info_headers = _call_http_json_adapter_method(info)
        header_value = _get_http_json_header_text_from_mapping(
            info_headers,
            header_name,
        )
        if header_value is not None:
            return header_value
    return None


def _format_http_json_response_header_diagnostic_hints(response: object) -> str:
    hint_parts: list[str] = []
    seen_labels: set[str] = set()
    for header_name, label in _HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS:
        if label in seen_labels:
            continue
        header_value = _get_http_json_response_header_text(response, header_name)
        if header_value is None:
            continue
        if label == "request id" and not _is_safe_http_json_request_id_value(header_value):
            continue
        safe_header_value = _format_http_json_error_body_preview(header_value)
        if not safe_header_value:
            continue
        hint_parts.append(f"{label}: {safe_header_value}")
        seen_labels.add(label)
    return "; ".join(hint_parts)


def _get_http_json_response_request_id(response: object) -> str | None:
    for header_name in _HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES:
        header_value = _get_http_json_response_header_text(response, header_name)
        if header_value is None:
            continue
        normalized = header_value.strip()
        if not normalized:
            continue
        if not _is_safe_http_json_request_id_value(normalized):
            continue
        return normalized
    return None


def _is_safe_http_json_request_id_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if len(normalized) > 128:
        return False
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in normalized):
        return False
    safe_value = _format_http_json_error_body_preview(normalized)
    return safe_value == normalized


def _get_safe_http_json_request_id_display_value(value: object) -> str | None:
    value = _coerce_tool_execution_string_like_value(value)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized == "[redacted]":
        return None
    if not _is_safe_http_json_request_id_value(normalized):
        return None
    return normalized


def _attach_http_json_response_request_id(
    output: dict[str, object],
    request_id: str | None,
) -> dict[str, object]:
    safe_existing_request_id = _get_safe_http_json_request_id_display_value(
        output.get("request_id")
    )
    if safe_existing_request_id is not None:
        output["request_id"] = safe_existing_request_id
        return output
    if "request_id" in output:
        output.pop("request_id", None)
    if not request_id:
        return output
    output["request_id"] = request_id
    return output


def _get_http_json_response_content_type(response: object) -> str | None:
    return _get_http_json_response_header_text(response, "Content-Type")


def _get_http_json_response_content_encoding(response: object) -> str | None:
    return _get_http_json_response_header_text(response, "Content-Encoding")


def _split_http_json_header_value(
    raw_value: str,
    *,
    separator: str,
) -> tuple[str, ...]:
    values: list[str] = []
    current_value: list[str] = []
    quote_char: str | None = None
    escaped = False
    for char in raw_value:
        if escaped:
            current_value.append(char)
            escaped = False
            continue
        if quote_char is not None:
            current_value.append(char)
            if char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in ("'", '"'):
            quote_char = char
            current_value.append(char)
            continue
        if char == separator:
            normalized_value = "".join(current_value).strip()
            if normalized_value:
                values.append(normalized_value)
            current_value = []
            continue
        current_value.append(char)
    normalized_value = "".join(current_value).strip()
    if normalized_value:
        values.append(normalized_value)
    return tuple(values)


def _split_http_json_header_values(raw_value: str) -> tuple[str, ...]:
    return _split_http_json_header_value(raw_value, separator=",")


def _split_http_json_header_parameters(raw_value: str) -> tuple[str, ...]:
    return _split_http_json_header_value(raw_value, separator=";")


def _get_http_json_response_charset(raw_content_type: object) -> str:
    if not isinstance(raw_content_type, str) or ";" not in raw_content_type:
        return "utf-8"
    charset_values: list[str] = []
    for content_type_value in _split_http_json_header_values(raw_content_type):
        for raw_parameter in _split_http_json_header_parameters(content_type_value)[1:]:
            raw_name, separator, raw_value = raw_parameter.partition("=")
            if raw_name.strip().lower() != "charset":
                continue
            if not separator:
                charset_values.append("")
                continue
            normalized_value = raw_value.strip().strip("\"'")
            charset_values.append(normalized_value if normalized_value else "")
    if not charset_values:
        return "utf-8"
    normalized_charset_values = {
        charset_value.lower().replace("_", "-")
        for charset_value in charset_values
    }
    if len(normalized_charset_values) > 1:
        safe_values = ", ".join(charset_values[:3])
        if len(charset_values) > 3:
            safe_values = f"{safe_values}, ..."
        return f"ambiguous response charset: {safe_values}"
    return charset_values[0]


def _decode_http_json_response_text(
    *,
    raw_body: bytes,
    content_type: object,
    response: object | None = None,
) -> str:
    charset = _get_http_json_response_charset(content_type)
    try:
        codecs.lookup(charset)
    except LookupError as exc:
        raise MockToolExecutionError(
            _format_http_json_invalid_charset_response(
                charset=charset,
                raw_body=raw_body,
                response=response,
            ),
            fatal=False,
        ) from exc
    try:
        return raw_body.decode(charset)
    except UnicodeDecodeError as exc:
        raise MockToolExecutionError(
            _format_http_json_invalid_json_response(
                raw_body=raw_body,
                error=exc,
                charset=charset,
                content_type=content_type,
                response=response,
            ),
            fatal=False,
        ) from exc


def _normalize_http_json_content_encodings(raw_value: object) -> tuple[str, ...]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ()
    encodings = [
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    ]
    return tuple(encodings)


def _decompress_http_json_deflate_body(raw_body: bytes) -> bytes:
    try:
        return zlib.decompress(raw_body)
    except zlib.error as wrapped_exc:
        try:
            return zlib.decompress(raw_body, -zlib.MAX_WBITS)
        except zlib.error as raw_exc:
            raise raw_exc from wrapped_exc


def _decode_http_json_response_body_for_content_encoding(
    *,
    raw_body: bytes,
    content_encoding: object,
    content_type: object = None,
) -> bytes:
    decoded_body = raw_body
    normalized_encodings = _normalize_http_json_content_encodings(content_encoding)
    if not normalized_encodings:
        return decoded_body
    for normalized_encoding in reversed(normalized_encodings):
        if normalized_encoding == "identity":
            continue
        if normalized_encoding == "gzip":
            try:
                decoded_body = gzip.decompress(decoded_body)
            except (OSError, EOFError, zlib.error) as exc:
                body_preview = _format_http_json_response_body_preview(
                    decoded_body,
                    content_type=content_type,
                )
                message = "invalid gzip response body"
                if body_preview:
                    message = f"{message}; body: {body_preview}"
                raise ValueError(message) from exc
            continue
        if normalized_encoding == "deflate":
            try:
                decoded_body = _decompress_http_json_deflate_body(decoded_body)
            except zlib.error as exc:
                body_preview = _format_http_json_response_body_preview(
                    decoded_body,
                    content_type=content_type,
                )
                message = "invalid deflate response body"
                if body_preview:
                    message = f"{message}; body: {body_preview}"
                raise ValueError(message) from exc
            continue
        safe_encoding = _format_http_json_error_body_preview(
            ",".join(normalized_encodings)
        )
        body_preview = _format_http_json_response_body_preview(
            decoded_body,
            content_type=content_type,
        )
        message = f"unsupported response content-encoding: {safe_encoding}"
        if body_preview:
            message = f"{message}; body: {body_preview}"
        raise ValueError(message)
    return decoded_body


def _is_supported_http_json_response_content_type(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return True
    if not _http_json_header_value_has_balanced_quoted_parameters(raw_value):
        return False
    content_type_values = _split_http_json_header_values(raw_value)
    if not content_type_values:
        return False
    for content_type_value in content_type_values:
        media_type = content_type_value.split(";", 1)[0].strip().lower()
        if not (media_type == "application/json" or media_type.endswith("+json")):
            return False
    return True


def _format_http_json_invalid_content_type_response(
    *,
    content_type: str,
    raw_body: bytes,
    response: object | None = None,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(content_type)
    message = (
        "HTTP JSON tool failed: invalid JSON response content-type: "
        f"{safe_content_type}"
    )
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_transport_error(
    exc: BaseException,
    response: object | None = None,
) -> str:
    raw_reason = getattr(exc, "reason", None)
    reason = raw_reason if raw_reason is not None else exc
    reason_preview = _format_http_json_error_body_preview(reason)
    if reason_preview:
        message = f"HTTP JSON tool failed: transport error: {reason_preview}"
    else:
        message = "HTTP JSON tool failed: transport error"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    return message


def _format_http_json_mapping_path_for_error(raw_path: object) -> str:
    safe_path = _format_safe_tool_execution_diagnostic_path(str(raw_path).strip())
    return _format_http_json_error_body_preview(safe_path)


def _format_http_json_mapping_payload_shape_key_for_error(raw_key: object) -> str:
    safe_key = _format_safe_tool_execution_summary_field_name(raw_key)
    if not safe_key:
        return ""
    safe_key = _format_http_json_error_body_preview(safe_key)
    if len(safe_key) <= _HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH:
        return safe_key
    return f"{safe_key[:_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH]}..."


def _format_http_json_mapping_payload_shape_keys_for_error(payload: dict) -> str:
    safe_keys: list[str] = []
    seen_keys: set[str] = set()
    for raw_key in payload.keys():
        safe_key = _format_http_json_mapping_payload_shape_key_for_error(raw_key)
        if not safe_key or safe_key in seen_keys:
            continue
        seen_keys.add(safe_key)
        safe_keys.append(safe_key)
    if not safe_keys:
        return "none"
    visible_keys = safe_keys[:_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS]
    hidden_count = len(safe_keys) - len(visible_keys)
    if hidden_count > 0:
        visible_keys.append(f"and {hidden_count} more")
    return ", ".join(visible_keys)


def _format_http_json_mapping_payload_shape_for_error(payload: object) -> str:
    if isinstance(payload, dict):
        keys = _format_http_json_mapping_payload_shape_keys_for_error(payload)
        return f"available response keys: {keys}"
    if isinstance(payload, list):
        message = f"response payload is a list with {len(payload)} items"
        if payload and isinstance(payload[0], dict):
            keys = _format_http_json_mapping_payload_shape_keys_for_error(payload[0])
            message = f"{message}; first item keys: {keys}"
        return message
    if payload is None:
        return "response payload is null"
    if isinstance(payload, bool):
        return "response payload is a boolean"
    if isinstance(payload, (int, float)):
        return "response payload is a number"
    if isinstance(payload, str):
        return "response payload is a string"
    return "response payload has an unsupported shape"


def _format_http_json_result_field_mapping_error(
    *,
    field_name: str,
    raw_path: object,
) -> str:
    safe_field_name = _format_safe_tool_execution_summary_field_name(field_name)
    safe_path = _format_http_json_mapping_path_for_error(raw_path)
    return f"{safe_field_name} -> {safe_path}"


def _format_http_json_missing_result_field_mappings(
    missing_result_fields: list[str],
) -> str:
    visible_mappings = missing_result_fields[
        :_HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS
    ]
    hidden_count = len(missing_result_fields) - len(visible_mappings)
    if hidden_count > 0:
        visible_mappings.append(f"and {hidden_count} more")
    return "; ".join(visible_mappings)
