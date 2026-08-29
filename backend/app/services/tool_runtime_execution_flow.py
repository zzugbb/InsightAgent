from __future__ import annotations

import re


def bind_tool_runtime_execution_flow_public_names(namespace: dict[str, object]) -> None:
    globals().update(namespace)


def build_tool_trace_event(
    *,
    task_id: str,
    step_id: str,
    step: dict[str, object],
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "step": _sanitize_tool_trace_event_step(step),
    }


def _sanitize_tool_trace_event_step(step: dict[str, object]) -> dict[str, object]:
    tool_obj = get_action_step_tool_meta(step)
    if not _step_tool_meta_uses_http_json_execution(tool_obj):
        return step
    sanitized_step = dict(step)
    meta = sanitized_step.get("meta")
    if not isinstance(meta, dict):
        return step
    sanitized_meta = dict(meta)
    sanitized_tool = dict(tool_obj) if isinstance(tool_obj, dict) else {}
    safe_output = build_tool_step_output(step)
    if isinstance(safe_output, dict):
        sanitized_tool["output"] = safe_output
    preview_value = sanitized_tool.get("output_preview")
    preview_mapping = _coerce_tool_output_preview_mapping(preview_value)
    if isinstance(preview_mapping, dict):
        sanitized_tool["output_preview"] = _normalize_http_json_safe_output_shape(
            preview_mapping
        )
    elif isinstance(preview_value, str):
        sanitized_tool["output_preview"] = _redact_http_json_raw_fallback_value(
            preview_value
        )
    sanitized_meta["tool"] = sanitized_tool
    sanitized_step["meta"] = sanitized_meta
    return sanitized_step


def _sanitize_tool_trace_event_payload(event: object) -> object:
    if not isinstance(event, dict):
        return event
    step = event.get("step")
    if not isinstance(step, dict):
        return event
    sanitized_step = _sanitize_tool_trace_event_step(step)
    if sanitized_step is step:
        return event
    sanitized_event = dict(event)
    sanitized_event["step"] = sanitized_step
    return sanitized_event


def build_tool_terminal_failure_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return _sanitize_tool_terminal_failure_payload(
        {
            "trace": build_tool_trace_event(
                task_id=task_id,
                step_id=step_id,
                step=action_step,
            ),
            "audit_detail": {
                "step_id": step_id,
                "retry_count": retry_count,
            },
            "state": {
                "task_id": task_id,
                "phase": "error",
            },
            "status": "failed",
            "error_message": error_message,
        }
    )


def _sanitize_tool_terminal_failure_payload(
    payload: dict[str, object] | None,
) -> dict[str, object] | None:
    if payload is None:
        return None
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "terminal_failure"):
        if key in sanitized:
            sanitized[key] = _sanitize_tool_runtime_trace_artifact_payload(
                sanitized[key]
            )
    if "success_bundle" in sanitized:
        sanitized["success_bundle"] = _sanitize_tool_plan_success_bundle_payload(
            sanitized["success_bundle"]
        )
    if "last_error" in sanitized:
        sanitized["last_error"] = sanitize_tool_registry_diagnostics_artifact_payload(
            sanitized["last_error"]
        )
    return sanitized


def _sanitize_tool_plan_success_bundle_payload(
    success_bundle: object,
) -> object:
    if not isinstance(success_bundle, dict):
        return success_bundle
    bundle = dict(success_bundle)
    if "trace" in bundle:
        bundle["trace"] = _sanitize_tool_trace_event_payload(bundle["trace"])
    if "rag_followup" in bundle:
        bundle["rag_followup"] = _sanitize_tool_plan_success_bundle_rag_followup_payload(
            bundle["rag_followup"]
        )
    return bundle


def _sanitize_tool_plan_success_bundle_rag_followup_payload(
    rag_followup: object,
) -> object:
    if not isinstance(rag_followup, dict):
        return rag_followup
    followup = dict(rag_followup)
    step = followup.get("step")
    if isinstance(step, dict):
        followup["step"] = _sanitize_tool_trace_event_step(step)
    if "trace" in followup:
        followup["trace"] = _sanitize_tool_trace_event_payload(followup["trace"])
    return followup


