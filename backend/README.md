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
  - `extra_tools` / registry `overrides` 现可直接声明 `execution.kind=http_json` 的真实执行器；provider/real tool 已不必再只靠模板 runner 做语义换壳，HTTP JSON 返回的 `documents_total/request_id/chunks/result` 等字段会继续沿 preview/output/result-summary、observation、rag follow-up 与 export 主链复用。
  - configured provider preflight 与 settings summary/validate 返回的 `tool_details` 现也显式包含 `execution_kind`；file/source 治理与前端设置面板可以直接识别哪些 tool 已切到真实 `http_json` runner。
  - 若 registry `extra_tools` / `overrides` 显式声明了 `execution`，但 `kind` 缺失、shape 非法或写成不支持的执行器，tool runtime 现会直接返回配置错误，不再静默回退到模板 stub runner。
  - 同一批坏掉的 `execution` 配置现在也会进入 `invalid/tool_executions` diagnostics：file/source/global settings、selected source、configured provider preflight 以及 trace/audit 可以在真正跑 tool 之前就把问题暴露出来，而不是只在运行期 fail-fast。
  - 对已接上 `http_json` 的 real tool，runtime 现在还会生成一份安全的 `execution_summary` 并挂到 tool semantic meta 上；`tool_start`、action step、持久化 trace 与 export 回放都能看到 method、origin/path、query/body/result-field 概览，同时避免把 header value 等敏感配置直接写进 trace。
  - `http_json` execution template 现在也会复用运行时 settings/source 上下文：global extra tool、source extra tool、registry override 与 file-backed source 都可以在 `headers/url/query/json_body` 中读取 `settings_api_key`、`settings_base_url`、`tool_registry_provider_source` 等变量，并支持 `${...}` 字符串插值来拼接 bearer/header 模板，而无需把敏感值硬编码进 registry 配置。
  - file-backed source manifest 里的 `extra_tools` / `overrides` 现也继续走同一套 source 级模板上下文传递；把 source 从内联 JSON 切到 `registry_file` 后，`tool_registry_provider_source` 一类运行时变量不会再丢失。
  - 对 `http_json` 模板中的保留命名空间变量，runtime 现在也会做更细粒度静态诊断：`settings_*` / `tool_registry_*` typo 会直接落进 `invalid_tool_executions`，并在 runner 构建时继续 fail-fast，而不是静默丢掉 header/query 参数后才在真实上游请求里暴露成旁路错误。
  - 前端 workbench 的 trace subtitle/search 现也开始消费这份 `execution_summary`；后端这边输出的安全执行摘要已经不再只停留在 JSON trace/export 里，而是能直接参与 UI 回放与检索。
  - configured provider preflight、settings summary/validate 的 `tool_details` 现在也继续带上 `execution_summary`；真实工具的 endpoint 与 query/body/response-field 摘要已经不再只存在于运行期 trace，settings 治理面就能先读到。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 与 retrieval follow-up 已贯通 action step、`tool_start/tool_end`、persisted trace、export 与 mock final answer。
  - real/provider retrieval 与 runtime override real tool 已不再在 result summary、observation、rag follow-up 或 task export 中伪造默认本地 knowledge-base 语义。
  - name-only success/helper fallback 会优先复用 configured registry 或 step meta 中已落下的 label / result summary / output preview，而不是退回 provider 通用名或原始 JSON；即使原始 `output` 未保留成 dict，observation、success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 聚合仍会优先沿 step meta 或 typed payload 的结构化结果回放；会话 Memory query、RAG ingest/query、RAG route 层与 shared knowledge-base merge 的 metadata、query payload root、document row、row list，以及 session create/detail/list/messages/export、task/session usage、task create/detail/list/cancel/trace/delta/export/stream-reconnect、auth register/refresh/session list/user list、audit log list 这些 outward summary route，以及 `chat_persistence_service` 的 task trace/usage/response/export/delta、`task_rows_*` 批量聚合 helper、task/session export response summary 外层 payload，以及 task/session export builder 路由入口，也已接受 typed Chroma / typed service payload / `model_dump()` 行，不再在归一化阶段静默清空或直接报错，nested metadata 也会继续保留。
  - runtime helper、governance/export、registry diagnostics 与 planner 输入归一化已统一兼容旁路结构化载荷；当前 provider planner 与真实 `OpenAICompatibleLLMProvider` 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`835/835`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts` 通过（`29/29`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`4/4`）
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
- 当前 registry extra tool / override 的真实执行器入口先以 `execution.kind=http_json` 为主；请求模板、响应字段映射与既有 runtime semantic/preview/export 主链保持同一契约，不额外发散独立 route。
- 显式给 tool 配了 `execution` 时，当前语义是“宁可报配置错，也不回退 stub”；这样 provider/source 治理不会把 real tool 假阳性地跑成本地模板行为。
- provider/source/global settings 侧当前也会把静态可判定的 `execution` 坏配置归一成 registry diagnostics；下一步优先继续补更细粒度的模板/映射诊断，而不是改外层接口。

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
