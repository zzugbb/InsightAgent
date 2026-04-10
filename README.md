# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 → 任务执行 → 轨迹解释 → Memory/RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前开发进度（按完整计划对齐）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| W1 主链路 | 已完成 | 会话/任务/消息持久化、SSE 流、trace 回放与 delta、前端工作台闭环 |
| W2 可观测 + Memory 最小闭环 | 已完成（进入收尾） | 轨迹时间线+流程图、TraceStep 契约、Chroma 会话 memory 状态/写入/检索 |
| W3 Tool + ReAct | 未开始 | 真实工具调用循环（非 mock） |
| W4 RAG + 成本展示 | 未开始 | 真实 RAG ingest/检索、token/cost UI 细化 |
| 阶段 5+ 产品化 | 未开始 | PG、多用户鉴权、治理、测试与运维 |

当前默认策略：`mock` 模式优先，先稳定主链路契约与可视化，再切真实 API。

## 当前能力摘要

- backend：
  - `POST /api/tasks`、`GET /api/tasks/{task_id}/stream`、`GET /api/tasks/{task_id}/trace`、`GET /api/tasks/{task_id}/trace/delta`
  - `GET /api/tasks` 支持 `limit/offset` 与可选 `session_id` 过滤，响应含 `total/has_more`
  - 会话接口支持创建/列表/详情/消息/重命名/删除
  - Memory：`GET .../memory/status`、`POST .../memory/add`、`POST .../memory/query`
  - `/health` 含 Chroma 可达性
- frontend：
  - 三栏工作台（会话 / 消息 / 轨迹与上下文）
  - 轨迹支持「时间线 / 流程图」双视图（thought/action/observation/tool/rag 区分）
  - 会话支持分页加载、重命名、删除
  - Context 面板支持 Memory 状态展示、add/query 调试

## SSE 与 TraceStep 契约（当前实现）

`GET /api/tasks/{task_id}/stream` 的 `event: trace` 中 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。

当前 SSE 事件类型：
- `start`
- `state`
- `trace`
- `heartbeat`
- `token`
- `done`
- `error`

对齐规则：
- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
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
- 真实 RAG ingest/检索（W4）
- `trace/delta` 流式期间更细粒度增量持久化
- usage / token / cost 展示完善
