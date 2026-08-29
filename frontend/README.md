# InsightAgent Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台。Node.js 使用 24.x。

## 当前状态

- `provider-tool-expansion` 与 `ci-release-engineering` 均已 100% 封板。
- Workbench、Task Center、任务详情、Trace/Context Inspector、Memory/RAG 调试、设置、审计、usage dashboard 与知识库治理已落地。
- 前端继续消费后端统一的 preview/output/result-summary、trace/export 字段，不新增 provider 专用显示分支。
- `app/globals.css` 已拆为 `app/styles/` 主题模块；前端源码体积边界已纳入 node 测试，生成锁文件不作为拆分对象。
- 前端 e2e workflow 覆盖 smoke/full/queue，queue 阶段使用独立 `:8011` backend；main push Playwright artifact-stage guard 使用 `fail-on-missing`。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto` 通过，Markdown/JSON summary 与 release readiness matrix 输出通过。
- Node tests：8 个测试文件，`122/122` 通过，包含 frontend source size boundary。
- `npm run lint` 与 `npm run build` 通过。
- E2E 基线：full Chromium `52 passed / 1 skipped`；低并发 queue phase `1/1` 且已纳入 CI workflow。
- Backend 契约基线：full slice `1983/1983`；module boundary `4/4`。

## 稳定契约

- SSE 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- `trace.step` 与后端 `TraceStep` 同构；`tool_start/tool_end` 与 action 节点通过 `step_id` 对齐。
- Workbench 使用 `trace/delta` 做静默增量刷新，流结束后补拉最终快照。
- result summary、safe output、failure hint 与 diagnostics 使用后端统一语义。

## 关键入口

- `app/components/workbench/index.tsx`：工作台编排。
- `app/components/workbench/inspector.tsx`、`trace-flow-view.tsx`：Trace 与 Context 可视化。
- `app/components/workbench/*-modal.tsx`：设置、runtime debug、知识库治理与审计。
- `app/tasks/[taskId]/page.tsx`：任务详情与导出。
- `lib/stores/chat-stream-store.ts` 与 `chat-stream-store-utils.ts`：SSE 分发、tool meta 与回放归一化。
- `lib/api-client.ts`：Bearer、refresh token 与 REST 请求。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

默认监听 `127.0.0.1:3001`，可用 `NEXT_PUBLIC_API_BASE_URL` 指向后端。详细 e2e 与提权流程以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。
