# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前状态

- 后端 W1-W4 与阶段 5 基础产品化已完成：JWT + refresh、用户级设置与密钥加密、PostgreSQL、`RBAC-lite`、`rag-rbac-lite`、任务取消/超时、running task 恢复、导出、usage dashboard 与审计事件扩展已落地。
- `real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy` 与 `registry-governance` 均已封板；当前主线进入 `rag-governance-hardening`，进度约 `12%`；默认 settings 语义保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- `http_json` 真实执行器覆盖请求模板、鉴权/header/query/body、response_path/result_fields、常见搜索/计算/GraphQL/Elastic/OData/向量/RAG SDK 风格输出、preview/output/result-summary、trace/export/SSE/audit/settings diagnostics。
- `app/services/task_queue_service.py` 负责单进程执行槽位、queued 安全等待快照、capacity-aware oldest eligible FIFO、queued cancel 等待项移除，以及可选 per-user/per-session 并发治理。
- `GET /api/settings` 暴露只读 `task_queue_diagnostics`，typed 契约固定基础运行态、governance、pressure/waiting policy 与 optional current user/session scope 字段；不改变 SSE / trace / export payload，不暴露内部 task ids。
- `backend/scripts/test_tool_runtime_slice.py` 已拆到 `backend/scripts/tool_runtime_slice/`；`app/services/tool_runtime.py` 已拆出 planner、execution、HTTP JSON、registry 四个 facade 模块，外部 import 保持稳定。
- `tool_runtime_registry.py` 与 settings/route/audit/SSE/trace 边界已完成 provider/source 脱敏、冲突 alias、跨结构共享 alias map、runtime artifacts/service actions、模型输出层、export/task/usage/audit/SSE/trace 安全摘要。
- `rag-governance-hardening` 已完成首批收口：`chroma_rag_service.py` 在 ingest 持久化前与 query response 出站前统一规整 source/metadata 敏感信息；ingest 为每个 chunk 写入稳定 `document_version` 与 `content_hash`，同文档同内容稳定、内容变化自动换版。

## 当前验证基线

- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`：`1871/1871` 通过
- backend e2e main phase：baseline / main / export consistency / cancel-timeout 通过
- frontend type contract：`npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts` 通过
- backend queue e2e phase：低并发 `8011` 本轮 fresh 通过，覆盖 queued cancel、safe queue snapshot、settings diagnostics 与 followup completion
- frontend targeted Chromium：queued recover/cancel、running cancel、Task Center session/global 隔离、刷新恢复隔离均已通过
- `bash scripts/test_ci_e2e_tooling.sh all`：通过
- 完整 Chromium e2e：默认 `8000/3001` 本轮 fresh 通过，`50 passed / 1 skipped`
- 本轮相关 `8011/8000/3001` 服务均已停止，`lsof` 无监听残留。
- `git diff --check`：通过
- 后续运行 backend slice、启动 backend、跑 backend e2e 和提交时，先按 `../docs/development-runbook.md` 使用固定 venv 与提权边界，避免重复触发本机端口 / `.git/index.lock` 权限错误。

## 下一步后端计划

1. 已封板主线：`real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`。
2. 当前主线：`rag-governance-hardening`，进度约 `12%`；已收口 RAG source/metadata 入站持久化与 query 出站脱敏，并补入稳定文档版本/内容指纹 metadata。
3. 后续聚焦版本字段的查询/导出治理、来源策略与更细粒度 shared 规则。
4. 后续开发继续保持 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 入口、SSE / trace / export 外部契约、runbook 提权流程与单文件规模治理稳定；新增测试/实现优先落到主题文件，必要时先拆新模块。

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- `app/providers/`：provider 抽象、mock provider、OpenAI-compatible remote provider
- `app/services/chat_execution_service.py`：任务流编排与 SSE 主链
- `app/services/task_queue_service.py`：单进程任务执行槽位、capacity-aware oldest eligible FIFO 等待调度、安全等待快照、等待项移除与测试重置入口
- `app/services/tool_runtime.py`：tool registry / provider / source、tool runtime helper、preflight、diagnostics、result preview/output/summary 语义
- `app/services/tool_runtime_planning.py`：tool planner / provider planner / planner payload normalization，作为 `tool_runtime.py` 的 facade 拆分模块
- `app/services/tool_runtime_execution.py`：tool runtime context、result preview/output/summary、attempt loop、trace event、rag follow-up 与 plan-item service execution，作为 `tool_runtime.py` 的 facade 拆分模块
- `app/services/tool_runtime_http_json.py`：HTTP JSON request/template/response/mapping、execution diagnostics 与敏感信息脱敏，作为 `tool_runtime.py` 的 facade 拆分模块
- `app/services/tool_runtime_registry.py`：registry/file-backed/provider-source、settings/preflight diagnostics、runtime artifacts 与 service action 模型，作为 `tool_runtime.py` 的 facade 拆分模块
- `scripts/tool_runtime_slice/`：`test_tool_runtime_slice.py` 的主题 mixin 包，承接 provider/source、planner、settings/registry、http_json、task/export/governance、trace provider source、runtime/result/rag 等 slice 测试；当前最大主题模块约 4.7k 行
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

`GET /api/settings` 的响应包含只读 `task_queue_diagnostics`，用于观察当前单进程队列的 `max_concurrent`、`active_count`、`waiting_count`、`available_slots`、`current_user_active_count`、`current_user_waiting_count`、`current_user_available_slots`、`current_user_limit_reached`、可选 `session_id` 查询参数下的 `current_session_active_count`、`current_session_waiting_count`、`current_session_available_slots`、`current_session_limit_reached`、`has_waiting_tasks`、`saturated`、`pressure_state`、可选 per-user/per-session 上限、fairness 开关、`waiting_policy`、capacity-aware FIFO 标记与 poll interval；`SettingsSummaryResponse` 与 `_build_task_queue_diagnostics()` 使用 `TaskQueueDiagnosticsSummary` typed 契约固定基础与 governance 字段为 required，current-user/current-session 字段保持 optional，且 `pressure_state` 仅允许精确的 `idle` / `active` / `saturated` / `scope_limited`，`waiting_policy` 仅允许 `capacity_aware_oldest_eligible_fifo`；`max_concurrent`、计数与限额字段保持整数，poll interval 保持数值，状态与治理开关保持布尔。`current_user_available_slots` 是全局空槽与 per-user 剩余额度共同收敛后的有效可用槽位，`current_session_available_slots` 是全局空槽与 per-session 剩余额度共同收敛后的有效可用槽位。该字段不参与用户设置保存，也不改变 SSE / trace / export payload，不暴露内部 task ids。
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
python scripts/e2e_queue_concurrency.py --base-url http://127.0.0.1:8011
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
- `TASK_QUEUE_MAX_CONCURRENT`：单 backend 进程内同时执行的流式任务数，默认 `32`
- `TASK_QUEUE_POLL_INTERVAL_SEC`：queued 任务等待执行槽位时的 SSE 状态刷新间隔，默认 `0.25`

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- registry 治理语义已封板，不优先继续扩大旧 fallback 兼容面，也不继续维护已归档的 runtime spec 历史文档。
- 文档只保留高信号当前状态，不继续累积按天流水账。