def build_tool_rag_step(
    *,
    step_id: str,
    seq: int,
    model: str,
    chunks: list[str],
    chunk_metadata: list[dict[str, object]] | None = None,
    knowledge_base_id: str | None,
    token_count: int,
    content: str | None = None,
) -> dict[str, object]:
    rag_meta: dict[str, object] = {
        "chunks": chunks,
    }
    if isinstance(knowledge_base_id, str) and knowledge_base_id:
        rag_meta["knowledge_base_id"] = normalize_knowledge_base_id(knowledge_base_id)
    safe_chunk_metadata = [
        dict(metadata)
        for metadata in (chunk_metadata or [])
        if isinstance(metadata, dict) and metadata
    ]
    if safe_chunk_metadata:
        rag_meta["chunk_metadata"] = safe_chunk_metadata
        document_versions = _build_tool_rag_document_versions(safe_chunk_metadata)
        if document_versions:
            rag_meta["document_versions"] = document_versions
    return {
        "id": step_id,
        "seq": seq,
        "type": "thought",
        "content": content
        or "Knowledge Retrieval returned snippets from the selected knowledge base.",
        "meta": {
            "model": model,
            "step_type": "rag_retrieval",
            "tokens": token_count,
            "cost_estimate": None,
            "rag": rag_meta,
        },
    }


def _build_tool_rag_followup_content(
    *,
    display_name: str | None,
    runtime_semantic_kind: str | None,
    semantic_family: str | None,
) -> str:
    normalized_display_name = (
        str(display_name).strip() if isinstance(display_name, str) else ""
    )
    normalized_runtime_semantic_kind = _normalize_tool_semantic_kind(
        runtime_semantic_kind
    )
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        normalized_runtime_semantic_kind != "knowledge_retrieval"
        and normalized_semantic_family == "knowledge_retrieval"
    ):
        if normalized_display_name:
            return f"{normalized_display_name} returned snippets."
        return "Knowledge Retrieval returned snippets."
    if normalized_display_name and normalized_display_name != "Knowledge Retrieval":
        return f"{normalized_display_name} returned snippets from the selected knowledge base."
    return "Knowledge Retrieval returned snippets from the selected knowledge base."


_TOOL_RAG_DOCUMENT_TEXT_FIELDS = (
    "snippet",
    "snippet_text",
    "snippetText",
    "content",
    "content_text",
    "contentText",
    "text",
    "text_content",
    "textContent",
    "excerpt",
    "summary",
    "description",
    "body",
    "body_text",
    "bodyText",
    "plain_text",
    "plainText",
    "markdown",
    "chunk",
    "chunkText",
    "passage",
    "page_content",
    "pageContent",
    "document_text",
    "documentText",
)
_TOOL_RAG_DOCUMENT_CONTAINER_FIELDS = (
    "metadata",
    "document",
    "payload",
    "_source",
    "chunk",
    "node",
    "data",
    "record",
    "item",
    "attributes",
    "source",
    "fields",
    "entity",
    "rich_snippet",
    "richSnippet",
    "top",
    "detected_extensions",
    "detectedExtensions",
)
_TOOL_RAG_DOCUMENT_LIST_FIELDS = (
    "documents",
    "items",
    "results",
    "hits",
    "matches",
    "organic_results",
    "organicResults",
    "points",
    "source_nodes",
    "sourceNodes",
    "data",
    "records",
    "value",
)
_TOOL_RAG_DOCUMENT_VERSION_RE = re.compile(r"^sha256:[a-f0-9]{16,64}$")
_TOOL_RAG_CONTENT_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_TOOL_RAG_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(^|[?&#;\s])(?:api[_-]?key|access[_-]?token|token|secret|password)=[^&#;\s]+"
)


def _redact_tool_rag_chunk_text(raw_value: str) -> str:
    return _redact_http_json_sensitive_payload_text(raw_value)


def _sanitize_tool_rag_metadata_text(value: object, *, limit: int) -> str | None:
    raw = _coerce_tool_execution_string_like_value(value)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    safe = _redact_tool_rag_chunk_text(text)
    safe = _TOOL_RAG_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        safe,
    )
    return safe[:limit]


def _sanitize_tool_rag_document_version(value: object) -> str | None:
    raw = _sanitize_tool_rag_metadata_text(value, limit=80)
    if raw and _TOOL_RAG_DOCUMENT_VERSION_RE.fullmatch(raw):
        return raw
    return None


def _sanitize_tool_rag_content_hash(value: object) -> str | None:
    raw = _sanitize_tool_rag_metadata_text(value, limit=80)
    if raw and _TOOL_RAG_CONTENT_HASH_RE.fullmatch(raw):
        return raw
    return None


def _coerce_tool_rag_metadata_mapping(raw_document: Mapping) -> dict[str, object]:
    metadata: dict[str, object] = {}
    raw_metadata = raw_document.get("metadata")
    if isinstance(raw_metadata, Mapping):
        metadata.update(dict(raw_metadata))
    for key in (
        "source",
        "document_id",
        "documentId",
        "document_version",
        "documentVersion",
        "content_hash",
        "contentHash",
    ):
        if key in raw_document:
            metadata[key] = raw_document[key]
    return metadata


