# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（根目录 `.nvmrc`、`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端镜像一致）。

## 当前状态

- 前端 W1-W4 与阶段 5 基础产品化已完成：Auth Gate、Workbench、Trace 双视图、Memory/RAG 调试、usage dashboard、任务/会话导出、任务详情页、running task 恢复、审计与知识库治理已具备可演示闭环。
- `real-tool-execution` 当前验收基线已完成收尾：workbench / live store / model settings 已承接 `execution_summary`、`execution_diagnostics`、safe output、result-summary、name-only semantic fallback 与 task/session export 回放语义。
- 前端继续保持与后端 SSE / trace / export 契约稳定对齐，不为真实工具执行新增独立本地语义分支。
- 下一主线启动前的仓库 pre-flight 已完成：后端 runtime slice 测试二次细分完成，`tool_runtime.py` 已抽出 planner/execution/HTTP JSON/registry facade 模块，原测试入口保持不变。
- `queue-and-concurrency-lite` 首轮主线已完成：后端已接入 create 默认 queued、进程内执行槽位、queued SSE state、queued cancel 等待项移除与低并发 queue 专项 e2e；前端已把活跃任务识别扩展为 `queued/pending/running`，能从安全 queue snapshot 显示当前任务排队位置，并在取消/timeout/完成与 queued 恢复时清理或保留正确 phase，当前已覆盖工作台恢复、Task Center、Inspector、任务详情页、Chromium e2e helper、queued recover/cancel、running cancel 终态、Task Center session/global 多任务隔离、刷新后后台会话 stream 不误恢复与完整 Chromium。
- `concurrency-fairness-policy` 已启动：后端已补可选按用户/按 session 并发执行槽位上限、capacity-aware oldest eligible FIFO 防插队、duplicate active task 非拥有 slot 释放防护、旧等待项互斥 eligibility 容量估算、旧等待项预占 scope quota 后的当前任务准入判断与 backend queue e2e 安全快照/安全计数 helper 覆盖，默认关闭且不改变现有 SSE/trace/export；前端运行设置已带当前 `activeSessionId` 请求只读 `task_queue_diagnostics` 摘要，settings URL helper 会归一化 API base 尾斜杠并带 encoded `session_id` 请求当前会话诊断，可查看全局、当前用户、当前会话 active/waiting/available 安全计数，其中当前用户 available 是全局空槽与 per-user 剩余额度共同收敛后的有效可用槽位，当前会话 available 是全局空槽与 per-session 剩余额度共同收敛后的有效可用槽位，并在触顶时显示 `your limit reached` / `session limit reached`；前端 `TaskQueueDiagnostics` 类型已把基础运行态计数、waiting policy 与 capacity-aware FIFO 标记收紧为必填字段，并把 `pressure_state` / `waiting_policy` 收紧为与后端一致的固定枚举，后端 `SettingsSummaryResponse` / `_build_task_queue_diagnostics()` 也已用 typed diagnostics 契约固定 required 基础字段与 governance 字段且保持 scope 字段 optional；后端 helper 已校验 queued SSE queue snapshot 基础字段存在性、结构一致性、count/wait_position 整数类型与 settings diagnostics 基础计数字段存在性、整数型 `max_concurrent`/计数/治理限额字段、数值型 poll interval、精确 `pressure_state` 枚举、布尔型状态/治理标记、非负治理限额、governance 必填字段、`has_waiting_tasks`/`saturated`/`pressure_state` 必填、固定枚举值与派生一致性、当前用户/当前会话 active/waiting scope 计数成组依赖且不超过全局计数、限额触顶、可用槽位派生一致性与 available slots 字段依赖；同时展示 scope-limited/saturated 压力状态、fairness 开关、capacity-aware FIFO 等待策略与 poll interval。

## 当前验证基线

