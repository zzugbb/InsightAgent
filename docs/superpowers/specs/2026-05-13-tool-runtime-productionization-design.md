# Tool Runtime Productionization Design

**Date:** 2026-05-13
**Scope:** InsightAgent backend service layer
**Status:** Draft approved in chat, written for final review

## Goal

Extract the current mock tool planning and execution logic out of
`backend/app/services/chat_execution_service.py` into a dedicated backend
runtime module, while keeping all external behavior unchanged.

## Non-Goals

- No SSE event contract changes
- No REST API contract changes
- No trace schema changes
- No provider behavior changes
- No new real tools in this slice
- No queueing or concurrency changes in this slice

## Success Criteria

- `tool_start`, `tool_end`, `error`, `trace`, `state`, `done` event payloads remain unchanged
- Existing task execution behavior for `mock_plan`, `mock_retrieve`, and `calc_eval` remains unchanged
- Existing retry semantics for `[mock-tool-error]` and fatal semantics for `[mock-tool-fatal]` remain unchanged
- Existing e2e assertions do not need to change because of this refactor
- Tool logic is no longer embedded directly inside `chat_execution_service.py`

## Current Problem

`backend/app/services/chat_execution_service.py` currently owns too many
responsibilities at once:

- task lifecycle orchestration
- SSE event emission
- trace step persistence
- timeout and cancel handling
- tool plan construction
- tool execution details
- tool-specific output shaping

This makes the service harder to evolve into a real tool runtime. The smallest
safe step is to isolate tool-specific logic without touching orchestration.

## Chosen Approach

Use a lightweight dedicated runtime module while keeping
`chat_execution_service.py` as the orchestration layer.

This is intentionally narrower than introducing a full registry framework.
It gives us clean internal boundaries now, while preserving today’s behavior
and minimizing refactor risk.

## Architecture

### 1. Keep orchestration in `chat_execution_service.py`

`chat_execution_service.py` will continue to own:

- task status transitions
- user message persistence
- trace step sequencing and persistence
- SSE event emission
- timeout and cancellation checks
- provider invocation for final answer generation
- final task completion / failure handling

### 2. Extract tool runtime logic into a dedicated module

Create a new backend service module responsible for:

- building a tool plan from the prompt
- executing a single tool spec
- encapsulating tool-specific errors
- returning stable tool outputs in the same shape used today

### 3. Preserve current tool set exactly

The extracted runtime will support the current tool names only:

- `mock_plan`
- `mock_retrieve`
- `calc_eval`

The new module is a structural seam for future work, not a behavior expansion.

## File Changes

### New file

- `backend/app/services/tool_runtime.py`

Responsibilities:

- define the tool execution error type
- expose `build_tool_plan(prompt: str) -> list[dict[str, object]]`
- expose a single tool execution entrypoint
- hold current helper logic used only by tool execution

### Modified file

- `backend/app/services/chat_execution_service.py`

Changes:

- remove embedded tool plan construction helpers
- remove embedded tool execution helpers
- import the extracted runtime helpers
- keep all existing orchestration, SSE, trace, retry, and completion behavior

## Behavioral Compatibility Requirements

The following must remain byte-for-byte compatible where practical, and
semantically compatible everywhere:

- tool names in plan output
- tool input structures
- tool output structures
- retry count propagation
- `meta.tool` content in trace steps
- `tool_start` and `tool_end` payload fields
- `tool_execution_error` code and fatal/retryable behavior

## Testing Strategy

This slice should use test-first validation around the new seam.

### Required coverage

1. Tool plan compatibility
   - prompts that trigger `mock_plan` only
   - prompts that trigger `mock_retrieve`
   - prompts that trigger `calc_eval`

2. Tool execution compatibility
   - `mock_plan` output shape
   - `calc_eval` output shape
   - `mock_retrieve` success path shape

3. Error compatibility
   - `[mock-tool-error]` first-attempt transient error
   - `[mock-tool-fatal]` fatal error
   - unknown tool fatal error

### Verification level for this slice

- add a focused backend test that exercises the extracted runtime directly
- keep existing e2e/common regression checks green after refactor

## Risks

### Risk: accidental contract drift

If output dictionaries, retry counts, or error wording drift, existing front-end
or e2e assertions may break.

Mitigation:

- copy current behavior exactly first
- add focused compatibility tests before moving code

### Risk: refactor grows into framework work

It would be easy to introduce registry/context abstractions too early.

Mitigation:

- keep this slice to a single runtime module only
- defer registry/generalized framework work to a later P0/P1 slice

## Rollout Plan

1. Add failing compatibility tests for extracted runtime behavior
2. Create `tool_runtime.py` with copied logic
3. Rewire `chat_execution_service.py` to call the new runtime helpers
4. Run focused tests
5. Run existing regression checks that protect current e2e/service behavior

## Follow-Up After This Slice

After this refactor is stable, the next logical slices are:

1. Introduce a minimal tool registry while preserving behavior
2. Convert `calc_eval` into the first explicitly registered runtime tool
3. Add runtime context boundaries for future real tools
