# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- W1-W4 已完成并收口：会话/任务/消息持久化、SSE 流、Trace 回放与增量同步、Memory、RAG、Token/Cost 展示、基础前后端工作台闭环已可用。
- 当前主线已切到默认工具去 mock 化、真实工具接入，以及 `tool registry / profile / provider source` 治理产品化。
- `tool-runtime-productionization` 已归档，不再把那两份 runtime spec 当作活跃文档维护；当前以代码、三份 README 和本计划文件为准。
- 默认运行策略仍是：配置完整真实 provider/model/api_key 时自动走 `remote`，否则回退 canonical `mock`。
- 最近代码主线已经打通：
  - planner 已能规划 real/extra tools、动态 registry/source 候选，并优先使用 configured registry 语义。
  - provider / provider source 已支持 `loader_factory`；file-backed diagnostics、selected source 与 settings/preflight/artifacts 已对齐到同一治理主干。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 已贯通 action step、`tool_start/tool_end`、持久化 trace、export 与 mock final answer。
  - retrieval / observation / helper fallback 已不再把 provider/real tool 误解释为默认本地知识库语义，name-only 路径也会优先复用已落盘的 registry 语义；即使原始 `output` 缺失，observation、success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 聚合也会优先复用 step meta 或 typed payload 中已落下的结构化结果；会话 Memory query、RAG ingest/query、RAG route 层与 shared knowledge-base merge 的 metadata、query payload root、document row、row list，以及 session create/detail/list/messages/export、task/session usage、task create/detail/list/cancel/trace/delta/export/stream-reconnect、auth register/refresh/session list/user list、audit log list 这批 outward summary route，以及 `chat_persistence_service` 的 task trace/usage/response/export/delta 与 `task_rows_*` 批量聚合 helper，也不再因 typed service payload / `model_dump()` payload 而退化成空结构或直接报错，nested metadata 也能继续保留。
  - runtime helper、governance/export、registry diagnostics 与 planner payload 归一化已收口对旁路结构化载荷的兼容；当前 provider planner 与真实 remote provider 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`814/814`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`39/39`）
  - `cd frontend && npm run lint` 通过
  - `bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `git diff --check` 通过

## 当前主线

1. 默认工具去 mock 化：优先补“已经能被规划，但执行本体、结果预览、trace/observation/export 仍残留默认 stub 语义”的缺口。
2. 真实工具接入：优先推进 extra/real tools 的执行本体产品化，而不是只停留在 planner payload 兼容。
3. registry / profile / provider source 治理：保持 loader、provider、source、diagnostics、selected source 与 settings summary 一套语义。
4. 契约稳定：外部 SSE / trace / export / e2e 契约尽量不乱改，优先做内部 helper、runtime 与 display 语义收口。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard 与主链路 e2e / CI tooling 已落地。
- 当前未完成的重点不是这些基线能力，而是默认工具去 mock 化后的真实执行语义、registry 治理深化与单机并发治理。

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
- `cancelled`
- `timeout`
- `done`
- `error`

对齐规则：

- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中可先为空或阶段性刷新，REST 中返回完整内容。
- 前端实时流、历史 trace 与导出回放都按同一 `TraceStep` 结构消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 知识库级 collection：`kb_{user_hash}_{knowledge_base_id}`（用户隔离）
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

### 通俗理解：为什么有 RAG 还需要 Memory

- `PostgreSQL`：完整账本，保存会话、消息、任务、trace、usage。
- `Chroma Memory`：当前会话便签本，保存可语义召回的会话记忆片段。
- `Chroma RAG`：长期知识库，保存导入文档的分块内容。

三者分工不同：

- `RAG` 解决“系统知道哪些外部资料”。
- `Memory` 解决“当前会话刚刚确认了什么偏好和约束”。
- `PostgreSQL` 解决“完整历史如何留档和回放”。

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

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

如需一键启动（会自动拉起 `postgres/chroma`，再启动 backend/frontend），可执行：

```bash
./start_insightagent.command
```

## 文档维护约定

- 活跃进度只保留“当前状态、当前主线、最近校验基线、下一步候选”这类高信号内容。
- 长串历史流水账、阶段内小切片和重复能力摘要不再继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