def _build_tool_rag_chunk_metadata(raw_document: Mapping) -> dict[str, object]:
    raw_metadata = _coerce_tool_rag_metadata_mapping(raw_document)
    metadata: dict[str, object] = {}
    source = _sanitize_tool_rag_metadata_text(raw_metadata.get("source"), limit=240)
    if source:
        metadata["source"] = source
    raw_document_id = raw_metadata.get("document_id", raw_metadata.get("documentId"))
    document_id = _sanitize_tool_rag_metadata_text(raw_document_id, limit=128)
    if document_id:
        metadata["document_id"] = document_id
    raw_document_version = raw_metadata.get(
        "document_version",
        raw_metadata.get("documentVersion"),
    )
    document_version = _sanitize_tool_rag_document_version(raw_document_version)
    if document_version:
        metadata["document_version"] = document_version
    raw_content_hash = raw_metadata.get("content_hash", raw_metadata.get("contentHash"))
    content_hash = _sanitize_tool_rag_content_hash(raw_content_hash)
    if content_hash:
        metadata["content_hash"] = content_hash
    return metadata


def _extract_tool_rag_chunk_from_document_mapping(
    raw_document: dict,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> str | None:
    if depth > 4:
        return None
    if visited is None:
        visited = set()
    document_id = id(raw_document)
    if document_id in visited:
        return None
    visited.add(document_id)
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        raw_value = raw_document.get(field_name)
        if not isinstance(raw_value, str):
            continue
        normalized_chunk = raw_value.strip()
        if normalized_chunk:
            return _redact_tool_rag_chunk_text(normalized_chunk)
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        nested_document = raw_document.get(field_name)
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    for container_name in _TOOL_RAG_DOCUMENT_CONTAINER_FIELDS:
        nested_document = raw_document.get(container_name)
        if isinstance(nested_document, str):
            normalized_chunk = nested_document.strip()
            if normalized_chunk:
                return _redact_tool_rag_chunk_text(normalized_chunk)
            continue
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    return None


def _extract_tool_rag_chunks_from_document_list(raw_documents: object) -> list[str]:
    normalized_documents = _extract_http_json_retrieval_list_from_container(raw_documents)
    if normalized_documents is None:
        return []
    extracted_chunks: list[str] = []
    for raw_document in normalized_documents:
        if isinstance(raw_document, str):
            normalized_chunk = raw_document.strip()
            if normalized_chunk:
                extracted_chunks.append(_redact_tool_rag_chunk_text(normalized_chunk))
            continue
        if not isinstance(raw_document, dict):
            continue
        normalized_chunk = _extract_tool_rag_chunk_from_document_mapping(raw_document)
        if normalized_chunk:
            extracted_chunks.append(normalized_chunk)
    return extracted_chunks


def _extract_tool_rag_chunks_from_output(output: dict[str, object]) -> list[str]:
    raw_chunks = output.get("chunks")
    if isinstance(raw_chunks, (list, tuple)):
        extracted_chunks = _extract_tool_rag_chunks_from_document_list(raw_chunks)
        if extracted_chunks:
            return extracted_chunks

    for list_field_name in _TOOL_RAG_DOCUMENT_LIST_FIELDS:
        extracted_chunks = _extract_tool_rag_chunks_from_document_list(
            output.get(list_field_name)
        )
        if extracted_chunks:
            return extracted_chunks
    return []


def _extract_tool_rag_chunk_metadata_from_document_list(
    raw_documents: object,
) -> list[dict[str, object]]:
    normalized_documents = _extract_http_json_retrieval_list_from_container(raw_documents)
    if normalized_documents is None:
        return []
    chunk_metadata: list[dict[str, object]] = []
    for raw_document in normalized_documents:
        if isinstance(raw_document, str):
            if raw_document.strip():
                chunk_metadata.append({})
            continue
        if not isinstance(raw_document, Mapping):
            continue
        raw_mapping = dict(raw_document)
        normalized_chunk = _extract_tool_rag_chunk_from_document_mapping(raw_mapping)
        if normalized_chunk:
            chunk_metadata.append(_build_tool_rag_chunk_metadata(raw_document))
    return chunk_metadata


def _extract_tool_rag_chunk_metadata_from_output(
    output: dict[str, object],
) -> list[dict[str, object]]:
    extracted = _extract_tool_rag_chunk_metadata_from_document_list(
        output.get("chunks")
    )
    if extracted and any(item for item in extracted):
        return extracted
    for list_field_name in _TOOL_RAG_DOCUMENT_LIST_FIELDS:
        extracted = _extract_tool_rag_chunk_metadata_from_document_list(
            output.get(list_field_name)
        )
        if extracted and any(item for item in extracted):
            return extracted
    return []


def _build_tool_rag_document_versions(
    chunk_metadata: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for metadata in chunk_metadata:
        document_version = str(metadata.get("document_version") or "").strip()
        content_hash = str(metadata.get("content_hash") or "").strip()
        if not _TOOL_RAG_DOCUMENT_VERSION_RE.fullmatch(document_version):
            continue
        if not _TOOL_RAG_CONTENT_HASH_RE.fullmatch(content_hash):
            continue
        key = f"{document_version}\x1f{content_hash}"
        if key not in grouped:
            grouped[key] = {
                "document_version": document_version,
                "content_hash": content_hash,
                "chunk_count": 0,
            }
            source = str(metadata.get("source") or "").strip()
            if source:
                grouped[key]["source"] = source
            document_id = str(metadata.get("document_id") or "").strip()
            if document_id:
                grouped[key]["document_id"] = document_id
        grouped[key]["chunk_count"] = int(grouped[key]["chunk_count"]) + 1
    document_versions = list(grouped.values())
    document_versions.sort(
        key=lambda item: (
            str(item.get("source") or ""),
            str(item.get("document_id") or ""),
            str(item.get("document_version") or ""),
        )
    )
    return document_versions


def build_tool_prompt_with_observations(
    *,
    prompt: str,
    tool_observations: list[str],
) -> str:
    if not tool_observations:
        return prompt
    return f"{prompt}\n\nTool observations:\n" + "\n".join(tool_observations)


def build_tool_attempt_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    events: dict[str, dict[str, object]],
    retryable: bool,
    error_message: str | None,
    retry_count: int,
) -> dict[str, object]:
    result = {
        "outcome": outcome,
        "action_step": action_step,
        "events": events,
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }
    if outcome == "success" and error_message is None:
        return result
    return _sanitize_tool_attempt_error_result_payload(result)


def _sanitize_tool_attempt_error_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "events", "error_message"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


def build_tool_attempt_outcome(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
    if exc is None:
        assert output is not None
        success_transition = build_tool_attempt_success_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            output=output,
            retry_count=runtime_ctx.attempt,
            token_count=token_count,
            last_error=last_error,
            display_name=display_name,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        return build_tool_attempt_result(
            outcome="success",
            action_step=success_transition["action_step"],
            events=success_transition["events"],
            retryable=False,
            error_message=None,
            retry_count=runtime_ctx.attempt,
        )

    error_transition = build_tool_attempt_error_transition(
        task_id=task_id,
        step_id=step_id,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        exc=exc,
        token_count=token_count,
        display_name=display_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return build_tool_attempt_result(
        outcome="error",
        action_step=error_transition["action_step"],
        events=error_transition["events"],
        retryable=bool(error_transition["retryable"]),
        error_message=str(error_transition["error_message"]),
        retry_count=int(error_transition["retry_count"]),
    )


def build_tool_iteration_context(
    *,
    step_id: str,
    seq: int,
    name: str,
    tool_input: dict[str, object],
    model: str,
    label: str,
    token_count: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    return {
        "step_id": step_id,
        "action_step": build_action_step_initial_step(
            step_id=step_id,
            seq=seq,
            name=canonical_name,
            meta=build_action_step_initial_meta(
                name=canonical_name,
                tool_input=tool_input,
                model=model,
                label=label,
                token_count=token_count,
                display_name=display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        ),
    }


def build_tool_iteration_success_artifacts(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    output = build_tool_step_output(action_step)
    step_tool_meta = get_action_step_tool_meta(action_step)
    canonical_name = normalize_tool_registry_name(name)
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "observation": build_tool_observation_entry(
            name=canonical_name,
            output=output,
            display_name=display_name,
            step_tool_meta=step_tool_meta,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "output": output,
    }


def build_tool_rag_followup(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    tool_name: str,
    tool_kind: str | None = None,
    tool_semantic_family: str | None = None,
    display_name: str | None = None,
    output: dict[str, object] | None,
    token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object] | None:
    if not isinstance(output, dict):
        return None
    runtime_semantic_kind = _normalize_tool_semantic_kind(tool_kind)
    if runtime_semantic_kind is None:
        runtime_semantic_kind = _get_tool_runtime_trace_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_family = _normalize_tool_semantic_kind(tool_semantic_family)
    if semantic_family is None:
        semantic_family = get_tool_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_kind = runtime_semantic_kind
    if semantic_kind != "knowledge_retrieval":
        semantic_kind = semantic_family
    if semantic_kind != "knowledge_retrieval":
        return None
    chunks = _extract_tool_rag_chunks_from_output(output)
    if not chunks:
        return None
    chunk_metadata = _extract_tool_rag_chunk_metadata_from_output(output)
    kb = output.get("knowledge_base_id")
    step = build_tool_rag_step(
        step_id=step_id,
        seq=seq,
        model=model,
        chunks=chunks,
        chunk_metadata=chunk_metadata,
        knowledge_base_id=str(kb) if kb else None,
        token_count=token_count,
        content=_build_tool_rag_followup_content(
            display_name=display_name,
            runtime_semantic_kind=runtime_semantic_kind,
            semantic_family=semantic_family,
        ),
    )
    return {
        "step": step,
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=step,
        ),
    }


def build_tool_iteration_execution(
    *,
    task_id: str,
    step_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    normalized_output = (
        normalize_tool_output_for_registration(
            output=output,
            registration=runtime_ctx.registration,
        )
        if isinstance(output, dict)
        else output
    )
    execution_display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
    start_events = build_tool_attempt_start_events(
        task_id=task_id,
        step_id=step_id,
        name=name,
        tool_input=tool_input,
        attempt=runtime_ctx.attempt,
        display_name=execution_display_name,
        registration=runtime_ctx.registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outcome = build_tool_attempt_outcome(
        task_id=task_id,
        step_id=step_id,
        action_step=dict(action_step),
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=normalized_output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if outcome["outcome"] == "success":
        observation_display_name = get_tool_observation_display_name_from_registration(
            name=runtime_ctx.registration.name,
            registration=runtime_ctx.registration,
        )
        return {
            "start_events": start_events,
            "outcome": outcome,
            "success_artifacts": build_tool_iteration_success_artifacts(
                task_id=task_id,
                step_id=step_id,
                action_step=outcome["action_step"],
                name=name,
                display_name=observation_display_name,
                registration=runtime_ctx.registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
            "rag_source_output": normalized_output if isinstance(normalized_output, dict) else None,
            "terminal_failure": None,
        }

    terminal_failure = None
    if not bool(outcome["retryable"]):
        terminal_failure = build_tool_terminal_failure_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=outcome["action_step"],
            error_message=str(outcome["error_message"]),
            retry_count=int(outcome["retry_count"]),
        )
    return {
        "start_events": start_events,
        "outcome": outcome,
        "success_artifacts": None,
        "terminal_failure": terminal_failure,
    }


def build_tool_plan_item_success_bundle(
    *,
    success_artifacts: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "trace": success_artifacts["trace"],
        "observation": success_artifacts["observation"],
        "output": success_artifacts["output"],
        "rag_followup": rag_followup,
    }


def build_tool_plan_item_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    last_error: str | None,
    success_bundle: dict[str, object] | None,
    terminal_failure: dict[str, object] | None,
) -> dict[str, object]:
    return _sanitize_tool_plan_item_result_payload(
        {
            "outcome": outcome,
            "action_step": action_step,
            "last_error": last_error,
            "success_bundle": success_bundle,
            "terminal_failure": terminal_failure,
        }
    )


def build_tool_plan_item_execution_result(
    *,
    iteration_execution: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    success_artifacts = iteration_execution.get("success_artifacts")
    terminal_failure = iteration_execution.get("terminal_failure")
    outcome = iteration_execution["outcome"]
    action_step = outcome["action_step"]
    error_message = outcome.get("error_message")

    if success_artifacts is not None:
        return build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=error_message,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

    return build_tool_plan_item_result(
        outcome="terminal_failure",
        action_step=action_step,
        last_error=error_message,
        success_bundle=None,
        terminal_failure=terminal_failure,
    )


def build_tool_plan_item_execution(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    model: str,
    rag_step_id: str,
    rag_token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    iteration_execution = build_tool_iteration_execution(
        task_id=task_id,
        step_id=str(iteration_ctx["step_id"]),
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    success_artifacts = iteration_execution.get("success_artifacts")
    rag_followup = None
    if success_artifacts is not None:
        success_output = iteration_execution.get("rag_source_output")
        if not isinstance(success_output, dict):
            success_output = success_artifacts["output"]
        rag_followup = build_tool_rag_followup(
            task_id=task_id,
            step_id=rag_step_id,
            seq=int(action_step.get("seq", 0)) + 1,
            model=model,
            tool_name=name,
            tool_kind=_get_tool_runtime_trace_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            tool_semantic_family=get_tool_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            display_name=get_tool_display_name_from_registration(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            output=success_output if isinstance(success_output, dict) else None,
            token_count=rag_token_count,
        )
    plan_item_result = build_tool_plan_item_execution_result(
        iteration_execution=iteration_execution,
        rag_followup=rag_followup,
    )
    attempt_outcome = iteration_execution["outcome"]
    postprocess = None
    success_effects = None
    terminal_effects = None
    if plan_item_result["success_bundle"] is not None:
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )
        success_effects = build_tool_plan_item_success_effects(
            action_step=plan_item_result["action_step"],
            postprocess=postprocess,
        )
    elif plan_item_result["terminal_failure"] is not None:
        terminal_effects = build_tool_plan_item_terminal_effects(
            action_step=plan_item_result["action_step"],
            terminal_failure=plan_item_result["terminal_failure"],
        )
    return {
        "start_events": iteration_execution["start_events"],
        "iteration_execution": iteration_execution,
        "tool_end_event": attempt_outcome["events"]["tool_end"],
        "error_event": attempt_outcome["events"].get("error"),
        "retryable": bool(attempt_outcome["retryable"]),
        "postprocess": postprocess,
        "success_effects": success_effects,
        "terminal_effects": terminal_effects,
        "plan_item_result": plan_item_result,
        "next_action_step": plan_item_result["action_step"],
        "last_error": plan_item_result["last_error"],
        "terminal_failure": plan_item_result["terminal_failure"],
    }


def build_tool_plan_item_postprocess(
    *,
    plan_item_result: dict[str, object],
) -> dict[str, object]:
    success_bundle = plan_item_result["success_bundle"]
    assert success_bundle is not None
    return {
        "trace": success_bundle["trace"],
        "observation": success_bundle["observation"],
        "output": success_bundle["output"],
        "rag_followup": success_bundle["rag_followup"],
    }


def _sanitize_tool_plan_item_payload_dict(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = _sanitize_tool_runtime_trace_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_payload_list(
    payload: list[dict[str, object]],
) -> list[dict[str, object]]:
    sanitized = _sanitize_tool_runtime_trace_artifact_payload(payload)
    assert isinstance(sanitized, list)
    return sanitized


def build_tool_plan_item_success_effects(
    *,
    action_step: dict[str, object],
    postprocess: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": postprocess["trace"],
        "observation": postprocess["observation"],
        "output": postprocess["output"],
        "rag_followup": postprocess["rag_followup"],
    }


def build_tool_plan_item_terminal_effects(
    *,
    action_step: dict[str, object],
    terminal_failure: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": terminal_failure["trace"],
        "status": terminal_failure["status"],
        "error_message": terminal_failure["error_message"],
        "audit_detail": terminal_failure["audit_detail"],
        "state": terminal_failure["state"],
    }


def build_tool_plan_item_stream_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    success_effects = loop_execution_result["success_effects"]
    terminal_effects = loop_execution_result["terminal_effects"]

    if success_effects is not None:
        trace_step = success_effects["trace_step"]
        trace_steps = [
            _sanitize_tool_trace_event_step(trace_step)
            if isinstance(trace_step, dict)
            else trace_step
        ]
        trace_events = [
            _sanitize_tool_trace_event_payload(loop_execution_result["trace_event"])
        ]
        rag_followup = success_effects["rag_followup"]
        if rag_followup is not None:
            trace_steps.append(rag_followup["step"])
            trace_events.append(_sanitize_tool_trace_event_payload(rag_followup["trace"]))
        return _sanitize_tool_plan_item_payload_dict(
            {
                "trace_steps": trace_steps,
                "trace_events": trace_events,
                "observation": success_effects["observation"],
                "tool_observations": [success_effects["observation"]],
                "terminal_effects": None,
                "seq_increment": 1 if rag_followup is not None else 0,
                "should_return": False,
            }
        )

    assert terminal_effects is not None
    terminal_trace_step = terminal_effects["trace_step"]
    terminal_trace = terminal_effects["trace"]
    sanitized_terminal_effects = dict(terminal_effects)
    if isinstance(terminal_trace_step, dict):
        sanitized_terminal_effects["trace_step"] = _sanitize_tool_trace_event_step(
            terminal_trace_step
        )
    sanitized_terminal_effects["trace"] = _sanitize_tool_trace_event_payload(
        terminal_trace
    )
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_steps": [sanitized_terminal_effects["trace_step"]],
            "trace_events": [sanitized_terminal_effects["trace"]],
            "observation": None,
            "tool_observations": [],
            "terminal_effects": sanitized_terminal_effects,
            "seq_increment": 0,
            "should_return": bool(loop_execution_result["should_return"]),
        }
    )


def build_tool_plan_item_terminal_return_effects(
    *,
    terminal_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "task_status": terminal_effects["status"],
            "state_event": terminal_effects["state"],
            "failure_event": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": terminal_effects["error_message"],
                "detail": terminal_effects["audit_detail"],
            },
        }
    )


def build_tool_plan_item_continue_update(
    *,
    stream_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(stream_effects["tool_observations"]),
            "seq_increment": int(stream_effects["seq_increment"]),
        }
    )


def build_tool_plan_item_continue_action(
    *,
    continue_update: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(continue_update["tool_observations"]),
            "seq_increment": int(continue_update["seq_increment"]),
        }
    )


def build_tool_plan_item_next_action(
    *,
    continue_update: dict[str, object],
    terminal_return_effects: dict[str, object] | None,
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "return" if terminal_return_effects is not None else "continue",
            "continue_update": continue_update,
            "terminal_return_effects": terminal_return_effects,
        }
    )


def build_tool_plan_item_return_action(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    terminal_return_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "complete_task_kwargs": {
                "task_id": task_id,
                "trace_steps": trace_steps,
                "user_id": user_id,
                "status": str(terminal_return_effects["task_status"]),
            },
            "failure_event_kwargs": terminal_return_effects["failure_event"],
            "state_event": terminal_return_effects["state_event"],
        }
    )


def build_tool_plan_item_trace_write_action(
    *,
    trace_write: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_step": trace_write["step"],
            "trace_event": trace_write["event"],
            "persist_force": bool(trace_write["force_persist"]),
        }
    )


def build_tool_plan_item_next_action_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    next_action: dict[str, object],
) -> dict[str, object]:
    continue_action = build_tool_plan_item_continue_action(
        continue_update=next_action["continue_update"],
    )
    if str(next_action["kind"]) == "return":
        terminal_return_effects = next_action["terminal_return_effects"]
        assert terminal_return_effects is not None
        return _sanitize_tool_plan_item_payload_dict(
            {
                "kind": "return",
                "continue_update": next_action["continue_update"],
                "continue_action": continue_action,
                "return_action": build_tool_plan_item_return_action(
                    task_id=task_id,
                    trace_steps=trace_steps,
                    user_id=user_id,
                    terminal_return_effects=terminal_return_effects,
                ),
            }
        )
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "continue_update": next_action["continue_update"],
            "continue_action": continue_action,
            "return_action": None,
        }
    )


