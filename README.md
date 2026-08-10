# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- 阶段 5 基础产品化已完成：会话/任务/消息持久化、SSE、Trace、Memory、RAG、鉴权、PostgreSQL、任务取消/超时、running task 恢复、usage dashboard、审计与任务/会话导出已具备可演示闭环。
- `real-tool-execution`、`queue-and-concurrency-lite` 与 `concurrency-fairness-policy` 均已封板；当前主线进入 `registry-governance`，进度约 `11%`。
- 当前队列基线：任务默认 `queued`，拿到进程内执行槽位后切 `running`；全局并发默认 `TASK_QUEUE_MAX_CONCURRENT=32`，可选 per-user/per-session 限额默认 `0` 关闭；等待队列保持 capacity-aware oldest eligible FIFO，queued cancel 会移出等待队列。
- `GET /api/settings` 暴露只读 `task_queue_diagnostics`，覆盖全局、当前用户与可选当前会话 active/waiting/available 计数、限额触顶、`pressure_state`、fairness 开关、等待策略与 poll interval；前后端 typed contract 已固定 required governance 字段、optional scope 字段和枚举值。
- `backend/scripts/test_tool_runtime_slice.py` 已拆到 `backend/scripts/tool_runtime_slice/`；`tool_runtime.py` 已拆出 planner、execution、HTTP JSON、registry 四个 facade 模块，外部 import 保持稳定；registry diagnostics summary、runtime/preflight 回灌和 provider source 安全摘要已开始收紧。
- 默认运行策略保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。

## 当前验证基线

- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`：`1785/1785` 通过
- `bash scripts/test_ci_e2e_tooling.sh all`：最近一次通过
- backend e2e main phase：baseline / main / export consistency / cancel-timeout 通过
- frontend type contract：`npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts` 通过
- backend queue e2e phase：低并发 `8011` latest fresh 通过，覆盖 queued cancel、safe queue snapshot、settings diagnostics 与 followup completion
- frontend targeted Chromium：queued recover/cancel、running cancel、Task Center session/global 隔离、刷新恢复隔离均已通过
- 完整 Chromium e2e：默认 `8000/3001` latest fresh 通过，`50 passed / 1 skipped`
- 本轮相关 `8011/8000/3001` 服务均已停止，`lsof` 无监听残留。
- `git diff --check`：通过
- 普通沙箱访问本机 Docker/端口会被权限拦截时，按流程提权后重跑，不拿旧结果冒充新结果。
- 测试/e2e/启动/提交的权限与依赖路径已固化到 `docs/development-runbook.md`；后续优先按 runbook 直接使用正确 venv、端口提权和 git 提权流程。

## 当前开发计划

1. 已封板主线：`real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`。
2. 当前主线：`registry-governance`，聚焦 selected source、settings/preflight、tool details、per-tool diagnostics、runtime semantic、trace/search/export 的治理语义；当前已收口 diagnostics summary 脱敏后去重、runtime/preflight 回灌 totals 派生/安全规整与 provider source 名称脱敏。
3. 本主线继续保持外部 SSE / trace / export / e2e 契约稳定，按“小红测 -> 实现 -> targeted/full slice”推进。
4. 后续候选：`rag-governance-hardening`，聚焦知识库版本化、来源治理与更细粒度 shared 规则。

## 关键能力边界

- 外部 SSE / trace / export / e2e 契约保持稳定，优先做内部 runtime/helper/display 收口。
- 新增 provider/source 协议继续按 `real-tool-execution` 已完成验收基线补小红测，不再作为当前主线阻塞项。
- `data/insightagent.plan.back.md` 是只读备份计划，不参与活跃开发同步。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard 与主链路 e2e / CI tooling 已落地。
- 当前未完成的重点不是这些基线能力，而是 registry 治理深化与后续 RAG 治理硬化。

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
