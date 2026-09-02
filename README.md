# InsightAgent

可观测 AI Agent 平台，覆盖会话、任务执行、Trace、Memory、RAG、鉴权、持久化、导出、运行态诊断与 CI/release 门禁。

## 当前状态

- `provider-tool-expansion` 已 100% 封板。
- `ci-release-engineering` 已 100% 封板。
- `production-runtime-hardening` 已 100% 封板：SSE `error.diagnostic`、失败审计 detail、前端审计详情与 reconnect provider 错误消息已对齐低敏诊断语义，旧字段保持兼容。
- `product-ux-polish` 已 100% 封板：语义 Trace 回放、Task Center/任务详情 normalized 状态与失败诊断、列表加载错误/陈旧数据保留/原位重试、任务详情 failure hint code 映射与 SSE close 后失败摘要兜底均已收口。
- `production-operations-readiness` 已 100% 封板：`/health` 新增非敏感 `operations` 摘要，暴露部署配置、SLO 阈值口径、备份恢复演练、运维 runbook/值班响应、应急响应演练新鲜度、告警等级汇总、按域风险汇总、机器友好的 readiness_level、readiness_checks 清单、任务队列、执行实例、stale recovery、超时与 Chroma probe 的运维 readiness/warnings，不改变既有 `/health` 字段。
- `security-hardening` 已进入，当前约 10%：后端已补全局安全响应头，覆盖 nosniff、frame deny、referrer policy、permissions policy 与 cross-origin opener policy；业务 payload 与 SSE/trace/export 契约不变。
- 后端与前端 e2e 后置 CI 稳定性已收口：backend 无 venv runner JSON 校验 fallback、frontend queue runtime API base URL、queue 慢加载稳定性与 export diagnostics 范围均已修复；commit `6ea51c7` 对应 GitHub `backend-e2e`、`frontend-e2e`、`release-gate` 均为 success。
- 后续开发继续保持 SSE / trace / export / e2e 外部契约兼容，并维持 backend/app、backend/scripts 与 frontend 源码单文件 <= 3000 行边界。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase all --summary-file /tmp/release-gate-all-summary.md --json-summary-file /tmp/release-gate-all-summary.json` 通过，覆盖 backend/frontend/tooling/hygiene 全量；JSON summary 已用 `json.tool` 复核；无 `backend/.venv` fixture 下 release readiness / release gate JSON 校验通过。
- Backend：full slice `2003/2003`；module boundary `4/4`；targeted security_headers `3/3`、production_operations `12/12`、production_operations_health `10/10`、production_reliability `39/39`、reconnect `9/9` 通过。
- Frontend：workbench utils targeted `78/78`、store utils targeted `16/16`、task detail targeted `10/10`、audit targeted `10/10`、knowledge governance targeted `6/6`；node tests `140/140`、`npm run lint`、`npm run build` 通过。
- E2E 基线：backend main、timeout、queue 三段通过；backend tooling scope 本地复验通过；frontend queue Chromium 专项本地复绿；backend finalize + artifact-stage guard 在 main push `fail-on-missing` 下通过，`included_count=20`、`missing_count=0`；frontend full Chromium `56 passed / 1 skipped`，targeted Chromium remote network/401/cancel、trace delta retry、审计日志/Task Center/知识库治理错误恢复均通过；commit `6ea51c7` 的 GitHub `backend-e2e` run `33373178443`、`frontend-e2e` run `33373178435`、`release-gate` run `33373178464` 均 completed success。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check`、备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 当前开发计划

1. 当前状态：`security-hardening` 已进入，当前约 10%；已完成后端全局安全响应头第一片，下一步继续寻找鉴权会话、生产密钥校验、限流或依赖安全审计中的可红测缺口。
2. 已封板主线新增 `production-operations-readiness`；既有 provider/tool、生产运行态、源码规模、CI/release、RAG、可观测性、可靠性、治理、并发与产品体验主线保持完成。
3. 下一候选主线保留 `release-observability-polish`。

## 稳定契约

- SSE 事件、`TraceStep`、result summary、safe output、JSON/Markdown export shape 保持稳定；`error.diagnostic` 与 failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性。
- 后端全局 HTTP 响应追加安全 header；只增加响应头，不改变 JSON payload、SSE event、trace/delta 或 export body shape。
- 任务详情页 `trace_semantic` URL 参数保持兼容扩展；语义切换仅同步 URL 并清理本地筛选，状态文字/色调与轮询控制优先使用 `status_normalized`，均不改变任务、trace 或 export payload。
- Workbench Inspector 语义筛选只调整前端本地 trace 筛选状态：保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure source 诊断 chips 与状态筛选只调整前端本地筛选/展示状态；状态、失败摘要和观测筛选统一优先使用 `status_normalized`，显式 `failure_hint/failure_source` 优先于 trace 文本推断，不改变任务列表 API 与 trace/export payload。
- Task Center、Audit Logs 与知识库治理的加载错误、陈旧数据保留与原位重试只调整前端 query/presentation 状态，不改变任务、审计或 RAG API shape。
- SSE close 后失败摘要兜底只在流结束但前端尚未进入 terminal phase 时补拉任务/trace 并映射低敏 failure hint，不改变 SSE、任务、trace 或 export payload。
- 默认 settings 仍按 provider/model/api_key 自动选择 `remote` 或 canonical `mock`。
- queued/running/cancel/reconnect 与 task recovery 语义保持稳定。
- `data/insightagent.plan.back.md` 是只读备份计划，永远不参与同步或修改。

## 核心边界

- `PostgreSQL` 保存用户、会话、消息、任务、trace、usage、设置与审计，是完整历史和回放账本。
- `Chroma Memory` 使用会话级 collection `memory_{session_id}`，服务当前对话的语义记忆。
- `Chroma RAG` 使用知识库 collection `kb_{user_hash}_{knowledge_base_id}`，服务跨会话复用资料。
- Chroma 默认连接 `127.0.0.1:8001`；不可达时 Memory/RAG 接口返回 503，任务后的 memory 摘要写入保持 best-effort。
- 仓库主目录为 `backend/`、`frontend/`、`data/`；完整启动和门禁细节以 runbook 为准。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard、生产可靠性治理与主链路 e2e / CI tooling 已落地。
- 观测体验：失败诊断、任务回放、Trace 语义过滤、Task Center 观测筛选、Audit Logs 服务端 keyword 与跨视图 Failure 回放已落地。
- RAG 产品体验：知识库版本明细、source/document 文档组、文档组删除、召回摘要、质量分布、筛选与 distance 解释已落地。
- Provider/tool 兼容：常见搜索总量/命中归一化、多 provider planner 工具调用形态、JSON 字符串参数与 failed reconnect 错误码复原已落地。

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
├── docs/
└── data/
```

## 运行与门禁

```bash
docker compose up -d chroma
./start_insightagent.command
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

默认 Chroma 连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

详细测试、e2e、启动和提交流程以 [`docs/development-runbook.md`](docs/development-runbook.md) 为准。

## 后续候选主线

- `release-observability-polish`：发布/回滚可见性、artifact 保留策略与门禁趋势摘要。

## 下一步

- `security-hardening` 继续按先红测、再实现、再 targeted/full slice 推进，优先找鉴权会话、生产密钥校验、限流与依赖安全审计中的小切片。

## 文档维护约定

- 活跃进度块只收敛“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”。
- README 中的长期参考章节、接口范围、运行约定、实现入口、SSE/Trace 与 Memory/RAG 说明不应在封板收敛时被整段删除。
- 长串历史流水账、阶段内小切片、旧失败过程和重复验证清单不继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
