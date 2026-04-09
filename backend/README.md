# Backend

基于 FastAPI 的 W1 最小后端：配置、SQLite、会话/任务/消息持久化、SSE Task Stream、Mock Provider。

## 当前已有内容

- `app/config.py`：统一读取环境变量与默认配置
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta`（Pydantic，与主计划及前端 `TraceStepPayload` 对齐）；`GET /api/tasks/{id}/trace` 与 `trace/delta` 的 `steps` 经 `parse_trace_steps` 校验后输出，OpenAPI 文档显式展示结构
- `app/api/routes/`：健康检查、会话、设置、任务路由
- `app/db.py`：SQLite 初始化、配置表与最小业务表结构
- `app/providers/`：Provider 抽象与 mock 实现
- `app/services/chat_persistence_service.py`：会话 / 任务 / 消息持久化
- `app/services/chat_execution_service.py`：SSE Task Stream；Mock 下持久化 trace 含 **planning → tool_call（`meta.tool`）→ rag_retrieval（`meta.rag`）→ final_answer** 四步，供前端流程图展示 **工具 / RAG** 节点
- `app/services/settings_service.py`：settings 读写
- `app/services/provider_service.py`：按 settings 解析当前 provider
- `app/services/chroma_status.py`：对 Chroma HTTP 做心跳探测（供 `/health` 使用）
- `app/services/chroma_memory_service.py`：通过 **chromadb.HttpClient** 维护会话 **memory_{session_id}**（`get_or_create`、**add**、**query**、任务成功后 **best-effort 写入摘要**）；**status** 仍用只读 `get_collection` + **count**
- 环境变量 **`CHROMA_HOST`** / **`CHROMA_PORT`** / **`CHROMA_PROBE`**：见仓库根 `docker-compose.yml` 与 `.env.example`

### HTTP 接口（摘要）

- `GET /health`：健康检查、运行模式摘要、**`chroma.url` 与 `chroma.reachable`**（由 `CHROMA_PROBE` 控制是否探测）
- `POST /api/sessions`：创建会话（可选 `title`）
- `GET /api/sessions`：最近会话列表（`limit`）
- `GET /api/sessions/{session_id}`：单个会话
- `PATCH /api/sessions/{session_id}`：更新会话标题（`{ "title": "..." }`）
- `DELETE /api/sessions/{session_id}`：删除会话（204）
- `GET /api/sessions/{session_id}/messages`：会话及消息列表
- `GET /api/sessions/{session_id}/memory/status`：Chroma 中 `memory_{session_id}` 是否已建 collection、**document_count**（依赖 `chromadb` 客户端与可连通的 Chroma 服务）
- `POST /api/sessions/{session_id}/memory/add`：正文 `{ "text": "...", "metadata": { ... } }`（**metadata** 可选，字符串键值，与 Chroma document metadata 对齐），写入一条向量文档并返回 **added_id**、**document_count**（503 表示 Chroma 不可达等）
- `POST /api/sessions/{session_id}/memory/query`：正文 `{ "text": "...", "n_results": 4 }`，语义检索，返回 **ids** / **documents** / **distances**（collection 不存在或为空时返回空列表）
- `GET /api/settings` / `PUT /api/settings`：非敏感设置摘要与写入骨架
- `POST /api/tasks`：创建任务（`session_id`、`user_input` 等）
- `GET /api/tasks`：最近任务列表
- `GET /api/tasks/{task_id}`：单个任务
- `GET /api/tasks/{task_id}/stream`：任务 SSE（仅 `pending` 等允许的状态）
- `GET /api/tasks/{task_id}/trace`：trace 全量回放
- `GET /api/tasks/{task_id}/trace/delta?after_seq=`：trace 增量

## 本地启动

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如需自定义配置，可复制 `.env.example` 为 `.env` 后修改。

**Chroma（可选）**：在仓库根执行 `docker compose up -d chroma`，默认 **`http://127.0.0.1:8001`**；再访问 `/health` 确认 `chroma.reachable` 为 `true`。

## 流式与持久化（现状）

- 流式入口：`POST /api/tasks` + `GET /api/tasks/{task_id}/stream`；仅 Mock Provider，不做真实远端调用
- SSE 事件类型包含 `start`、`state`、`trace`、`heartbeat`、`token`、`done`、`error`（及任务关联字段）
- 任务结束后最小落库 `sessions` / `tasks` / `messages`；支持按 `session_id`、`task_id` 查询及 trace / delta 读取
- `prompt` 中含 `[mock-error]` 时可触发一次 mock SSE error，便于联调

## 下一步（与仓库根目录 README 一致）

- 后端 **Memory ingest（add）与 query** 最小 API，并在业务流中占位调用
- 可选：为 SSE 事件体补充与 REST 对齐的文档或共享 schema
- 保持 SSE 与 trace REST 契约稳定；trace 数据结构继续服务于 W2 可视化

## 当前限制

- `api_key` 仅最小存储骨架，未加密
- `remote` 模式等对 provider 的校验仍较粗
- 未做远端连通性检测
- `trace/delta` 以落库读取为主，流式过程中实时增量持久化仍有限
- 未实现 `tool_start/tool_end`、真实 usage、完整分页列表等

## 当前数据库结构（摘要）

- `sessions`：`id` / `title` / 时间戳等
- `tasks`：`prompt` / `status` / `trace_json` 等
- `messages`：按 `session_id` 归属，可选 `task_id`
- `trace_json` 中为标准化 step 数组，含 `seq` 等字段；REST 响应中的 `steps` 使用 `TraceStep` 模型校验与文档化