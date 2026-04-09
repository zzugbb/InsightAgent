# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 收口阶段`：

- backend 已具备 Task Stream、SQLite 持久化、`POST /api/tasks` 与 `GET /api/tasks/{task_id}/stream`、trace 全量回放与 delta（Mock Provider）
- frontend 为聊天型 Agent 主界面：左侧最近会话、中间消息流与单一「发送」入口、右侧轨迹与上下文；运行设置从侧栏进入
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

下一步只做一件事：在当前聊天型 Agent 主界面已稳定承载 session / message / task / trace 的基础上，继续整理 trace 区块的数据结构，为 W2 的可视化视图做准备。