def build_tool_plan_item_service_actions(
    *,
    service_execution: dict[str, object],
) -> list[dict[str, object]]:
    actions = [
        build_tool_plan_item_trace_write_service_action(
            trace_write_action=trace_write_action,
        )
        for trace_write_action in service_execution["trace_write_actions"]
    ]
    next_action_execution = service_execution["next_action_execution"]
    if str(next_action_execution["kind"]) == "return":
        return_action = next_action_execution["return_action"]
        assert return_action is not None
        return _sanitize_tool_plan_item_payload_list(
            [
                *actions,
                *build_tool_plan_item_return_service_actions(
                    return_action=return_action,
                ),
            ]
        )

    continue_action = next_action_execution["continue_action"]
    return _sanitize_tool_plan_item_payload_list(
        [
            *actions,
            build_tool_plan_item_continue_service_action(
                continue_action=continue_action,
            ),
        ]
    )


def build_tool_plan_item_trace_write_service_action(
    *,
    trace_write_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "trace_write",
            "trace_step": trace_write_action["trace_step"],
            "trace_event": trace_write_action["trace_event"],
            "persist_force": bool(trace_write_action["persist_force"]),
        }
    )


def build_tool_plan_item_continue_service_action(
    *,
    continue_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "tool_observations": list(continue_action["tool_observations"]),
            "seq_increment": int(continue_action["seq_increment"]),
        }
    )


