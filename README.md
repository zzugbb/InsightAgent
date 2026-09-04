# InsightAgent

可观测 AI Agent 平台，覆盖会话、任务执行、Trace、Memory、RAG、鉴权、持久化、导出、运行态诊断与 CI/release 门禁。

## 当前状态

- 已封板主线：`provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`、`product-ux-polish`、`production-operations-readiness`、`security-hardening`、`release-observability-polish`。
- `security-hardening` 封板结论：安全 header、JWT header/默认密钥/CORS 硬阻断、refresh token 输入收敛、认证错误低敏化、auth session 副作用保护与 secret material 默认凭据阻断均已收口。
- `release-observability-polish` 封板结论：release readiness matrix、artifact `retention-days: 14`、release gate 前端类型契约测试、结构化 release gate summary、previous summary artifact 下载诊断、trend summary 与 `decision_summary` 已收口，可支撑 release approval 与 rollback decision。
- 当前状态：暂无新主线展开；等待用户授权 push 或选择下一主线。
- 外部 SSE / trace / export / e2e 契约保持兼容；`backend/app`、`backend/scripts` 与 `frontend` 源码继续维持单文件 <= 3000 行边界。

## 当前验证基线

- Release gate all：PASS，覆盖 backend/frontend/tooling/hygiene；JSON summary 已用 `json.tool` 复核，包含 `decision_summary`。
- Backend：full slice `2018/2018`；module boundary `4/4`；security `17/17`；production operations health `11/11`。
- Frontend：release gate 内置 node 清单与扩展 node tests 均为 `141/141`；`npm run lint` 与 `npm run build` 通过。
- Hygiene：`git diff --check`、`git diff --cached --check` 与备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 当前开发计划

1. `release-observability-polish` 已本地 100% 封板；本轮未 push。
2. 下一步由用户确认是否授权 push，或选择新的候选主线。
3. 后续开发继续按先红测、再实现、再 targeted/full slice 推进。

## 稳定契约

- SSE 事件、`TraceStep`、result summary、safe output、JSON/Markdown export shape 保持稳定；`error.diagnostic` 与 failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性。
- 后端全局 HTTP 响应追加安全 header；只增加响应头，不改变 JSON payload、SSE event、trace/delta 或 export body shape。
- Access token 解析要求 JWT header 为 `alg=HS256`、`typ=JWT`；签名、过期和 subject 校验语义保持不变。
- Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常。
- 生产环境禁止使用默认 `INSIGHT_AGENT_JWT_SECRET` 或其首尾空白包装值签发或验签 access token；开发默认值仍只允许在非生产环境使用。
- 生产环境默认 `INSIGHT_AGENT_JWT_SECRET` 及其首尾空白包装值也不能作为 refresh token 哈希或 secret 加密派生材料；`/health.operations` 按同一口径报告 `default_jwt_secret`。
- 生产环境禁止 `INSIGHT_AGENT_CORS_ORIGINS` 包含 wildcard `*`；非生产 CORS 调试行为保持不变。
- 鉴权依赖对 token parser 异常统一返回低敏 `401 invalid token`，保留 `WWW-Authenticate: Bearer`，不向客户端回显内部配置或解析细节。
- Auth token 签发与刷新会在创建/轮换 refresh token 和写入 auth session 前先校验 access token 签发配置；生产默认 JWT secret 错误不留下会话存储副作用。
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

`scripts/ci_run_release_gate.sh` 的 Markdown/JSON summary 会保留 summary kind、summary schema version、service-required 标识、resolved phases、逐步结果、步骤聚合计数、失败步骤标签与 release/rollback `decision_summary`；service-backed e2e 仍按 runbook 单独执行。
`scripts/ci_download_previous_release_gate_summary.sh` 会在 GitHub release-gate workflow 中尝试下载同分支上一条 successful `release-gate-summary` artifact；缺少 `gh`、分支、run id、历史 run 或 artifact 时只输出低敏诊断并保留 baseline 路径。
`scripts/ci_release_gate_trend_summary.sh` 可从当前和可选上一份 release gate JSON summary 生成趋势摘要，并透传 release/rollback `decision_summary`；GitHub release-gate workflow 会产出并上传 `release-gate-trend-summary` artifact。

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

默认 Chroma 连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

详细测试、e2e、启动和提交流程以 [`docs/development-runbook.md`](docs/development-runbook.md) 为准。

## 后续候选主线

- 暂无已展开新主线；下一步可在用户授权后 push 当前本地提交，或从新的产品/运维/安全候选中选择。

## 下一步

- 当前主线已本地封板；下一步等待 push 授权或新主线选择。

## 文档维护约定

- 活跃进度块只收敛“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”。
- README 中的长期参考章节、接口范围、运行约定、实现入口、SSE/Trace 与 Memory/RAG 说明不应在封板收敛时被整段删除。
- 长串历史流水账、阶段内小切片、旧失败过程和重复验证清单不继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