- `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts`：`76/76` 通过
- `npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts`：通过
- targeted Chromium：主路径导出、404 ownership 导出、取消后立即重发 `3/3` 通过
- backend queue e2e phase：低并发 backend 下 queued cancel / safe wait_position / settings safe global/current-user/current-session active/waiting/available counts / followup completion 最近 fresh 通过；脚本 helper 现额外校验 queued snapshot 结构一致性、queued snapshot count/wait_position 整数类型、scope available slots 字段依赖、scope active/waiting 计数上界、整数型 settings `max_concurrent`/计数/治理限额、数值型 poll interval、布尔型 settings 状态/治理标记、非负治理限额、governance 必填字段与 settings `pressure_state` 精确枚举值
- frontend queue phase：低并发 backend/frontend 下 `bash scripts/ci_run_frontend_e2e.sh --phase queue --api-base-url http://127.0.0.1:8011 --frontend-base-url http://127.0.0.1:3001` 最近 fresh 通过，`1 passed`；默认 full 环境下该低并发专项显式 skip
- frontend running cancel Chromium：默认 backend/frontend 下 `npm run test:e2e -- e2e/workbench-edge-cases.spec.ts -g "running task cancel reaches"` 通过
- frontend multi-task Chromium：默认 backend/frontend 下 `npm run test:e2e -- e2e/workbench-edge-cases.spec.ts -g "task center separates active session"` 通过
- frontend reload isolation Chromium：默认 backend/frontend 下 `npm run test:e2e -- e2e/workbench-edge-cases.spec.ts -g "reload keeps background session stream"` 通过
- 完整 Chromium e2e：真实 backend/frontend 服务下 `bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001` 最近 fresh 通过，`50 passed / 1 skipped`；低并发 queued 专项在 full 阶段按预期 skip
- 最近 e2e 轮次启动的 8011、8000、3001 服务均已发送 Ctrl+C 并正常退出；最后的 `lsof` 端口残留确认因提权审批通道连接断开未能执行。
- `bash scripts/test_ci_e2e_tooling.sh all`：通过
- `git diff --check`：通过
- 后续启动 frontend、访问本机 e2e 服务、跑 Chromium e2e 和提交时，先按 `../docs/development-runbook.md` 使用固定 Node/npm 路径与提权边界，避免重复触发端口 / `.git/index.lock` 权限错误。

## 下一步前端计划

1. `concurrency-fairness-policy`：当前主线，约 `99.997%`；后端已完成可选按用户/按 session 并发执行槽位上限、capacity-aware oldest eligible FIFO 防插队、duplicate active task 非拥有 slot 释放防护、旧等待项互斥 eligibility 容量估算、旧等待项预占 scope quota 后的当前任务准入判断与 backend queue e2e 安全快照 helper 覆盖，前端已补 settings `task_queue_diagnostics` 限额、全局/当前用户/当前会话 active/waiting/available、当前用户/当前会话限额触顶、queued SSE queue snapshot 基础字段存在性、整数类型与结构一致性、settings 基础计数字段存在性、整数型 `max_concurrent`/计数/治理限额字段、数值型 poll interval、精确 `pressure_state` 枚举、布尔型状态/治理标记、governance 必填字段、非负治理限额、前端 diagnostics 类型契约、后端 `SettingsSummaryResponse`/builder typed diagnostics 契约、基础运行态字段必填契约、`pressure_state`/`waiting_policy` 跨端枚举契约、`has_waiting_tasks`/`saturated`/`pressure_state` e2e helper 必填、固定枚举值与一致性契约、当前用户/当前会话 active/waiting scope 计数成组依赖与全局上界、可用槽位、等待策略可观测入口与 settings session URL helper 边界；backend queue e2e 已最近 fresh 复验，frontend queue phase 与 full Chromium 保持上一轮 fresh 复验结果，下一步主要是最终封板复验与提交收口。
2. Workbench composer：继续细化 queued/running/cancel 后按钮 loading、重复 prompt resend、跨会话切换与刷新恢复。
3. 任务详情页：继续保持 queued/running/terminal 回放、导出与 trace 契约稳定。
4. e2e：保持 full Chromium、低并发 queue phase 与 targeted 边界专项作为进入下一主线前的回归门。

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
- `app/components/workbench/audit-logs-modal.tsx`：审计日志筛选、分页、展开与导出
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
- 下一阶段优先跟进真实工具执行本体接入后的 settings/preflight/runtime trace/display/export 一致性，不优先继续扩张旧 payload fallback。
- 文档只保留当前能力、当前主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
