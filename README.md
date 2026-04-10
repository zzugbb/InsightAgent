# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台。**进度与里程碑以仓库内 [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) 为准**（本地 `.cursor/plans` 可自建，但不作为唯一来源）。**SSE 与 TraceStep 对照**见 [`docs/SSE_AND_TRACE_CONTRACT.md`](docs/SSE_AND_TRACE_CONTRACT.md)；**Memory / Chroma / 嵌入**见 [`docs/MEMORY_CHROMADB.md`](docs/MEMORY_CHROMADB.md)。

## 当前阶段

**里程碑 1（W1 主链路）**：已完成。  
**里程碑 2（W2 核心：可观测轨迹 + Memory 最小闭环）**：**已达到** — 详见 [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)。后续工作以 **W2 收尾**（embedding/契约文档/真实工具 RAG 等）为主。

当前能力摘要：

- **backend**：Task Stream、SQLite 持久化、`POST /api/tasks`、`GET /api/tasks`（可选 **`session_id`** 按会话筛任务）与 `GET /api/tasks/{task_id}/stream`、trace 全量回放与 delta（Mock Provider）；**`GET .../trace` / `trace/delta` 响应已用 Pydantic `TraceStep` / `TraceStepMeta` 显式建模（OpenAPI 与前端类型对齐）**；**`GET /health` 含 Chroma 连接信息与可达性**；**Memory**：**`GET .../memory/status`** 只读条数；**`POST .../memory/add`**、**`POST .../memory/query`** 最小写入与检索；任务成功结束后 **best-effort** 写入一条会话摘要（需 Docker Chroma 可连）；会话支持创建 / 列表 / 详情 / 消息 / **重命名（PATCH）** / **删除（DELETE）**
- **frontend**：聊天型 Agent 工作台——左侧最近会话、中间消息流与单一「发送」入口、右侧「轨迹 / 上下文」；运行设置从侧栏进入；**桌面端**左栏与右栏均可 **拖拽调宽、折叠窄条展开**，侧栏会话支持 **重命名 / 删除**；站点 **图标与品牌区** 已接入；右侧轨迹支持 **时间线 / 流程图** 切换（`@xyflow/react`：**自定义 traceStep 节点**，含 **工具 / RAG** 与 thought/action/observation 区分配色 + 元信息 + 可折叠内容摘要）；**「上下文」Memory** 含状态与 **add/query 调试**（含 metadata、命中 **metadatas**）；任务列表支持 **本会话筛选** 与 **会话失效提示**
- 当前流式事件已支持 `start/state/trace/heartbeat/token/done/error`
- 开发策略：小步迭代；**W2 收尾**阶段优先补齐文档与可选工程项（见 [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)）

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
├── data/
├── docker-compose.yml   # Chroma 服务（可选）
├── docs/
│   ├── DEVELOPMENT_PLAN.md        # 里程碑与 W2 收尾清单
│   ├── SSE_AND_TRACE_CONTRACT.md  # SSE 事件与 REST TraceStep 对齐说明
│   └── MEMORY_CHROMADB.md         # Chroma 连接、嵌入边界与 Memory API
└── .cursor/plans/   # 可选；本地 Cursor 计划（默认 gitignore）
```

## Docker（Chroma，可选）

仓库根目录提供 **`docker-compose.yml`**，默认将 Chroma 映射到宿主机 **8001**：

```bash
docker compose up -d chroma
```

后端默认连接 **`http://127.0.0.1:8001`**（可在 `backend/.env` 中修改 `CHROMA_HOST`、`CHROMA_PORT`）。启动 Chroma 后，`GET http://127.0.0.1:8000/health` 中 `chroma.reachable` 应为 `true`（未启动时为 `false`）。Memory 的写入/检索见 **`POST .../memory/add`**、**`.../query`**。

## 当前约束

- 暂时不接真实 API
- 默认按 `mock` 模式开发
- 每次只推进一个小阶段，避免并行任务过多

## 下一步（W2 收尾）

里程碑 2 已完成；收尾阶段建议优先：**真实工具/RAG 接入**、以及 `backend/README` 中列出的工程限制项（分页、usage、`trace/delta` 实时增量等）。**Embedding / Chroma** 说明初版见 **[`docs/MEMORY_CHROMADB.md`](docs/MEMORY_CHROMADB.md)**；**SSE ↔ TraceStep** 见 **[`docs/SSE_AND_TRACE_CONTRACT.md`](docs/SSE_AND_TRACE_CONTRACT.md)**。细则与检查清单见 **[`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)**。