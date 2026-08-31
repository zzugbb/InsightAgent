# InsightAgent Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台。Node.js 使用 24.x。

## 当前状态

- `provider-tool-expansion`、`ci-release-engineering` 与 `production-runtime-hardening` 均已 100% 封板；`product-ux-polish` 已进入开发，当前约 67%。
- Workbench、Task Center、任务详情、Trace/Context Inspector、Memory/RAG 调试、设置、审计、usage dashboard 与知识库治理已落地。
- 前端继续消费后端统一的 preview/output/result-summary、trace/export 字段，不新增 provider 专用显示分支。
- SSE `error.diagnostic.reason` 与 failure audit diagnostic 是后端追加的低敏兼容字段；前端现有错误提示继续使用 `code/message/detail/status_code`，审计详情可展示低敏 diagnostic reason，reconnect 继续依赖后端稳定 code/message。
- 任务详情页与 Workbench Inspector 已补齐语义 Trace 聚焦；Task Center failure drilldown 和列表/详情 normalized 状态展示已对齐，避免隐藏或误标可诊断任务。
- `app/globals.css` 已拆为 `app/styles/` 主题模块；前端源码体积边界已纳入 node 测试，生成锁文件不作为拆分对象。
- 前端 e2e workflow 覆盖 smoke/full/queue，queue 阶段使用独立 `:8011` backend；main push Playwright artifact-stage guard 使用 `fail-on-missing`。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto` 通过，Markdown/JSON summary 与 release readiness matrix 输出通过。
- Node tests：workbench utils targeted `75/75`、task detail targeted `9/9`；8 个测试文件 `133/133` 通过，包含 frontend source size boundary。
- `npm run lint` 与 `npm run build` 通过。
- E2E 基线：targeted Chromium semantic URL replay `1/1`、Workbench Inspector semantic filter replay `1/1`、Task Center/任务详情 normalized status replay `1/1`、Task Center failure diagnostic replay `1/1`、remote failure replay `1/1` 通过；full Chromium `52 passed / 1 skipped`；低并发 queue phase `1/1` 且已纳入 CI workflow。
- Backend 契约基线：full slice `1988/1988`；module boundary `4/4`。

## 下一步前端计划

1. 当前状态：`product-ux-polish` 约 67%，已补齐 Trace 语义 replay、筛选干扰清理、Task Center failure drilldown 与列表/详情 normalized 状态展示。
2. 已封板主线：`provider-tool-expansion`、`production-runtime-hardening`、`source-size-maintenance`、`ci-release-engineering`、`rag-product-experience`、`observability-experience`、`production-reliability-hardening`、`rag-governance-hardening`、`registry-governance`、`concurrency-fairness-policy`、`queue-and-concurrency-lite`、`real-tool-execution`。
3. 本主线继续聚焦 Workbench/Task Center 高频操作、trace 回放可读性与治理页面效率。
4. 后续前端回归门继续以 frontend node/type/lint、低并发 queue phase、targeted Chromium 与 full Chromium 为准；涉及 UI 时再补 fresh frontend/e2e。

## 后续候选主线

- `product-ux-polish`：Workbench/Task Center 高频操作、trace 回放可读性、治理页面效率与失败诊断入口可发现性。

## 稳定契约

- SSE 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- `trace.step` 与后端 `TraceStep` 同构；`tool_start/tool_end` 与 action 节点通过 `step_id` 对齐。
- Workbench 使用 `trace/delta` 做静默增量刷新，流结束后补拉最终快照。
- result summary、safe output、failure hint 与 diagnostics 使用后端统一语义。
- `trace_semantic` URL 参数兼容支持 `planner/retrieval/calculator/failure`；详情页语义切换仅同步 URL 并清理本地筛选，状态文字/色调优先使用 `status_normalized`，均不改变任务、trace 或 export payload。
- Workbench Inspector 语义筛选只调整本地 trace 筛选状态：保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure source 诊断 chips 与状态筛选只调整前端本地筛选/展示状态；来源分组不被当前来源 drilldown 自过滤，重复点击已选来源会取消来源 drilldown，切换到非 failure-hint 观测维度会清理隐藏来源筛选，状态筛选、状态展示与失败样式优先使用 `status_normalized`，不改变任务列表 API 与 trace/export payload。
- queued/running/cancel/reconnect 与 task recovery 前端语义保持稳定。

## 能力索引

- Workbench：会话、消息、任务中心、Trace/Context Inspector 与 running task recovery。
- 任务回放：任务详情页、Trace 时间线/流程图、Failure 入口、任务和会话 JSON/Markdown 导出。
- 任务详情页支持通过 `trace_semantic` URL 参数直达语义 Trace，并在切换时更新可分享 URL、清理旧筛选；Task Center failure drilldown 可直达 Failure 回放，列表与详情状态文字/色调统一优先使用 normalized 状态。
- 设置与治理：模型设置、provider/source diagnostics、task queue diagnostics、审计日志、usage dashboard、知识库治理。
- Memory/RAG 调试：会话级 `memory_{session_id}` 调试入口、知识库 `kb_{user_hash}_{knowledge_base_id}` 状态/写入/检索入口。
- 前端不新增 provider 专用显示分支，继续消费后端统一 preview/output/result-summary 与 trace/export 字段。

## 当前已有内容

- 三栏工作台：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试，失败后自动回登录
- Workbench：聊天主视图、任务中心抽屉、任务详情页 `/tasks/[taskId]`
- Inspector：Trace 时间线 / 流程图双视图、Context 概览、同步诊断、当前任务
- 流式链路：SSE 状态、token 追加、trace 实时更新、`trace/delta` 自动静默轮询与结束补拉
- running task 恢复：刷新页面或切回会话时自动接管 `queued/pending/running` 任务流
- 导出：任务与会话 JSON / Markdown 导出
- 模型设置：`mock / remote` 模式切换、校验、保存、错误码友好提示、provider/source diagnostics 与 task queue diagnostics 限额/全局与当前用户计数/可用槽位/压力状态/等待策略说明
- RAG / Memory 调试：运行调试子页展示召回摘要、质量分布、筛选、来源摘要与 distance 解释
- 知识库治理：列表、版本明细展开、文档组摘要、文档组删除、来源采样、shared 权限显隐、清空/删除
- 审计日志：筛选、分页、详情、导出
- usage dashboard：趋势、会话榜、任务榜与来源分布

## 当前运行态重点

- 实时流、持久化 trace 与导出回放当前共用同一套 `TraceStep` 消费主干，前端优先避免派生本地专用语义。
- `tool_end.result_summary`、preview/output key、retrieval follow-up 与 registry diagnostics 已进入工作台主展示链，当前重点是继续跟随后端保持 helper/runtime 语义一致。
- 任务失败线索已进入共享快照语义；Task Center、任务详情、Usage Dashboard 与 Audit Logs 复用同一失败摘要、来源分类、可读错误码和 Failure 轨迹入口。
- Usage Dashboard、Audit Logs、Task Center 与任务详情页已统一失败回放入口和 Failure 计数。
- running task recovery、remote cancel、model settings diagnostics 与知识库治理 shared 权限是当前最容易回归的前端运行态重点。
- 当前前端回归重点仍围绕 workbench 主链、remote errors、settings、usage dashboard 与 common tooling。

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、会话导出入口与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：模型设置、审计、用量统计、知识库治理与当前用户信息入口
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/usage-dashboard-modal.tsx`：用量仪表盘
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx` / `audit-logs-modal-utils.ts`：审计日志筛选、服务端 keyword URL、分页、失败详情可读化、展开与导出
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库治理
- `app/components/workbench/runtime-debug-modal.tsx`：Memory / RAG 调试
- `app/tasks/[taskId]/page.tsx`：任务详情页与任务导出入口
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/stores/chat-stream-store-utils.ts`：tool_end / tool meta 合并、preview/output/result-summary 归一化
- `app/components/workbench/utils.ts`：trace display、tool result preview、follow-up 展示与搜索辅助
- `app/components/workbench/model-settings-modal-utils.ts`：settings 预览、provider/source/tool registry diagnostics 与 task queue diagnostics 说明
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期
- `lib/types/trace.ts`：前端 TraceStep 类型

