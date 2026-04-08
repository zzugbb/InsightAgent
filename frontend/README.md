# Frontend

当前已经建立最小 Next.js App Router 骨架。

## 当前已有内容

- `package.json`、`tsconfig.json`、`next.config.ts`
- `app/layout.tsx`、`app/page.tsx`
- `app/globals.css`
- `app/components/workbench.tsx`：聊天型 Agent 主界面骨架
- `lib/stores/chat-stream-store.ts`：最小 Zustand Task Stream / trace store
- `lib/sse/parse.ts`：最小 SSE block 解析

## 当前边界

- 聊天型 Agent 主界面当前通过 `useChatStreamStore`（Zustand）消费 `POST /api/tasks` + `GET /api/tasks/{task_id}/stream`
- `POST /api/chat` 当前只作为最小非流式调试入口保留
- 当前页面已整理为左侧最近会话、中间消息流与输入区、右侧标签面板的聊天型 Agent 结构
- 当前已显示最近会话列表，并允许切换 active session
- 当前已支持按 active session 加载并展示已落库消息历史，作为主消息流的基础形态
- 当前任务信息已下沉到右侧上下文面板，并可直接回放选中 task 的 trace
- 当前已支持加载 `GET /api/tasks/{task_id}/trace` 做已落库 trace 回放
- 当前已支持消费流式 `error` 事件并显示错误信息
- 当前已支持加载 `GET /api/tasks/{task_id}/trace/delta?after_seq=` 做最小增量补包
- 当前已将设置从首页主舞台降级到右侧标签面板
- 尚未接入 React Flow（计划 W2）

## 下一步

与根目录 README 保持一致：下一步先整理 trace 区块的数据结构与展示层，为 W2 的可视化视图做准备。
