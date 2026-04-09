# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 `W1 / 收口阶段`：

- **backend**：Task Stream、SQLite 持久化、`POST /api/tasks` 与 `GET /api/tasks/{task_id}/stream`、trace 全量回放与 delta（Mock Provider）；会话支持创建 / 列表 / 详情 / 消息 / **重命名（PATCH）** / **删除（DELETE）**
- **frontend**：聊天型 Agent 工作台——左侧最近会话、中间消息流与单一「发送」入口、右侧「轨迹 / 上下文」；运行设置从侧栏进入；**桌面端**左栏与右栏均可 **拖拽调宽、折叠窄条展开**，侧栏会话支持 **重命名 / 删除**；站点 **图标与品牌区** 已接入
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

在聊天型主界面已稳定承载 session / message / task / trace 的基础上，继续 **整理 trace 区块的数据结构与展示层**，为 W2 的可视化视图做准备；工作台交互类需求以不阻塞主链路为前提迭代。