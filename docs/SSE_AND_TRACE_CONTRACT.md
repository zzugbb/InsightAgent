# SSE 任务流与 TraceStep 契约说明

本文说明 **`GET /api/tasks/{task_id}/stream`**（`text/event-stream`）与 **`GET /api/tasks/{task_id}/trace`**（JSON）在 **轨迹步骤** 上的对齐关系，便于联调与代码生成。实现以 `backend/app/services/chat_execution_service.py`、`app/schemas/trace.py` 及前端 `lib/types/trace.ts`、`lib/stores/chat-stream-store.ts` 为准。

---

## 1. 总览

| 通道 | 内容 | Trace 形态 |
|------|------|------------|
| **REST** `GET .../trace` | 响应体 `steps: TraceStep[]` | 落库后的完整步骤列表，经 `parse_trace_steps` 校验 |
| **REST** `GET .../trace/delta?after_seq=` | 增量 `steps` + `next_cursor` | 同上，按 `seq` 过滤 |
| **SSE** `event: trace` | `data` 内嵌单步 `step` | **与 `TraceStep` 同构**（`id` / `type` / `content` / `meta` / 可选 `seq`） |

**结论**：`trace` 事件里 **`step` 对象**与 OpenAPI 中的 **`TraceStep`**（及前端 **`TraceStepPayload`**）一致；扩展字段可走 `meta`（`TraceStepMeta.extra="allow"`）。

---

## 2. SSE 事件类型（当前实现）

以下为 **`chat_execution_service.stream_task_execution`** 实际发出的 `event` 名及 `data` JSON 字段（UTF-8，`data:` 行为 JSON 字符串）。

### `start`

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID |
| `task_id` | string | 任务 ID |
| `provider` | string | Provider 名（Mock 等） |
| `model` | string | 模型标识 |

### `state`

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `phase` | string | 如 `thinking`、`streaming`、`error` |

### `trace`（核心）

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `step_id` | string | 与 `step.id` 一致，便于前端关联 |
| `step` | **object** | **TraceStep 形状**：`id`、`type`、`content`、`meta?`、`seq?` |

**流式注意**：最终 `observation` 步在首次 `trace` 时可能 **`content` 为空字符串**，正文由后续 **`token`** 事件的 `delta` 拼接得到；落库 `trace_json` 为**完整正文**（见下节）。

### `heartbeat`

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `ts` | string | ISO 时间戳 |

### `token`

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `step_id` | string | 通常为最终 observation 步 ID |
| `delta` | string | 输出增量 |

### `done`

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | |
| `task_id` | string | |
| `step_id` | string | 常与最终步一致 |
| `status` | string | 如 `completed` |
| `usage` | object | `prompt_tokens` / `completion_tokens` / `cost_estimate` 等，可为 `null` |

### `error`

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | |
| `step_id` | string | |
| `message` | string | 错误信息 |
| `retryable` | boolean | 是否可重试（当前多为 `false`） |

---

## 3. 与 REST trace 的差异与一致点

1. **顺序**：SSE 按时间顺序多次发送 `trace`；REST 一次返回数组，顺序与落库一致。  
2. **最终步正文**：SSE 中 observation 先空后由 `token` 拼出；REST 中为**完整 `content`**。  
3. **`seq`**：持久化时由 `_normalize_trace_steps` 等补齐；SSE 若未带 `seq`，前端可用索引推导游标（见 `chat-stream-store`）。  
4. **校验**：REST 响应经 Pydantic `TraceStep`；SSE 客户端应按同一形状解析 `step`，避免字段漂移。

---

## 4. 相关文件

| 位置 | 作用 |
|------|------|
| `backend/app/schemas/trace.py` | `TraceStep` / `TraceStepMeta` |
| `frontend/lib/types/trace.ts` | `TraceStepPayload` / `TraceStepMeta` |
| `backend/app/services/chat_execution_service.py` | SSE 事件构造 |
| `frontend/lib/stores/chat-stream-store.ts` | `dispatchSseEvent` 消费逻辑 |

---

## 5. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-04-09 | 初版：事件表与 REST 对齐说明 |
