# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式优先，覆盖任务流、轨迹、会话持久化与会话级 Memory。

## 当前进度

- W1：已完成
- W2：已完成（进入收尾）
- W3/W4：未开始（真实工具 / RAG）
- 工程协作：前端 `npm run lint` 已可直接执行，且当前告警已清零
- 协同进展：前端已消费并格式化 `tasks.usage_json`（总 tokens / cost）

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`sessions`、`tasks`、`settings`
- `app/db.py`：SQLite 初始化与基础表
- `app/providers/`：Provider 抽象 + mock 实现
- `app/services/chat_execution_service.py`：SSE 任务流（mock 四步 trace）
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `tasks.usage_json`：任务完成时持久化 `done.usage`（前端可用于任务列表摘要展示）

## HTTP 接口（摘要）

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`（含 `total/has_more`）
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/memory/status`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=`（含 `total/has_more`）
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=`

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：
- `start`
- `state`
- `trace`
- `heartbeat`
- `token`
- `done`
- `error`

其中 `event: trace` 的 `data.step` 与 REST TraceStep 同构（`id/type/content/meta/seq?`）。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：`memory/add`、`memory/query` 返回 503；任务后的摘要写入为 best-effort

## 本地启动

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需 Memory 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

## 当前限制（W2 收尾）

- `api_key` 仅最小存储骨架，未加密
- `remote` 模式 provider 校验仍较粗
- 真实工具调用循环与真实 RAG 尚未接入
- usage/token/cost 仍是占位增强阶段
- `trace/delta` 流式中的实时增量持久化仍可继续细化
