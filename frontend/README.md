# Frontend

当前已经建立最小 Next.js App Router 骨架。

## 当前已有内容

- `package.json`、`tsconfig.json`、`next.config.ts`
- `app/layout.tsx`、`app/page.tsx`
- `app/globals.css`
- `app/components/workbench/`：聊天型 Agent 主界面（侧栏、对话区、检查器拆分）
- `lib/stores/chat-stream-store.ts`：最小 Zustand Task Stream / trace store
- `lib/sse/parse.ts`：最小 SSE block 解析

## 当前边界

- 聊天型 Agent 主界面通过 `useChatStreamStore`（Zustand）消费 `POST /api/tasks` + `GET /api/tasks/{task_id}/stream`
- 当前页面为左侧最近会话、中间消息流与单一发送入口、右侧「轨迹 / 上下文」与侧栏「运行设置」
- 当前已显示最近会话列表，并允许切换 active session
- 当前已支持按 active session 加载并展示已落库消息历史，作为主消息流的基础形态
- 当前任务信息已下沉到右侧上下文面板，并可直接回放选中 task 的 trace
- 当前已支持加载 `GET /api/tasks/{task_id}/trace` 做已落库 trace 回放
- 当前已支持消费流式 `error` 事件并显示错误信息
- 当前已支持加载 `GET /api/tasks/{task_id}/trace/delta?after_seq=` 做最小增量补包
- 运行设置：左下角「设置」菜单（主题 / 语言 / 模型与运行弹窗）；`/settings` 会重定向首页；右栏仅「轨迹 / 上下文」
- 数据请求使用 **TanStack Query**（去重、聚焦刷新、流式结束后 invalidate）
- 侧栏支持「新会话」；无选中会话时发送会先 **POST /api/sessions** 再跑任务流
- 助手消息使用 **react-markdown + remark-gfm + rehype-sanitize**（GFM 表格/列表等，外链新标签打开）
- 窄屏：左侧 **会话抽屉** + 右侧 **轨迹抽屉**，独立遮罩，**焦点陷阱** 与 Esc 关闭
- 消息列表超过约 24 条时 **虚拟列表**；会话超过 14 条时侧栏虚拟化
- 轨迹默认仅展示最近 6 步，可「展开全部」；流式失败展示「未落库」提示与 **aria-live** 摘要
- **⌘K / Ctrl+K** 聚焦输入框；文案集中在 `lib/i18n/zh.ts`，错误映射在 `lib/errors.ts`
- 尚未接入 React Flow（计划 W2）

## 下一步

与根目录 README 保持一致：下一步先整理 trace 区块的数据结构与展示层，为 W2 的可视化视图做准备。
