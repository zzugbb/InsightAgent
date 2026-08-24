# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（根目录 `.nvmrc`、`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端镜像一致）。

## 当前状态

- 前端 W1-W4 与阶段 5 基础产品化已完成：Auth Gate、Workbench、Trace 双视图、Memory/RAG 调试、usage dashboard、任务/会话导出、任务详情页、running task 恢复、审计与知识库治理已具备可演示闭环。
- `real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening` 与 `production-reliability-hardening` 均已封板；前端继续保持与后端 SSE / trace / export 契约稳定对齐，不新增独立本地语义分支。
- Workbench 已承接 `execution_summary`、`execution_diagnostics`、safe output、result-summary、name-only semantic fallback 与 task/session export 回放语义。
- 队列 UI 已覆盖 `queued/pending/running` 活跃任务识别、安全 queue snapshot 排队位置、queued/running cancel、跨会话隔离、刷新恢复与 Task Center session/global 多任务隔离。
- 运行设置会带 active session 请求只读 `task_queue_diagnostics`，展示全局、当前用户、当前会话 active/waiting/available、安全限额触顶、`pressure_state`、fairness 开关、capacity-aware FIFO 等待策略与 poll interval。
- 前端 `TaskQueueDiagnostics` 类型已固定基础运行态、governance 字段与 `pressure_state` / `waiting_policy` 枚举；后端 runtime slice 拆分与 `tool_runtime.py` facade 拆分已完成，原测试入口保持不变。
- `registry-governance` 已封板：provider/source diagnostics、settings/preflight、runtime artifacts、trace/export/audit/SSE 与 task/usage 回放语义已完成脱敏和 alias 对齐，前端可见字段 shape 不变。
- 后端 `rag-governance-hardening` 已封板：RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口已完成治理收口；知识库治理表继续展示唯一文档版本数与首个版本号，trace 搜索可命中安全 source/document/version/hash。
- 后端 `production-reliability-hardening` 已 100% 封板，且最新 GitHub checks `2/2` 通过。前端相关契约已固定：客户端 SSE 断开保留 running 任务供 reload/reconnect/cancel，服务端执行协程取消才落 failed；前端可见删除会话响应、SSE、trace 与 export shape 不变。
- 当前进入 `observability-experience` 主线，进度约 87%：任务快照会从 trace diagnostics、TaskResponse failure fields 与 task_failed audit event 中提取失败线索并标注来源（SSE error / tool error / trace content / persisted trace），Task Center/任务详情/Usage Dashboard 会统一把稳定错误码映射为可读失败说明；Task Center 支持从任务列表批量回放 audit failure hint，展示/搜索该线索与来源，并支持按 Needs attention / Failed status / Failure hint / Failure trace 做观测筛选；Task Center 的 registry profile/provider source 筛选已进入本地任务快照过滤；任务详情页展示同一失败摘要，可从失败线索快捷定位 Failure 轨迹，并在原始 trace 缺少错误 step 时合成本地 failure 回放节点；Usage Dashboard 任务榜会显示失败摘要并可直接打开任务详情回放，Audit Logs 任务列也可进入同一回放页；Audit Logs keyword 已进入服务端过滤，分页、total、导出和 e2e 搜索口径一致；Trace 语义统计已新增 Failure 维度，Inspector 与任务详情页可按失败语义过滤轨迹。

## 当前验证基线

- `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts app/components/workbench/audit-logs-modal-utils.node.test.ts app/tasks/task-detail-page-utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts`：`101/101` 通过
- `cd frontend && npm run lint`：通过
- `npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts`：通过
- targeted TS：本轮涉及的 workbench utils、Task Center 与 Task Center governance e2e 通过 targeted `tsc` / Playwright 编译路径
- task center governance Chromium：`e2e/usage-dashboard.spec.ts:372`，`1/1` 通过，覆盖 Task Center registry profile/source 请求与列表可见性过滤
- task detail replay Chromium：`e2e/usage-dashboard.spec.ts:1323`，`3/3` 通过，覆盖 Task Center/任务详情 Failure 语义统计
- remote error observability Chromium：`e2e/workbench-remote-errors.spec.ts:479`，`1/1` 通过，覆盖 Task Center audit failure hint 回放与可读失败说明、Needs attention / Failed status 观测筛选、Audit Logs 服务端 keyword 请求、任务详情 audit failure hint 恢复与失败轨迹快捷定位
- usage/audit-to-detail Chromium：`e2e/usage-dashboard.spec.ts:774`，`1/1` 通过
- frontend targeted Chromium：`workbench-edge-cases.spec.ts:824` 与 `workbench-main-path.spec.ts:436` 均通过，覆盖 GitHub frontend-e2e 暴露的 reload/background session stream 与 reload recovery cancel 回归
- frontend full Chromium：默认 `8000/3001` 通过，`50 passed / 1 skipped`；低并发 queued 专项在 full 阶段按预期 skip
- frontend queue phase：低并发 `8011/3001` 通过，`1/1`
- backend main e2e phase：baseline / main / export consistency / cancel-timeout 通过
- backend queue e2e phase：低并发 `8011` 覆盖 queued cancel、safe queue snapshot、settings diagnostics 与 followup completion
- 后端可见契约回归：production reliability `35/35`、queue `66/66`、task `361/361`、settings `216/216`、usage dashboard `40/40`、backend full slice `1948/1948` 通过
- frontend diagnostics finalize：`scripts/ci_finalize_e2e_for_workflow.sh --scope frontend --event-name push --ref refs/heads/main` 在 `strict_level=any` 下通过，error-context counters 为 0
- GitHub checks：`7550120 fix: 保留客户端断流运行任务` 已 `2/2` 通过
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过
- `git diff --check`：通过
- 后续启动 frontend、访问本机 e2e 服务、跑 Chromium e2e 和提交时，先按 `../docs/development-runbook.md` 使用固定 Node/npm 路径与提权边界，避免重复触发端口 / `.git/index.lock` 权限错误。

