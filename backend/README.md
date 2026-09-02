# InsightAgent Backend

FastAPI 后端，提供 Auth、会话/任务、SSE、Trace、PostgreSQL、Memory、RAG、导出、usage、审计与 tool runtime 能力；默认演示路径为 canonical `mock`，也支持 OpenAI-compatible `remote`。

## 当前状态

- 已封板主线：`provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`、`product-ux-polish`、`production-operations-readiness`、`security-hardening`。
- `security-hardening` 封板结论：全局安全响应头、JWT header/默认密钥/CORS 硬阻断、refresh token 输入收敛、认证错误低敏化、auth session 副作用保护与 secret material 默认凭据阻断已收口，业务 payload 不变。
- `/health.operations` 保持非敏感运维摘要：readiness、readiness_level、warnings、warning_summary、risk_domains、readiness_checks、部署配置、SLO、备份恢复、runbook/值班、演练新鲜度、队列、执行实例、超时与 Chroma probe。
- 当前主线：`release-observability-polish`，进度约 35%；release readiness matrix 已补发布摘要、回滚判定与 artifact retention 检查，backend/frontend/release-gate artifacts 显式保留 14 天，release gate Markdown/JSON summary 已输出步骤聚合计数与失败步骤标签。
- `backend/app` 与 `backend/scripts` Python 源码均低于 3000 行；后续新增实现继续优先落到主题模块，保留兼容 facade。

## 当前验证基线

- Release gate all：PASS，覆盖 backend/frontend/tooling/hygiene；JSON summary 已用 `json.tool` 复核。
- Backend：full slice `2018/2018`；module boundary `4/4`；security `17/17`；production operations health `11/11`。
- Frontend：release gate 内置 node 清单与扩展 node tests 均为 `141/141`；`npm run lint` 与 `npm run build` 通过。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check` 与备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 下一步后端计划

1. `release-observability-polish` 已推进到 release summary 结构化输出：`step_summary` 与 `failed_step_labels` 可用于发布审批、趋势比较和失败定位。
2. 下一步从门禁趋势摘要或发布/回滚摘要可见性中选取可红测证明的小切片。
3. 继续保持 full slice 入口、SSE / trace / export 外部契约、runbook 提权流程与单文件规模治理稳定。

## 后续候选主线

- `release-observability-polish`：发布/回滚可见性、artifact 保留策略、release summary 结构化输出与门禁趋势摘要。

## 稳定契约

- SSE 事件、REST `TraceStep`、result summary、safe output 与 JSON/Markdown export shape 保持稳定。
- 全局 HTTP 响应追加 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Permissions-Policy` 与 `Cross-Origin-Opener-Policy`；该安全头层不改变业务响应体、SSE event、trace/delta 或 export body shape。
- Access token 解析要求 JWT header 为 `alg=HS256`、`typ=JWT`；签名、过期和 subject 校验语义保持不变。
- Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常。
- 生产环境禁止使用默认 `INSIGHT_AGENT_JWT_SECRET` 或其首尾空白包装值签发或验签 access token；开发默认值仍只允许在非生产环境使用。
- 生产环境默认 `INSIGHT_AGENT_JWT_SECRET` 及其首尾空白包装值也不能作为 refresh token 哈希或 secret 加密派生材料；`/health.operations` 按同一口径报告 `default_jwt_secret`。
- 生产环境禁止 `INSIGHT_AGENT_CORS_ORIGINS` 包含 wildcard `*`；非生产 CORS 调试行为保持不变。
- 鉴权依赖对 token parser 异常统一返回低敏 `401 invalid token`，保留 `WWW-Authenticate: Bearer`，不向客户端回显内部配置或解析细节。
- Auth token 签发与刷新会在创建/轮换 refresh token 和写入 auth session 前先校验 access token 签发配置；生产默认 JWT secret 错误不留下会话存储副作用。
- `tool_start/tool_end` 与 trace action 节点通过 `step_id` 对齐。
- remote provider 错误在 SSE `error` 中保持结构化 `code / fatal / retryable / detail / status_code`，并在 SSE 与 failure audit 中追加低敏 `diagnostic.category/reason/recoverability/http_status_family/has_detail`。
- 任务详情页可通过兼容 URL 参数 `trace_semantic` 回放语义 Trace；前端语义切换与 normalized 状态/轮询控制均不改变后端任务、trace 或 export payload。
- Workbench Inspector 语义筛选清理旧 search/kind 干扰属于前端本地状态变更，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure drilldown、normalized 状态/失败摘要与显式 `failure_hint` 优先级均为前端本地语义，不改变任务列表 API、后端 trace 或 export shape。
- Task Center、Audit Logs 与知识库治理列表的错误恢复/陈旧数据保留不改变任务、审计或 RAG API shape。
- 前端 SSE close 后失败摘要兜底只补拉既有任务/trace 并映射低敏 failure hint，不改变后端 SSE、任务、trace 或 export payload。
- Memory/RAG collection 命名、Chroma 503 降级、shared knowledge base 权限语义保持稳定。
- 默认 settings 语义保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。