## SSE 消费与契约对齐

当前前端按以下事件消费：

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

- `trace` 事件中的 `step` 与后端 REST `TraceStep` 同构。
- `tool_start/tool_end` 会先驱动 action 节点状态，再由 `trace` 事件补齐持久化快照。
- Workbench 会定时静默拉取 `trace/delta`，失败时退避重试，并在流结束后自动补拉一次。
- 同步健康度会在 Inspector Context 区域展示，便于定位网络抖动或增量拉取异常。

## Memory（会话级）

- collection 规则：`memory_{session_id}`
- 状态读取：`GET /api/sessions/{session_id}/memory/status`
- 写入调试：`POST /api/sessions/{session_id}/memory/add`
- 检索调试：`POST /api/sessions/{session_id}/memory/query`

## RAG（知识库）

- 状态：`GET /api/rag/status?knowledge_base_id=...`
- 写入：`POST /api/rag/ingest`
- 检索：`POST /api/rag/query`
- 默认知识库 ID：`default`
- 实际 collection：`kb_{user_hash}_{knowledge_base_id}`

## PostgreSQL / Memory / RAG 怎么看（前端通俗版）

- `PostgreSQL`：完整历史，支撑会话、消息、任务、trace、usage、导出。
- `Memory`：当前会话便签，适合放“本次对话临时约束和结论”。
- `RAG`：外部知识库，适合放手册、FAQ、产品文档。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

说明：

- `npm run dev` / `npm run start` 固定监听 `127.0.0.1:3001`
- 默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端；未设置时使用 `http://127.0.0.1:8000`

前端 e2e 常用命令：

```bash
npm run test:e2e
npm run test:e2e:smoke:matrix
```

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

详细 e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。

## 当前约束

- 当前前端优先保持与后端 SSE / trace / export 契约稳定对齐，不主动发散出新的本地语义分支。
- registry-governance 已封板，settings/preflight/runtime trace/display/export 一致性保持稳定，不优先继续扩张旧 payload fallback。
- 文档收敛只处理当前状态、验证基线、下一步计划/候选主线、稳定契约和高信号摘要；长期参考章节不应被整段删除。
