# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 → 任务执行 → 轨迹解释 → Memory/RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前开发进度（按完整计划对齐）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| W1 主链路 | 已完成 | 会话/任务/消息持久化、SSE 流、trace 回放与 delta、前端工作台闭环 |
| W2 可观测 + Memory 最小闭环 | 已完成（进入收尾） | 轨迹时间线+流程图、TraceStep 契约、Chroma 会话 memory 状态/写入/检索、`trace/delta` 流式阶段增量持久化（`seq` 递增） |
| W3 Tool + ReAct | 未开始 | 真实工具调用循环（非 mock） |
| W4 RAG + 成本展示 | 未开始 | 真实 RAG ingest/检索、token/cost UI 细化 |
| 阶段 5+ 产品化 | 未开始 | PG、多用户鉴权、治理、测试与运维 |

当前默认策略：`mock` 模式优先，先稳定主链路契约与可视化，再切真实 API。

## 当前能力摘要

- backend：
  - `POST /api/tasks`、`GET /api/tasks/{task_id}/stream`、`GET /api/tasks/{task_id}/trace`、`GET /api/tasks/{task_id}/trace/delta`
  - `trace/delta` 支持 `limit` 参数控制单次增量返回量（默认 200，最大 500）
  - 流式阶段会按批次持久化最终 `observation`（默认每 8 个 token chunk 一次，并在结束时兜底），`trace/delta?after_seq=` 可持续拉取增量
  - `GET /api/tasks` 支持 `limit/offset` 与可选 `session_id` 过滤，响应含 `total/has_more`
  - `GET /api/tasks/usage/summary` 支持全局与按 `session_id` 的 usage 聚合
  - 会话接口支持创建/列表/详情/消息/重命名/删除
  - `GET /api/sessions/{session_id}/usage/summary` 兼容保留（会话聚合）
  - Memory：`GET .../memory/status`、`POST .../memory/add`、`POST .../memory/query`
  - `/health` 含 Chroma 可达性
- frontend：
  - 三栏工作台（会话 / 消息 / 轨迹与上下文）
  - 轨迹支持「时间线 / 流程图」双视图（thought/action/observation/tool/rag 区分）
  - 会话支持分页加载、重命名、删除
  - Context 面板支持 Memory 状态展示、add/query 调试
  - usage 展示增强：支持全局/会话自动切换汇总，含加载/错误/空状态与覆盖率（with_usage/total）
  - `trace/delta` 支持流式期间自动轮询同步（静默）+ 失败退避重试，并在流结束后自动补拉一次
  - Inspector 上下文摘要新增 delta 同步健康度（状态/重试次数/最近成功时间/下次重试/最近错误/恢复提示），恢复提示为短时展示并自动消退；重试中展示秒级倒计时
  - 页面处于后台（不可见）时暂停 delta 自动同步，回到前台自动恢复
  - Inspector 在 delta 连续失败时提供轻量告警提示（不阻塞主链路）
  - 前端 ESLint 基线已落地，`npm run lint` 可直接执行且当前告警已清零

## SSE 与 TraceStep 契约（当前实现）

`GET /api/tasks/{task_id}/stream` 的 `event: trace` 中 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。

当前 SSE 事件类型：
- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `done`
- `error`

对齐规则：
- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 作为工具生命周期事件，与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中先空内容，再由 `token.delta` 拼接；REST 中是完整内容。
- REST 返回步骤由后端 `TraceStep`（Pydantic）校验，前端按 `lib/types/trace.ts` 对齐消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 嵌入策略：当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- 错误语义：
  - Chroma 不可达时，`memory/add` 与 `memory/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
└── data/
```

## Docker（可选，Chroma）

在仓库根目录启动：

```bash
docker compose up -d chroma
```

默认后端连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

## W2 收尾与下一步

- 真实工具调用与错误/重试语义（W3）
- W3 首版已打通 `tool_start/tool_end` 事件链路（mock 语义）
- 真实 RAG ingest/检索（W4）
- `trace/delta` 已完成首版流式增量持久化，后续可继续调优批次频率与写入策略
- 前端已接入流式阶段自动 `trace/delta` 同步与失败退避重试；后续可继续调优轮询参数
- usage / token / cost 展示继续完善（如跨会话历史趋势）