def build_tool_plan_item_return_service_actions(
    *,
    return_action: dict[str, object],
) -> list[dict[str, object]]:
    return _sanitize_tool_plan_item_payload_list(
        [
            {
                "kind": "complete_task",
                "kwargs": return_action["complete_task_kwargs"],
            },
            {
                "kind": "record_failure_event",
                "kwargs": return_action["failure_event_kwargs"],
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": return_action["state_event"],
            },
            {
                "kind": "return",
            },
        ]
    )


def build_tool_plan_item_service_effects_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    service_effects: dict[str, object],
) -> dict[str, object]:
    service_execution = {
        "trace_write_actions": list(service_effects["trace_write_actions"]),
        "next_action_execution": build_tool_plan_item_next_action_execution(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            next_action=service_effects["next_action"],
        ),
    }
    service_execution["service_actions"] = build_tool_plan_item_service_actions(
        service_execution=service_execution,
    )
    sanitized_service_execution = _sanitize_tool_runtime_trace_artifact_payload(
        service_execution
    )
    assert isinstance(sanitized_service_execution, dict)
    return sanitized_service_execution


def build_tool_plan_item_service_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    service_effects = build_tool_plan_item_service_effects(
        loop_execution_result=loop_execution_result,
    )
    return build_tool_plan_item_service_effects_execution(
        task_id=task_id,
        trace_steps=trace_steps,
        user_id=user_id,
        service_effects=service_effects,
    )


