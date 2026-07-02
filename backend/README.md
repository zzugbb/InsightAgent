# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前状态

- W1-W4 主链路已完成并收口。
- 阶段 5 已完成的基础能力包括：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时、`RBAC-lite`、`rag-rbac-lite`、任务取消/超时、running task 恢复支撑、任务/会话导出、usage dashboard、审计事件扩展。
- 当前活跃主线不再是 `tool-runtime-productionization` 文档化收口，而是：
  - 默认工具去 mock 化
  - 真实工具接入
  - `tool registry / profile / provider source` 治理产品化
  - extra/real tool 在执行本体、trace、observation、result preview、export 语义上的真实化
- 最近已对齐到代码的高信号能力：
  - 默认 canonical tool 名已统一到 `task_plan / task_retrieve`，`mock_*` 仅保留兼容 alias；planner 已能规划 real/extra tools 与动态 registry/source 候选。
  - provider / provider source 已支持 `loader_factory`，tool-registry diagnostics 已进入 entry 级 trace/export/preflight 语义，settings、selected source 与 runtime artifacts 使用同一治理主干。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 与 retrieval follow-up 已贯通 action step、`tool_start/tool_end`、persisted trace、export 与 mock final answer。
  - real/provider retrieval 与 runtime override real tool 已不再在 result summary、observation、rag follow-up 或 task export 中伪造默认本地 knowledge-base 语义。
  - name-only success/helper fallback 会优先复用 configured registry 或 step meta 中已落下的 label / result summary / output preview，而不是退回 provider 通用名或原始 JSON。
  - runtime helper、governance/export、registry diagnostics 与 planner 输入归一化已统一兼容旁路结构化载荷；当前 provider planner 已支持结构化 `dict/list/tuple`、单工具对象、content-part 文本响应，以及带 `content/usage` 或顶层 `tools/usage` 的 response envelope，并兼容 `input_tokens/output_tokens` usage alias 与脏 usage 值容错。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`729/729`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`39/39`）
  - `cd frontend && npm run lint` 通过
  - `bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `git diff --check` 通过

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- `app/providers/`：provider 抽象、mock provider、OpenAI-compatible remote provider
- `app/services/chat_execution_service.py`：任务流编排与 SSE 主链
- `app/services/tool_runtime.py`：tool registry / provider / source、tool runtime helper、preflight、diagnostics、result preview/output/summary 语义
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/chroma_rag_service.py`：RAG ingest/query/status、knowledge base list/clear/delete 与 shared/private 语义
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 usage，供任务列表、导出与 dashboard 复用

## HTTP 接口（摘要）

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- `GET /api/auth/users`（admin only）
- `GET /api/auth/me`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/export/json`
- `GET /api/sessions/{session_id}/export/markdown`
- `GET /api/sessions/{session_id}/memory/status`
- `GET /api/sessions/{session_id}/usage/summary`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=&query=`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`
- `GET /api/tasks/usage/summary`
- `GET /api/tasks/usage/dashboard`
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/query`
- `GET /api/rag/knowledge-bases`
- `POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}`

补充约定：

- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`。
- `GET /api/tasks*` 相关响应包含 `status_normalized`、`status_label`、`status_rank`。
- usage 接口支持来源维度统计：`provider / estimated / mixed / legacy`。
- `shared-*` 知识库走共享命名空间；admin 可写，普通用户只读。

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：

- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `cancelled`
- `timeout`
- `done`
- `error`

对齐说明：

- `event: trace` 的 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。
- `tool_start/tool_end` 使用与 action 节点一致的 `step_id`，与 trace 节点一一对齐。
- `trace/delta?after_seq=` 可在任务流式进行中拉取阶段性 `observation` 刷新内容。
- remote provider 异常会被归一成结构化错误码，并在 SSE `error` 中透传稳定的 `code / fatal / retryable / detail / status_code`。

## 当前实现边界

- `trace/delta` 支持 `limit` 参数控制单次增量返回量；当前默认 `200`，最大 `500`。
- `GET /api/tasks/usage/summary` 与 `GET /api/tasks/usage/dashboard` 都已支持 usage 来源统计；当前来源语义是 `provider / estimated / mixed / legacy`。
- 任务相关对外读取已优先走 task row 上的规范化治理摘要与 parsed trace 主干，不再鼓励在 route 层继续做 sibling fallback。
- 默认 settings 语义是：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`；remote `base_url/api_key` 继承链已打通到 get/save/validate。
- shared RAG 语义当前保持 `shared-*` 命名空间约定：admin 可写共享库，普通用户对共享库只读。
- 当前后端主线优先补真实工具执行与 registry-aware helper 语义，不优先继续扩写 archived runtime spec。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- RAG collection 命名：`kb_{user_hash}_{knowledge_base_id}`
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务后的摘要写入为 best-effort

### 通俗分工（后端视角）

- `PostgreSQL`：业务主存储，保存用户、会话、消息、任务、trace、usage、设置、审计。
- `Chroma Memory`：会话级语义记忆，服务当前对话上下文。
- `Chroma RAG`：知识库级文档检索，服务跨会话复用的资料。

## 本地启动

推荐使用 **Python 3.14**（与 `compose.full.yml`、根目录 `.python-version`、CI 保持一致）。

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

如需将历史 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

常用校验：

```bash
python scripts/e2e_baseline.py --base-url http://127.0.0.1:8000
python scripts/e2e_main_path.py --base-url http://127.0.0.1:8000
python scripts/e2e_export_consistency.py --base-url http://127.0.0.1:8000
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout
backend/.venv/bin/python scripts/test_tool_runtime_slice.py
```

如需 Memory / RAG 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

当前常用运行参数：

- `TRACE_PERSIST_MIN_INTERVAL_SEC`：trace 增量持久化最小间隔
- `STREAM_RECONNECT_POLL_FAST_SEC`：running reconnect 快轮询间隔
- `STREAM_RECONNECT_POLL_MAX_SEC`：running reconnect 慢轮询上限
- `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`：reconnect heartbeat 间隔
- `TASK_TIMEOUT_SEC`：任务超时秒数

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- 当前主线优先真实工具执行语义，不优先继续维护已归档的 runtime spec 历史文档。
- 文档只保留高信号当前状态，不继续累积按天流水账。
