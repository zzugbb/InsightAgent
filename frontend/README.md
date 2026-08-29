# InsightAgent Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台。Node.js 使用 24.x。

## 当前状态

- `provider-tool-expansion` 已 100% 封板；兼容逻辑由后端承接，前端继续消费既有 preview/output/result-summary、trace/export 字段。
- 当前主线为 `ci-release-engineering`，进度约 78%；release gate 已纳入前端 node/lint/build、PR diff 自动分层、CI workflow、summary artifact 与 release readiness matrix。
- 前端 e2e workflow 已覆盖 smoke/full 以及低并发 queue recovery 阶段；queue 阶段使用独立 `:8011` backend，避免影响默认全量 UI 基线。
- main push 的 Playwright artifact-stage guard 严格度已升级为 `fail-on-missing`，PR 仍使用 `fail-on-empty`。
- Workbench、Task Center、任务详情、Trace/Context Inspector、Memory/RAG 调试、设置、审计、usage dashboard、知识库治理均已落地。
- 全局样式拆分已完成：`app/globals.css` 仅保留有序 import，实际样式按主题拆入 `app/styles/`。
- 前端源码体积边界已纳入 node 测试；`package-lock.json` 属于生成锁文件，不作为拆分对象。
- SSE / trace / export、queued/running/cancel/reload recovery 与任务回放语义保持稳定。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto` 通过，Markdown/JSON summary 与 release readiness matrix 输出通过。
- Node tests：8 个测试文件，`122/122` 通过，包含 frontend source size boundary。
- `npm run lint` 通过。
- `npm run build` 通过。
- E2E：full Chromium 既有基线 `52 passed / 1 skipped`；低并发 queue phase 既有基线 `1/1` 且已纳入 CI workflow；本轮 targeted Chromium `workbench-main-path` `5/5` 通过。
- Backend 契约基线：full slice `1983/1983`；`registry 534/534`、`http_json 531/531`、`provider 538/538`、`runtime 163/163`、`trace 188/188`、`export 184/184`、`usage 63/63`；module boundary `4/4`。

## 能力索引

- Workbench：会话、消息、流式 token、任务中心、Trace 时间线/流程图、Context 与同步诊断。
- Recovery：刷新或切回会话后接管 `queued/pending/running` 任务；支持 cancel、terminal 状态与 reconnect。
- Debug：Memory/RAG 召回质量、距离、来源筛选与安全摘要。
- Governance：模型设置、provider/source/tool registry diagnostics、task queue diagnostics、审计日志、知识库版本/文档组与 shared 权限。
- Export：任务与会话 JSON / Markdown；Trace 与结果摘要可回放。

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台编排。
- `app/components/workbench/inspector.tsx`：Trace 与 Context 面板。
- `app/components/workbench/chat-column.tsx`：消息与流式 assistant 展示。
- `app/components/workbench/trace-flow-view.tsx`：Trace 流程图。
- `app/components/workbench/model-settings-modal.tsx`：模型设置与校验。
- `app/components/workbench/runtime-debug-modal.tsx`：Memory/RAG 调试。
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库治理。
- `app/tasks/[taskId]/page.tsx`：任务详情与导出。
- `app/globals.css` 与 `app/styles/`：全局样式 facade 与主题样式模块。
- `lib/stores/chat-stream-store.ts`：SSE 分发与 Trace 状态。
- `lib/stores/chat-stream-store-utils.ts`：tool meta、preview/output/result-summary 归一化。
- `lib/api-client.ts`：Bearer、refresh token 与 REST 请求。

## SSE / 回放契约

- 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- `trace.step` 与后端 `TraceStep` 同构；`tool_start/tool_end` 与 action 节点通过 `step_id` 对齐。
- Workbench 使用 `trace/delta` 做静默增量刷新，流结束后补拉最终快照。
- 前端不新增 provider 专用显示分支；result summary、safe output、failure hint 与 diagnostics 使用后端统一语义。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

默认监听 `127.0.0.1:3001`，可用 `NEXT_PUBLIC_API_BASE_URL` 指向后端。详细 e2e 与提权流程以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。
不启动服务的前端门禁可从仓库根目录运行 `bash scripts/ci_run_release_gate.sh --phase frontend`；PR/CI 默认使用 `--phase auto` 按改动范围选择阶段。发布候选的 service-backed smoke/full e2e 范围以 `bash scripts/ci_release_readiness_matrix.sh --format markdown` 为准。
