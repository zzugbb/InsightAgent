# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，当前按 `.cursor` 主计划逐步开发。

## 当前阶段

当前处于 **`W1 已收口` / `W2 启动`**：

- **backend**：Task Stream、SQLite 持久化、`POST /api/tasks` 与 `GET /api/tasks/{task_id}/stream`、trace 全量回放与 delta（Mock Provider）；**`GET .../trace` / `trace/delta` 响应已用 Pydantic `TraceStep` / `TraceStepMeta` 显式建模（OpenAPI 与前端类型对齐）**；**`GET /health` 含 Chroma 连接信息与可达性**；**Memory**：**`GET .../memory/status`** 只读条数；**`POST .../memory/add`**、**`POST .../memory/query`** 最小写入与检索；任务成功结束后 **best-effort** 写入一条会话摘要（需 Docker Chroma 可连）；会话支持创建 / 列表 / 详情 / 消息 / **重命名（PATCH）** / **删除（DELETE）**
- **frontend**：聊天型 Agent 工作台——左侧最近会话、中间消息流与单一「发送」入口、右侧「轨迹 / 上下文」；运行设置从侧栏进入；**桌面端**左栏与右栏均可 **拖拽调宽、折叠窄条展开**，侧栏会话支持 **重命名 / 删除**；站点 **图标与品牌区** 已接入；右侧轨迹支持 **时间线 / 流程图** 切换（`@xyflow/react`：**自定义 traceStep 节点**（thought/action/observation 配色 + 元信息 + 可折叠内容摘要））；**「上下文」Memory 区展示 Chroma 已连接/未连接、collection 是否存在、向量条数**（随选中会话拉取 `/memory/status`）
- 当前流式事件已支持 `start/state/trace/heartbeat/token/done/error`
- 当前开发策略保持不变：每次只推进一个小能力，先把 W1 主链路与补链路收口

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
├── data/
├── docker-compose.yml   # Chroma 服务（可选）
└── .cursor/plans/
```

## Docker（Chroma，可选）

仓库根目录提供 **`docker-compose.yml`**，默认将 Chroma 映射到宿主机 **8001**：

```bash
docker compose up -d chroma
```

后端默认连接 **`http://127.0.0.1:8001`**（可在 `backend/.env` 中修改 `CHROMA_HOST`、`CHROMA_PORT`）。启动 Chroma 后，`GET http://127.0.0.1:8000/health` 中 `chroma.reachable` 应为 `true`（未启动时为 `false`）。ingest/检索 API 仍待后续迭代。

## 当前约束

- 暂时不接真实 API
- 默认按 `mock` 模式开发
- 每次只推进一个小阶段，避免并行任务过多

## 下一步

**Memory** 已具备 **`/memory/add`**、**`/memory/query`** 与任务结束 **自动写入摘要**；后续可接：与业务字段对齐的 metadata、独立 embedding 配置、流程图侧 **工具 / RAG** 节点；可选为 SSE `trace` 载荷补充与 REST 同构的 schema 说明。工作台交互类需求以不阻塞主链路为前提迭代。