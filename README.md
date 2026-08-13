# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- 阶段 5 基础产品化已完成：会话/任务/消息持久化、SSE、Trace、Memory、RAG、鉴权、PostgreSQL、任务取消/超时、running task 恢复、usage dashboard、审计与任务/会话导出已具备可演示闭环。
- `real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance` 与 `rag-governance-hardening` 均已封板；当前主线为 `production-reliability-hardening`，进度约 `68%`。
- 当前队列基线：任务默认 `queued`，拿到进程内执行槽位后切 `running`；全局并发默认 `TASK_QUEUE_MAX_CONCURRENT=32`，可选 per-user/per-session 限额默认 `0` 关闭；等待队列保持 capacity-aware oldest eligible FIFO，queued cancel 会移出等待队列。
- `GET /api/settings` 暴露只读 `task_queue_diagnostics`，覆盖全局、当前用户与可选当前会话 active/waiting/available 计数、限额触顶、`pressure_state`、fairness 开关、等待策略与 poll interval；前后端 typed contract 已固定 required governance 字段、optional scope 字段和枚举值。
- `backend/scripts/test_tool_runtime_slice.py` 已拆到 `backend/scripts/tool_runtime_slice/`；`tool_runtime.py` 已拆出 planner、execution、HTTP JSON、registry 四个 facade 模块，外部 import 保持稳定。
- `registry-governance` 已封板：provider/source 脱敏、冲突 alias、跨 settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口。
- `rag-governance-hardening` 已封板：RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口均已完成治理收口，外部 SSE / trace / export / e2e shape 保持稳定。
- `production-reliability-hardening` 已完成首批后端收口：按 user/session scope 清理 waiting queue、删除会话后清理残留 queued waiting entries、启动时 owner-aware 恢复 orphaned `running` 任务；任务进入 `queued/running` 使用 guarded 状态切换并周期刷新 DB heartbeat，完成时清理归属；stale heartbeat 接管默认关闭、显式配置阈值后可回收其他失联实例任务；pending/queued 任务若已在本进程 active，会走 reconnect 防止双执行；执行启动/等待/取消/收尾/失败自愈时不会把 terminal 任务误写回 `queued/running/cancelled/completed/failed/timed_out`，provider failure / timeout 输给取消时按真实取消终态输出；active slot、DELETE 204、SSE / trace / export shape 保持不变。
- 默认运行策略保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。

## 当前验证基线

- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability`：`26/26` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue`：`66/66` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task`：`359/359` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings`：`216/216` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`：`1930/1930` 通过
- RAG targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag`，`78/78` 通过
- RAG route targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route`，`2/2` 通过
- Result summary targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary`，`30/30` 通过
- `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts`：`77/77` 通过
- `cd frontend && npm run lint`：通过
- frontend type contract：`npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts` 通过
- `backend/.venv/bin/python -m py_compile` 本轮相关 backend execution/persistence/test 模块：通过
- 进入本主线前的完整 e2e 封板基线：backend main phase、backend queue phase、frontend full Chromium `50 passed / 1 skipped`、frontend queue phase `1/1` 与 CI tooling 均已通过；本轮未重跑 e2e / frontend。
- `git diff --check`：通过
- 普通沙箱访问本机 Docker/端口会被权限拦截时，按流程提权后重跑，不拿旧结果冒充新结果。
- 测试/e2e/启动/提交的权限与依赖路径已固化到 `docs/development-runbook.md`；后续优先按 runbook 直接使用正确 venv、端口提权和 git 提权流程。

## 当前开发计划

1. 已封板主线：`real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening`。
2. 当前主线：`production-reliability-hardening`，进度约 `68%`；已完成 queue scope cleanup、session delete waiting cleanup、startup orphan running cleanup、execution owner/heartbeat 归属治理、stale heartbeat 接管开关、active stream race 防双执行、terminal start/wait/cancel/complete race 防误复活/防覆盖，以及 provider failure / timeout lost-race 失败自愈。
3. 后续优先围绕异常退出后的队列清理、持久化边界、失败自愈与 e2e 稳定性继续补红测。
4. 继续保持外部 SSE / trace / export / e2e 契约稳定，按“小红测 -> 实现 -> targeted/full slice”推进。

## 后续候选主线

- `rag-product-experience`：面向用户可见能力增强，聚焦知识库版本对比、文档治理、检索解释与召回质量评估。
- `observability-experience`：打磨 Workbench、Task Center、Trace、失败诊断、任务回放与知识库治理的可读性和操作效率。
- `provider-tool-expansion`：按小红测继续扩展真实 provider、工具协议与 registry 管理能力，不扩大既有外部契约。
- `ci-release-engineering`：把当前手工封板验证基线进一步沉淀为分层 CI、e2e 编排和发布前检查。

## 关键能力边界

- 外部 SSE / trace / export / e2e 契约保持稳定，优先做内部 runtime/helper/display 收口。
- 新增 provider/source 协议继续按 `real-tool-execution` 已完成验收基线补小红测，不再作为封板主线阻塞项。
- 单文件规模纳入治理：新增测试/实现优先使用主题文件；主题文件明显膨胀时先拆分到新文件/新模块，沿用既有 slice 主题包与 facade 拆分方式。
- `data/insightagent.plan.back.md` 是只读备份计划，不参与活跃开发同步。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard 与主链路 e2e / CI tooling 已落地。
- 当前进入 `production-reliability-hardening` 主线，继续围绕可靠性补红测和局部收口。

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
