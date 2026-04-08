# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 项目搭建`：

- backend 已具备 mock chat、最小 SSE、SQLite 持久化与读取接口
- frontend 已具备 settings、JSON chat；SSE 由 `useChatStreamStore`（Zustand）承载 token/trace 与拉流逻辑
- 下一步（仍属 W1）：补齐与主计划一致的 API 形态（如 `POST /api/tasks` + `GET .../stream`）或先做 trace 全量 Replay 只读联调，二选一、每次一小步

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

建议下一小步（择一）：**A)** 后端增加 `GET /api/tasks/{task_id}/trace` 与前端「拉取上一轮 trace」按钮；**B)** 将任务创建与 SSE 路径改为计划中的 `POST /api/tasks` + `GET /api/tasks/{id}/stream`（与当前 `POST /api/chat/stream` 并存迁移）。