## HTTP 接口范围

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

`GET /api/settings` 的响应包含只读 `task_queue_diagnostics`，用于观察全局、当前用户和可选当前会话的 active/waiting/available 计数、限额状态、压力状态与等待策略。该字段不参与用户设置保存，不暴露内部 task ids，也不改变 SSE / trace / export payload。

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
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}/documents`

补充约定：

- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`。
- `GET /api/tasks*` 相关响应包含 `status_normalized`、`status_label`、`status_rank`。
- usage 接口支持来源维度统计：`provider / estimated / mixed / legacy`。
- `shared-*` 知识库走共享命名空间；admin 可写，普通用户只读。

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- `app/providers/`：provider 抽象、mock provider、OpenAI-compatible remote provider
- `app/services/chat_execution_service.py`：任务流编排与 SSE 主链
- `app/services/task_queue_service.py`：单进程任务执行槽位、capacity-aware oldest eligible FIFO 等待调度、安全等待快照、等待项移除与测试重置入口
- `app/services/tool_runtime.py`：tool runtime 兼容 facade，汇总旧导出路径
- `app/services/tool_runtime_planning.py`：planner、provider planner 与 payload normalization
- `app/services/tool_runtime_display.py`：tool 显示名、语义分类、输出归一化与 `run_tool` 旧导出实现
- `app/services/tool_runtime_execution.py`：runtime context、attempt 与前半段执行语义
- `app/services/tool_runtime_execution_flow.py`：trace event、RAG follow-up、iteration 与 service effects
- `app/services/tool_runtime_http_json.py`：HTTP JSON request/template/mapping 核心
- `app/services/tool_runtime_http_json_execution.py`：HTTP JSON runner、execution spec、summary 与 diagnostics
- `app/services/tool_runtime_http_json_response.py`：响应读取、解码、错误格式化和敏感信息脱敏
- `app/services/tool_runtime_registry.py`：registry/file/provider-source facade
- `app/services/tool_runtime_registry_settings.py`：settings override、provider artifacts 与 diagnostics 实现
- `app/services/tool_runtime_registry_runtime.py`：registry service action、preflight 与 runtime artifacts 实现
- `app/services/tool_runtime_registry_public.py`：兼容 wrapper 安装器
- `app/services/chat_persistence_service.py`：会话/任务持久化与治理列处理
- `app/services/chat_persistence_trace_export.py`：Trace 展示、响应摘要与任务 export
- `app/services/chat_persistence_usage.py`：usage summary/dashboard 与 session export response summary
- `scripts/tool_runtime_slice/`：后端 slice 测试主题包；`backend/scripts/test_tool_runtime_slice.py` 是兼容入口
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/chroma_rag_service.py`：RAG ingest/query/status、knowledge base list/clear/delete 与 shared/private 语义
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 usage，供任务列表、导出与 dashboard 复用

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
- SSE `error.diagnostic` 是新增低敏摘要字段，包含稳定 `reason` 枚举；旧客户端可忽略。

## 当前实现边界

- `trace/delta` 支持 `limit` 参数控制单次增量返回量；当前默认 `200`，最大 `500`。
- `GET /api/tasks/usage/summary` 与 `GET /api/tasks/usage/dashboard` 都已支持 usage 来源统计；当前来源语义是 `provider / estimated / mixed / legacy`。
- 任务相关对外读取优先走 task row 上的规范化治理摘要与 parsed trace 主干，不鼓励在 route 层继续扩写 sibling fallback。
- 默认 settings 语义是：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`；remote `base_url/api_key` 继承链已打通到 get/save/validate。
- shared RAG 语义当前保持 `shared-*` 命名空间约定：admin 可写共享库，普通用户对共享库只读。
- registry extra tool / override 的真实执行器入口以 `execution.kind=http_json` 为主；请求模板、响应字段映射与既有 runtime semantic/preview/export 主链保持同一契约。
- 显式给 tool 配了 `execution` 时，当前语义是“宁可报配置错，也不回退 stub”；provider/source 治理不会把 real tool 假阳性地跑成本地模板行为。
- provider/source/global settings 侧会把静态可判定的 `execution` 坏配置归一成 registry diagnostics。

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

