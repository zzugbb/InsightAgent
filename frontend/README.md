# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（根目录 `.nvmrc`、`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端镜像一致）。

## 当前状态

- W1-W4 主链路已完成并收口：Auth Gate、Workbench、Trace 双视图、Memory / RAG 调试、usage 展示、任务与会话导出、任务详情页、running task 恢复等已具备可演示闭环。
- 当前前端主线已从“配合 runtime spec 内部收口”转向“真实工具语义在工作台中的稳定呈现”，重点跟随后端推进：
  - extra/real tool 的 display label、preview/output/result-summary 语义
  - retrieval follow-up 与 tool-registry diagnostics 展示
  - model settings 中 provider/source diagnostics 与 selected source 说明
  - 真实工具输入、计划项与最终 trace/export 回放的一致性
- 最近已对齐到代码的高信号能力：
  - `tool_end.result_summary`、preview/output key 与安全 observation 已进入流式 store 与回放主链，不再回退泛化 `Tool done: ...` 或原始 JSON；当后端只保留 step meta 而未保留原始 `output` 时，也会优先回放 `result_summary` / `output_preview`，并把 preview 继续作为结构化 success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 透传；Memory / RAG 调试返回的 query metadata、query payload root、RAG ingest 文档行、RAG route 列表/命中行、shared merge 结果、session create/detail/list/messages/export、task/session usage、task detail/list/trace/export/stream-reconnect、auth/audit 列表相关 outward summary，以及由 `chat_persistence_service` 直接产出的 task summary/export/trace 批量聚合结果、task/session export response summary 与 export builder 路由入口，现在也不会再因后端 typed payload 被归一化成空对象或直接报错。
  - trace display/search 已能消费 `meta.tool_registry.entries`；model settings modal 已消费 `diagnostics_summary`，broken file-backed source 不会直接从设置里消失。
  - 后端 `extra_tools` / `overrides` 已可绑定 `execution.kind=http_json` 的真实执行器，因此 workbench 对 provider search / provider calc 一类 real tool 的 preview/output/result-summary/observation/export 回放，不再默认假设它们只是本地 template runner 的语义换壳。
  - model settings modal 的 tool detail summary 现会直接显示 `via http_json` 一类 `execution_kind`，前端可以更直观看到某个 provider/source tool 是否已经接到真实执行器。
  - 当后端显式配置了无效 `execution` 时，当前策略是 fail-fast 而不是静默回退 stub runner；前端后续看到的是明确的配置错误，而不是“看似成功、实际跑了本地模板”的假语义。
  - 同时，provider/source diagnostics 现在也会把这类静态可判定的坏配置提前归一成 `invalid/tool_executions` 项；设置面板不需要等任务真跑起来，source diagnostics 就能先提示 real tool 的执行器配置已经坏掉。
  - 后端对 `http_json` real tool 新增的安全 `execution_summary` 也会随 tool meta 进入 SSE/trace/export 主链；即使前端当前还没单独做专门 UI，这份 method/origin/path/query-body/result-field 概览已经会稳定跟着工作台回放语义走。
  - 后端现在还支持 `http_json` 执行模板读取运行时 `settings_api_key/settings_base_url/tool_registry_provider_source` 上下文，并在 `headers/url/query/json_body` 中使用 `${...}` 做安全字符串插值；前端继续只消费安全 `execution_summary` 与 diagnostics，不会把 secret 模板值直接带进设置面板或 trace UI。
  - 即使 provider/source 改成 file-backed registry manifest，后端也会继续把同一套 source 级模板上下文灌进 `extra_tools/overrides`；因此前端看到的 source diagnostics、tool detail summary 与运行态 trace 语义不会再因配置承载形态不同而分叉。
  - 对 `http_json` 模板里拼错的 `settings_*` / `tool_registry_*` 运行时变量，后端现在会更早在 source diagnostics 中给出 `invalid/tool_executions` 提示；前端不必等真实 tool 执行到上游请求阶段，设置治理面就能先看出是模板变量 typo，而不是网络/权限波动。
  - workbench trace subtitle 与搜索现在会直接消费 `execution_summary`；真实工具运行中的 `POST https://.../search`、response path、result fields 等安全摘要已经能在前端回放和检索里直接看到。
  - model settings modal 的 tool detail summary 现在也会直接显示 `execution_summary` 的 endpoint 与 query/body/response-field 摘要；provider/source 治理面不需要进入运行态 trace，就能先看出某个 `http_json` real tool 会打到什么路径、响应会映射到哪些字段。
  - real/provider retrieval 与 runtime override real tool 的 follow-up、result summary、observation、导出回放已不再误写成本地默认知识库命中。
  - extra/real tool 的注册语义、safe output 与计划项输入会优先沿 configured registry 继承；后端 provider planner 与真实 remote provider 现在也共用一套 response text / usage 提取语义，能稳定消费 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 usage alias、脏 usage 值与流式 delta 文本字段变体，因此前后端对 name-only fallback 与旁路结构化 payload 的消费已基本一致。
- 当前最近一次已记录校验基线：
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts` 通过（`29/29`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`4/4`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`39/39`）
  - `cd frontend && npm run lint` 通过
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`835/835`）
  - `bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `git diff --check` 通过

## 当前已有内容

- 三栏工作台：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试，失败后自动回登录
- Workbench：聊天主视图、任务中心抽屉、任务详情页 `/tasks/[taskId]`
- Inspector：Trace 时间线 / 流程图双视图、Context 概览、同步诊断、当前任务
- 流式链路：SSE 状态、token 追加、trace 实时更新、`trace/delta` 自动静默轮询与结束补拉
- running task 恢复：刷新页面或切回会话时自动接管 `pending/running` 任务流
- 导出：任务与会话 JSON / Markdown 导出
- 模型设置：`mock / remote` 模式切换、校验、保存、错误码友好提示、provider/source diagnostics 说明
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
- `app/components/workbench/model-settings-modal-utils.ts`：settings 预览、provider/source/tool registry diagnostics 说明
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
- 文档只保留当前能力、当前主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
