# Frontend

当前已经建立最小 Next.js App Router 骨架。

## 当前已有内容

- `package.json`、`tsconfig.json`、`next.config.ts`
- `app/layout.tsx`、`app/page.tsx`
- `app/globals.css`
- `app/components/workbench.tsx`：最小 settings/chat 联调页面

## 当前边界

- Workbench 通过 `useChatStreamStore`（Zustand）消费 `POST /api/chat/stream`，展示 token 与 trace
- `lib/sse/parse.ts`：SSE 帧解析；`lib/stores/chat-stream-store.ts`：流式状态与 `runChatStream`
- 尚未接入 React Flow（计划 W2）

## 下一步

与根目录 README「建议下一小步」保持一致：优先选 trace Replay HTTP 联调，或任务 API 与 SSE 路径对齐主计划。