## 本地运行

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如需重新创建虚拟环境：

```bash
cd backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

如需将历史 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
backend/.venv/bin/python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

常用校验：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue
cd backend && PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py
bash scripts/ci_run_release_gate.sh --phase auto
```

`scripts/ci_run_release_gate.sh` 的 Markdown/JSON summary 会保留 resolved phases、逐步结果、步骤聚合计数与失败步骤标签；service-backed e2e 仍按 runbook 单独执行。

如需 Memory / RAG 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

常用运行参数：

- `TRACE_PERSIST_MIN_INTERVAL_SEC`：trace 增量持久化最小间隔
- `STREAM_RECONNECT_POLL_FAST_SEC`：running reconnect 快轮询间隔
- `STREAM_RECONNECT_POLL_MAX_SEC`：running reconnect 慢轮询上限
- `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`：reconnect heartbeat 间隔
- `TASK_TIMEOUT_SEC`：任务超时秒数
- `TASK_QUEUE_MAX_CONCURRENT`：单 backend 进程内同时执行的流式任务数，默认 `32`
- `TASK_QUEUE_POLL_INTERVAL_SEC`：queued 任务等待执行槽位时的 SSE 状态刷新间隔，默认 `0.25`
- `TASK_EXECUTION_OWNER_ID`：当前 backend 执行实例 ID，多实例部署时应为每个实例设置唯一稳定值
- `TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC`：running 任务刷新 DB heartbeat 的最小间隔，默认 `2.0`
- `TASK_EXECUTION_STALE_AFTER_SEC`：启动恢复时接管其他实例 stale running 任务的阈值，默认 `0` 关闭
- `INSIGHT_AGENT_BACKUP_ENABLED`：生产备份是否已启用，默认 `false`
- `INSIGHT_AGENT_BACKUP_PROVIDER`：备份提供方标识；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_BACKUP_RESTORE_RUNBOOK_URL`：恢复 runbook 链接；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_BACKUP_LAST_RESTORE_DRILL_AT`：最近一次恢复演练时间（ISO-8601），用于判断恢复演练新鲜度
- `INSIGHT_AGENT_OPERATIONS_RUNBOOK_URL`：生产运维 runbook 链接；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_INCIDENT_CONTACT`：生产值班/应急联系人；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_INCIDENT_LAST_DRILL_AT`：最近一次应急响应演练时间（ISO-8601）；`/health` 仅暴露演练记录与新鲜度摘要
- `INSIGHT_AGENT_STATUS_PAGE_URL`：状态页链接；`/health` 仅暴露是否已配置

测试、e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- registry 治理语义已封板，不优先继续扩大旧 fallback 兼容面，也不继续维护已归档的 runtime spec 历史文档。
- 文档收敛只处理当前状态、验证基线、下一步计划/候选主线、稳定契约和高信号摘要；长期参考章节不应被整段删除。
`GET /health` 额外返回只读 `operations` 摘要，包含 `readiness`、`readiness_level`、非敏感 `warnings`、`warning_summary` 告警等级计数、`risk_domains` 按 deployment/SLO/backup_restore/runbook/runtime 聚合的风险计数、`readiness_checks` 固定清单、部署配置分类与布尔校验、SLO 阈值口径、备份恢复演练状态、runbook/值班响应配置状态、应急响应演练新鲜度、任务队列并发、执行实例 stale recovery、任务超时与 Chroma probe 状态；不会返回数据库连接串、API key、密钥、联系人或 runbook URL 原文，也不改变既有健康字段。
