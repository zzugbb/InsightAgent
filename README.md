# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- 阶段 5 基础产品化已完成：会话/任务/消息持久化、SSE、Trace、Memory、RAG、鉴权、PostgreSQL、任务恢复、导出、usage dashboard 与审计具备可演示闭环。
- 已封板主线：从 `real-tool-execution` 到 `provider-tool-expansion` 的九条主线均已封板。
- 当前封板结论：`provider-tool-expansion` 100% 完成；HTTP JSON provider search 总量/命中归一化、provider planner 多协议工具调用解析、JSON 字符串参数解析与 reconnect 稳定错误码复原均已收口。
- 稳定契约：默认 remote/mock 判定、queued/running/cancel 语义、SSE / trace / export / display shape 保持不变。
- 结构治理：backend slice 已按主题拆分，`tool_runtime.py` 保留 facade，planner/execution/HTTP JSON/registry 已拆模块。
- 后续候选主线：`ci-release-engineering`。

## 当前验证基线

- Backend：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，`1983/1983` 通过。
- Provider-tool targeted：`provider_search 15/15`、`http_json 531/531`、`tool_plan_provider 57/57`、`failed_task_error_event_hint 1/1` 通过。
- Frontend：node tests `121/121`，`npm run lint` 通过，`npm run build` 通过。
- E2E：backend main phase 通过；frontend full Chromium `52 passed / 1 skipped`。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check`、备份计划 diff 检查通过；端口 8000/3001 无残留监听。

## 当前开发计划

1. 当前主线：`provider-tool-expansion` 已 100% 封板；四份活跃文档已收敛到当前状态、验证基线、候选主线与稳定契约。
2. 已封板主线：从 `real-tool-execution` 到 `provider-tool-expansion` 的九条主线均已封板。
3. 后续候选主线：`ci-release-engineering`。
4. 继续保持外部 SSE / trace / export / e2e 契约稳定，按“小红测 -> 实现 -> targeted/full slice”推进。

## 后续候选主线

- `ci-release-engineering`：把当前手工封板验证基线进一步沉淀为分层 CI、e2e 编排和发布前检查。

## 关键能力边界

- 外部 SSE / trace / export / e2e 契约保持稳定，优先做内部 runtime/helper/display 收口。
- 新增 provider/source 协议继续按 `real-tool-execution` 已完成验收基线补小红测，不再作为封板主线阻塞项。
- 单文件规模纳入治理：新增测试/实现优先使用主题文件；主题文件明显膨胀时先拆分到新文件/新模块，沿用既有 slice 主题包与 facade 拆分方式。
- `data/insightagent.plan.back.md` 是只读备份计划，不参与活跃开发同步。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard、生产可靠性治理与主链路 e2e / CI tooling 已落地。
- `observability-experience` 已封板，失败诊断、任务回放、Trace 与 Task Center 的可读性和定位效率进入维护态。

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

- 活跃进度只保留“当前状态、封板主线、最近校验基线、下一步候选”这类高信号内容。
- 长串历史流水账、阶段内小切片和重复能力摘要不再继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