def build_tool_plan_item_service_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    stream_effects = build_tool_plan_item_stream_effects(
        loop_execution_result=loop_execution_result,
    )
    continue_update = build_tool_plan_item_continue_update(
        stream_effects=stream_effects,
    )
    terminal_effects = stream_effects["terminal_effects"]
    terminal_return_effects = (
        build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )
        if terminal_effects is not None
        else None
    )
    should_return = bool(stream_effects["should_return"])
    next_action = build_tool_plan_item_next_action(
        continue_update=continue_update,
        terminal_return_effects=terminal_return_effects,
    )
    trace_writes = [
        {
            "step": trace_step,
            "event": trace_event,
            "force_persist": should_return,
        }
        for trace_step, trace_event in zip(
            stream_effects["trace_steps"],
            stream_effects["trace_events"],
        )
    ]
    trace_write_actions = [
        build_tool_plan_item_trace_write_action(trace_write=trace_write)
        for trace_write in trace_writes
    ]
    service_effects = {
        "trace_steps": stream_effects["trace_steps"],
        "trace_events": stream_effects["trace_events"],
        "trace_writes": trace_writes,
        "trace_write_actions": trace_write_actions,
        "continue_update": continue_update,
        "next_action": next_action,
        "tool_observations": continue_update["tool_observations"],
        "seq_increment": continue_update["seq_increment"],
        "should_return": should_return,
        "terminal_return_effects": terminal_return_effects,
    }
    sanitized_service_effects = _sanitize_tool_runtime_trace_artifact_payload(
        service_effects
    )
    assert isinstance(sanitized_service_effects, dict)
    return sanitized_service_effects

