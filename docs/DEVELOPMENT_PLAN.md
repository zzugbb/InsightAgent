# InsightAgent 开发计划与里程碑

本文档与仓库根目录 `README.md`、`backend/README.md`、`frontend/README.md` 同步维护；个人本地若使用 Cursor，可在 `.cursor/plans/` 下保留副本或链接至本文件（`.cursor/` 默认被 `.gitignore` 忽略，**不以该目录为唯一进度来源**）。

---

## 里程碑定义

### 里程碑 1 — W1 主链路收口

**目标**：端到端可跑的「会话 → 任务 → SSE 流式 → 落库 → 回放」与基础工作台。

**验收要点（已完成）**

- 后端：`POST /api/tasks`、`GET /api/tasks/{id}/stream`、SQLite 会话/任务/消息、`GET .../trace` 与 `trace/delta`、Mock Provider、`TraceStep` / `TraceStepMeta` OpenAPI 建模。
- 前端：侧栏会话、消息流、发送入口、Inspector 轨迹、设置、主题/语言、流式状态与 trace 回放。

**状态**：**已完成**

---

### 里程碑 2 — W2 核心：可观测轨迹 + Memory 最小闭环

**目标**：轨迹可区分「思考 / 行动 / 观察 / 工具 / RAG」，并具备会话级向量 Memory 的读写与可观测状态；任务列表与会话联动可靠。

**验收要点（已完成）**

| 域 | 内容 |
|----|------|
| 轨迹 | 时间线 + 流程图；`meta.tool` / `meta.rag` 与类型映射；Mock 四步 trace（planning → tool → rag → final）；时间线卡片左侧色条与流程图配色一致。 |
| Memory | Chroma `memory_{session_id}`；`GET .../memory/status`；`POST .../memory/add`（可选 metadata）；`POST .../memory/query`（含 **metadatas**）；任务成功 **best-effort** 摘要写入；Inspector 调试区与 i18n。 |
| 任务 | `GET /api/tasks?session_id=` 按会话筛选；任务列表 404 时清空选中并提示；Inspector「本会话任务」标题。 |
| 健康 | `/health` 含 Chroma 可达性（可选 Docker Compose）。 |

**状态**：**已完成**（当前代码库已满足上表）

---

## W2 收尾（后续迭代，不阻塞里程碑 2）

以下项在里程碑 2 之后按需推进，用于 **W2 正式收尾** 或进入下一阶段：

1. **Embedding / 模型**：**初版说明已完成** — 见 **[`MEMORY_CHROMADB.md`](MEMORY_CHROMADB.md)**（连接方式、嵌入由 Chroma Server 默认承担、当前 API 边界与后续独立配置注意点）。
2. **契约文档**：**初版已完成** — 见 **[`SSE_AND_TRACE_CONTRACT.md`](SSE_AND_TRACE_CONTRACT.md)**（SSE 事件表 + 与 REST `TraceStep` 对齐说明）。后续可在 OpenAPI 中嵌入更多示例或生成 Typescript。
3. **真实工具 / RAG**：替换或并行于 Mock 的 tool/rag 步骤（含错误与重试语义）。
4. **工程化**：`trace/delta` 流式过程中实时增量持久化、usage 计费字段等（见 `backend/README.md`「当前限制」）。**列表分页**：`GET /api/sessions`、`GET /api/tasks` 支持 **`limit`+`offset`**，响应含 **`total` / `has_more`**。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-04-09 | 初版：里程碑 1/2 定义与 W2 收尾清单；里程碑 2 标为已达成交付。 |
| 2026-04-09 | 增补 `SSE_AND_TRACE_CONTRACT.md`；W2 收尾第 2 项记为初版完成。 |
| 2026-04-09 | 增补 `MEMORY_CHROMADB.md`；W2 收尾第 1 项记为初版完成。 |
| 2026-04-09 | 会话/任务列表 API 增加 `offset` 分页参数。 |
| 2026-04-09 | 列表响应增加 `total`、`limit`、`offset`、`has_more`。 |
