# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 收口阶段`：

- backend 已具备 mock chat、最小 SSE、SQLite 持久化、trace 全量回放与 delta 骨架
- frontend 已具备 settings、JSON chat、SSE token/trace 展示，以及已落库 trace 回放按钮
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

下一步只做一件事：前端接入 `GET /api/tasks/{task_id}/trace/delta?after_seq=`，把 SSE 实时流和 HTTP 增量补包串起来，完成 W1 到 W2 之间的最小过渡。
