# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand 的 Agent 工作台前端。

## 当前进度

- W1：已完成
- W2：已完成（进入收尾）
- W3/W4：未开始（真实工具 / RAG）

## 当前已有内容

- 三栏布局：会话、消息、轨迹/上下文
- 会话：创建、切换、分页加载、重命名、删除
- 轨迹：时间线与流程图双视图（thought/action/observation/tool/rag 区分）
- 流式：SSE 任务状态、token 追加、trace 实时更新
- 回放：`trace` 全量与 `trace/delta` 增量加载
- usage 展示：支持当前任务、任务列表摘要；汇总由后端 `GET /api/tasks/usage/summary` 驱动（全局/会话自动切换），并具备 loading/error/empty 状态与统计覆盖率展示
- Memory：状态展示 + add/query 调试（含 metadata）
- 设置：主题、主题色、语言、模型与运行模式
- 工程校验：已配置 `.eslintrc.json`，`npm run lint` 可直接运行且当前告警已清零

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/types/trace.ts`：前端 TraceStep 类型
- `lib/api-client.ts`：REST 请求封装

## SSE 消费与契约对齐

当前前端按以下事件消费：
- `start`
- `state`
- `trace`
- `heartbeat`
- `token`
- `done`
- `error`

`trace` 事件中的 `step` 与后端 REST `TraceStep` 同构，`dispatchSseEvent`（`lib/stores/chat-stream-store.ts`）为当前权威消费路径。

## Memory（会话级）

- collection 规则：`memory_{session_id}`
- 状态读取：`GET /api/sessions/{session_id}/memory/status`
- 写入调试：`POST /api/sessions/{session_id}/memory/add`
- 检索调试：`POST /api/sessions/{session_id}/memory/query`

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端（未设置时使用 `http://127.0.0.1:8000`）。

## 下一步（W2 收尾）

- 配合后端接入真实工具/RAG 后补齐流程图语义
- 继续完善 usage/token/cost 的统计维度（跨会话/时间段聚合）
- 继续做不阻塞主链路的可访问性与交互细化