## 下一步前端计划

1. 已封板主线：`real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening`、`production-reliability-hardening`。
2. 当前主线：`observability-experience` 已推进到约 87%，已完成任务失败线索摘要、来源分类、Task Center 观测筛选与 registry profile/provider source 本地筛选生效、任务中心/任务详情复用、Usage Dashboard / Audit Logs 任务详情回放入口、TaskResponse/audit failure hint 恢复、Task Center 列表 audit failure hint 批量回放、远端错误码可读映射、任务详情失败轨迹快捷定位、Usage Dashboard top tasks 失败摘要展示、Audit Logs 失败 hint/source/code/message 可读详情、Audit Logs 服务端 keyword 过滤，以及 Trace/Inspector/任务详情失败语义过滤与 Failure 统计。
3. 后续体验维护继续保持 Workbench composer queued/running/cancel 细节、任务详情页 queued/running/terminal 回放、导出与 trace 契约稳定，并继续补齐失败诊断分组、trace 筛选效率和跨视图回放效率。
4. 后续前端回归门继续以 frontend node/type/lint、低并发 queue phase、targeted Chromium 与 full Chromium 为准；涉及 UI 时再补 fresh frontend/e2e。

## 后续候选主线

- `rag-product-experience`：知识库版本对比、文档治理操作、检索解释、召回质量呈现与 RAG 调试体验。
- `observability-experience`：当前主线；优化 Workbench、Task Center、Trace、失败诊断、任务回放和知识库治理的可读性与操作效率。
- `provider-tool-expansion`：配合后端新增 provider/tool 协议，保持 settings/preflight/runtime/trace/export 显示契约稳定。
- `ci-release-engineering`：把 frontend node/type/lint、targeted Chromium、queue phase 与 full Chromium 基线沉淀为更明确的发布前门禁。

## 当前已有内容

- 三栏工作台：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试，失败后自动回登录
- Workbench：聊天主视图、任务中心抽屉、任务详情页 `/tasks/[taskId]`
- Inspector：Trace 时间线 / 流程图双视图、Context 概览、同步诊断、当前任务
- 流式链路：SSE 状态、token 追加、trace 实时更新、`trace/delta` 自动静默轮询与结束补拉
- running task 恢复：刷新页面或切回会话时自动接管 `queued/pending/running` 任务流
- 导出：任务与会话 JSON / Markdown 导出
- 模型设置：`mock / remote` 模式切换、校验、保存、错误码友好提示、provider/source diagnostics 与 task queue diagnostics 限额/全局与当前用户计数/可用槽位/压力状态/等待策略说明
- RAG / Memory 调试：设置中的运行调试子页
- 知识库治理：列表、来源采样、shared 权限显隐、清空/删除
- 审计日志：筛选、分页、详情、导出
- usage dashboard：趋势、会话榜、任务榜与来源分布

## 当前运行态重点

- 实时流、持久化 trace 与导出回放当前共用同一套 `TraceStep` 消费主干，前端优先避免派生本地专用语义。
- `tool_end.result_summary`、preview/output key、retrieval follow-up 与 registry diagnostics 已进入工作台主展示链，当前重点是继续跟随后端消除 helper fallback 漏洞。
- 任务失败线索已进入 `resolveTaskSnapshotSummary`，Task Center、任务详情页和 Usage Dashboard 共享同一失败摘要、来源分类与稳定错误码可读映射；任务详情页会从 TaskResponse/audit failure hint 恢复远端错误并提供 Failure 轨迹快捷定位；Task Center 任务列表会从 task_failed audit event 回放失败线索，观测筛选与 registry profile/provider source 本地过滤复用同一任务快照语义，Trace Failure 语义过滤复用同一失败判定 helper，避免另起本地分支。
- Usage Dashboard 任务榜已显示失败摘要并接入任务详情外链，Audit Logs 任务列也可直接进入任务回放页；任务失败/超时审计详情复用 stream 错误码文案生成 Failure hint，同时保留 raw message；Task Center 语义摘要和任务详情 KPI 已显示 Failure 计数。
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

## 本地启动

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

## 当前约束

- 当前前端优先保持与后端 SSE / trace / export 契约稳定对齐，不主动发散出新的本地语义分支。
- registry-governance 已封板，settings/preflight/runtime trace/display/export 一致性保持稳定，不优先继续扩张旧 payload fallback。
- 文档只保留当前能力、封板主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