_EXECUTION_FLOW_EXPORTS = (
    'build_tool_trace_event',
    '_sanitize_tool_trace_event_step',
    '_sanitize_tool_trace_event_payload',
    'build_tool_terminal_failure_transition',
    '_sanitize_tool_terminal_failure_payload',
    '_sanitize_tool_plan_item_result_payload',
    '_sanitize_tool_plan_success_bundle_payload',
    '_sanitize_tool_plan_success_bundle_rag_followup_payload',
    'build_tool_rag_step',
    '_build_tool_rag_followup_content',
    '_TOOL_RAG_DOCUMENT_TEXT_FIELDS',
    '_TOOL_RAG_DOCUMENT_CONTAINER_FIELDS',
    '_TOOL_RAG_DOCUMENT_LIST_FIELDS',
    '_TOOL_RAG_DOCUMENT_VERSION_RE',
    '_TOOL_RAG_CONTENT_HASH_RE',
    '_TOOL_RAG_SENSITIVE_ASSIGNMENT_RE',
    '_redact_tool_rag_chunk_text',
    '_sanitize_tool_rag_metadata_text',
    '_sanitize_tool_rag_document_version',
    '_sanitize_tool_rag_content_hash',
    '_coerce_tool_rag_metadata_mapping',
    '_build_tool_rag_chunk_metadata',
    '_extract_tool_rag_chunk_from_document_mapping',
    '_extract_tool_rag_chunks_from_document_list',
    '_extract_tool_rag_chunks_from_output',
    '_extract_tool_rag_chunk_metadata_from_document_list',
    '_extract_tool_rag_chunk_metadata_from_output',
    '_build_tool_rag_document_versions',
    'build_tool_prompt_with_observations',
    'build_tool_attempt_result',
    '_sanitize_tool_attempt_error_result_payload',
    'build_tool_attempt_outcome',
    'build_tool_iteration_context',
    'build_tool_iteration_success_artifacts',
    'build_tool_rag_followup',
    'build_tool_iteration_execution',
    'build_tool_plan_item_success_bundle',
    'build_tool_plan_item_result',
    'build_tool_plan_item_execution_result',
    'build_tool_plan_item_execution',
    'build_tool_plan_item_postprocess',
    '_sanitize_tool_plan_item_payload_dict',
    '_sanitize_tool_plan_item_payload_list',
    'build_tool_plan_item_success_effects',
    'build_tool_plan_item_terminal_effects',
    'build_tool_plan_item_stream_effects',
    'build_tool_plan_item_terminal_return_effects',
    'build_tool_plan_item_continue_update',
    'build_tool_plan_item_continue_action',
    'build_tool_plan_item_next_action',
    'build_tool_plan_item_return_action',
    'build_tool_plan_item_trace_write_action',
    'build_tool_plan_item_next_action_execution',
    'build_tool_plan_item_service_actions',
    'build_tool_plan_item_trace_write_service_action',
    'build_tool_plan_item_continue_service_action',
    'build_tool_plan_item_return_service_actions',
    'build_tool_plan_item_service_effects_execution',
    'build_tool_plan_item_service_execution',
    'build_tool_plan_item_service_effects',
)
