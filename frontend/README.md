# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（根目录 `.nvmrc`、`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端镜像一致）。

## 当前状态

- 前端阶段 5 已具备完整演示闭环：Auth Gate、Workbench、Trace、Memory/RAG 调试、usage dashboard、导出、任务详情、running task 恢复、审计与知识库治理均已落地。
- 已封板主线：`real-tool-execution`、队列/并发治理、registry/RAG 治理、生产可靠性、可观测体验、RAG 产品体验、`provider-tool-expansion`。
- 当前封板结论：provider-tool 兼容由后端完成；前端继续消费既有 preview/output/result-summary、trace/export 字段，无需新增本地显示分支。
- 稳定契约：SSE / trace / export shape、queued/running/cancel/reload recovery、Task Center 与任务详情回放语义保持不变。
- 回归重点：workbench 主链、remote errors、settings、usage dashboard、知识库治理与 common tooling。
- 后续候选主线：`ci-release-engineering`。

## 当前验证基线

- Frontend node tests：`121/121` 通过。
- Frontend quality gates：`npm run lint` 与 `npm run build` 通过。
- Frontend e2e：full Chromium `52 passed / 1 skipped`；queue phase 低并发专项 `1/1` 通过。
- Backend 契约基线：full slice `1983/1983`、tool_registry `494/494`、http_json `531/531`、facade `4/4`、provider_search `15/15`、tool_plan_provider `57/57`、backend main e2e 通过。
- Hygiene：diff checks、备份计划 diff 检查与端口清理通过。

## 下一步前端计划

1. 当前主线：`provider-tool-expansion` 已 100% 封板；四份活跃文档已收敛到当前状态、验证基线、候选主线与稳定契约。
2. 已封板主线：从 `real-tool-execution` 到 `provider-tool-expansion` 的九条主线均已封板。
3. 后续候选主线：`ci-release-engineering`；后续体验维护继续保持 Workbench composer queued/running/cancel 细节、任务详情页 queued/running/terminal 回放、导出与 trace 契约稳定。
4. 后续前端回归门继续以 frontend node/type/lint、低并发 queue phase、targeted Chromium 与 full Chromium 为准；涉及 UI 时再补 fresh frontend/e2e。

## 后续候选主线

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
- RAG / Memory 调试：运行调试子页展示召回摘要、质量分布、筛选、来源摘要与 distance 解释
- 知识库治理：列表、版本明细展开、文档组摘要、文档组删除、来源采样、shared 权限显隐、清空/删除
- 审计日志：筛选、分页、详情、导出
- usage dashboard：趋势、会话榜、任务榜与来源分布

## 当前运行态重点

- 实时流、持久化 trace 与导出回放当前共用同一套 `TraceStep` 消费主干，前端优先避免派生本地专用语义。
- `tool_end.result_summary`、preview/output key、retrieval follow-up 与 registry diagnostics 已进入工作台主展示链，当前重点是继续跟随后端消除 helper fallback 漏洞。
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
- 本轮后端仅做 runtime 大文件主题拆分，前端消费契约不变；node/lint/build 作为无回归确认。
- 文档只保留当前能力、封板主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
