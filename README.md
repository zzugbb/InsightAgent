# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 收口阶段`：

- backend 已具备 mock chat、最小 SSE、SQLite 持久化、`POST /api/tasks` 与 `GET /api/tasks/{task_id}/stream` 骨架、trace 全量回放与 delta 骨架
- frontend 已具备 settings、JSON chat、SSE token/trace 展示，以及 trace 全量回放 / delta 补包按钮；SSE 入口已切到 task 形态
- SSE 当前已支持 `start/state/trace/heartbeat/token/done/error`
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

下一步只做一件事：收口旧接口，评估是否让前端 trace 回放 / delta / SSE 全部以 task 形态为主，并开始减少对 `POST /api/chat/stream` 的依赖。
