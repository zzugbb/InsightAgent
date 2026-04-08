# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 收口阶段`：

- backend 已具备 mock chat、Task Stream、SQLite 持久化、`POST /api/tasks` 与 `GET /api/tasks/{task_id}/stream`、trace 全量回放与 delta
- frontend 已具备 settings、Task Stream token/trace 展示、最近会话列表、会话消息查看、最近任务列表，以及 trace 全量回放 / delta 补包按钮；`POST /api/chat` 仅保留为最小非流式调试入口
- 当前流式事件已支持 `start/state/trace/heartbeat/token/done/error`
- 当前开发策略保持不变：每次只推进一个小能力，先把 W1 主链路与补链路收口

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
├── data/
└── .cursor/plans/
```

## 当前约束

- 暂时不接真实 API
- 默认按 `mock` 模式开发
- 每次只推进一个小阶段，避免并行任务过多

## 下一步

下一步只做一件事：在当前 session / message / task 都已可见的基础上，评估是否进入 W2 的 trace 可视化准备。
