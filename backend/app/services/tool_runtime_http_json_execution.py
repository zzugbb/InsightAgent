from __future__ import annotations

from app.services import tool_runtime_http_json as _http_json


def _bind_http_json_namespace(namespace: dict[str, object]) -> None:
    globals().update(
        {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__")
        }
    )


_bind_http_json_namespace(vars(_http_json))


_EXECUTION_IMPL_EXPORTS: tuple[str, ...] = (
    '_build_http_json_tool_runner',
    '_build_invalid_tool_execution_runner',
    '_build_tool_runner_from_execution_spec',
    '_resolve_tool_execution_kind_from_spec',
    '_build_tool_execution_summary_from_spec',
    '_resolve_tool_execution_summary_value',
    '_resolve_tool_execution_string_like_summary_value',
    '_format_safe_tool_execution_summary_url_path',
    '_sanitize_tool_execution_summary_value',
    'sanitize_tool_execution_summary',
    'sanitize_tool_execution_diagnostics',
    '_describe_tool_execution_spec_validation_error',
    '_describe_tool_execution_spec_validation_errors',
    '_build_invalid_tool_execution_diagnostics',
    '_group_invalid_tool_execution_messages_by_tool',
    '_collect_invalid_tool_execution_messages_from_extra_tool_specs',
    '_collect_invalid_tool_execution_messages_from_override_specs',
    'build_tool_registry_settings_execution_diagnostics',
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



def bind_tool_runtime_http_json_execution_public_names(
    namespace: dict[str, object],
) -> None:
    _bind_http_json_namespace(namespace)
