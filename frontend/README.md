# Frontend

当前已经建立最小 Next.js App Router 骨架。

## 当前已有内容

- `package.json`、`tsconfig.json`、`next.config.ts`
- `app/layout.tsx`、`app/page.tsx`
- `app/globals.css`
- `app/components/workbench.tsx`：最小 settings/chat/SSE 联调页面
- `lib/stores/chat-stream-store.ts`：最小 Zustand SSE / trace store
- `lib/sse/parse.ts`：最小 SSE block 解析

## 当前边界

- Workbench 通过 `useChatStreamStore`（Zustand）消费 `POST /api/chat/stream`，展示 token 与 trace
- 当前已支持加载 `GET /api/tasks/{task_id}/trace` 做已落库 trace 回放
- 当前已支持消费 SSE `error` 事件并显示错误信息
- 尚未接入 React Flow（计划 W2）
- 尚未接入 `trace/delta` 做断线补包

## 下一步

与根目录 README 保持一致：下一步只接 `trace/delta`，让前端在已有 SSE 基础上补齐最小增量拉取能力。
