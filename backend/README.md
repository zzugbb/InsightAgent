# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前状态

- 后端 W1-W4 与阶段 5 基础产品化已完成：JWT + refresh、用户级设置与密钥加密、PostgreSQL、`RBAC-lite`、`rag-rbac-lite`、任务取消/超时、running task 恢复、导出、usage dashboard 与审计事件扩展已落地。
- `real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening`、`production-reliability-hardening`、`observability-experience` 与 `rag-product-experience` 均已封板；当前主线进入 `provider-tool-expansion`，进度约 64%；默认 settings 语义保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- `http_json` 真实执行器覆盖请求模板、鉴权/header/query/body、response_path/result_fields、常见搜索/计算/GraphQL/Elastic/OData/向量/RAG SDK 风格输出、preview/output/result-summary、trace/export/SSE/audit/settings diagnostics。
- `app/services/task_queue_service.py` 负责单进程执行槽位、queued 安全等待快照、capacity-aware oldest eligible FIFO、queued cancel 等待项移除，以及可选 per-user/per-session 并发治理。
- `GET /api/settings` 暴露只读 `task_queue_diagnostics`，typed 契约固定基础运行态、governance、pressure/waiting policy 与 optional current user/session scope 字段；不改变 SSE / trace / export payload，不暴露内部 task ids。
- `backend/scripts/test_tool_runtime_slice.py` 已拆到 `backend/scripts/tool_runtime_slice/`；`app/services/tool_runtime.py` 已拆出 planner、execution、HTTP JSON、registry 四个 facade 模块，外部 import 保持稳定。
- `tool_runtime_registry.py` 与 settings/route/audit/SSE/trace 边界已完成 provider/source 脱敏、冲突 alias、跨结构共享 alias map、runtime artifacts/service actions、模型输出层、export/task/usage/audit/SSE/trace 安全摘要。
- `rag-governance-hardening` 已封板：RAG ingest/query source metadata、嵌套 metadata value、query hit id、知识库标识、版本摘要、reserved alias、route/runtime trace/export/display、错误出口与 shared/private 列表边界均已收口；后端外部响应 shape 保持稳定。
- `production-reliability-hardening` 已 100% 封板，且最新 GitHub checks `2/2` 通过。后端已收口 waiting cleanup、execution owner/heartbeat、guarded running/terminal writes、duplicate active 防双执行、stale heartbeat 可选接管、terminal race 防误复活、reconnect SSE 终态回放与失败自愈。
- 关键后端契约：客户端 SSE 断开只释放本进程 active slot，并保留 running 任务供 reload/reconnect/cancel；服务端执行协程 `CancelledError` 才 owner-guarded 标记 failed 并清理归属。active slot、204 响应与外部 SSE / trace / export 契约不变。
- `observability-experience` 已 100% 封板；已完成任务失败线索聚合、来源分类、TaskResponse failure fields、task_failed audit event 兜底恢复、Task Center 任务列表 audit failure hint 批量回放、Task Center registry profile/provider source 本地筛选生效、Task Center 当前可见任务失败来源诊断分组与来源 chip 本地下钻、跨视图 Failure URL 预设直达、稳定失败码文本纳入前端 Failure 语义、Usage Dashboard / Audit Logs 到任务详情的回放入口、Usage Dashboard top tasks 失败摘要派生、Audit Logs 失败 hint/source/code/message 可读详情、Audit Logs 服务端 keyword 过滤，以及前端共享 Trace Failure/semantic 语义统计、统计卡下钻与 Task Center 观测筛选；后端 SSE / trace / export shape 保持不变。
- `rag-product-experience` 已 100% 封板；前端知识库治理表消费现有 `document_versions` 展开版本明细并派生 source/document 文档组摘要；后端 `DELETE /api/rag/knowledge-bases/{knowledge_base_id}/documents` 支持按 source/document 删除文档组，并记录 `rag_document_delete` 审计事件；Runtime Debug 基于现有 RAG query metadata/distance 展示查询级召回摘要、质量分布、召回使用建议、质量/来源/未知来源筛选、组合筛选空结果提示、命中来源摘要与召回质量标签；RAG status/list、ingest/query、SSE、trace 与 export 外部响应 shape 保持不变。
- `provider-tool-expansion` 已启动：HTTP JSON provider search 输出归一化支持分页型 `data`/`records` 当前页结果配合 `meta.page.total` / `pagination.total` / `paging.total` 等显式总量元数据、GraphQL connection 的 `data.search.pageInfo.totalCount + edges[]`、Meilisearch/Algolia 风格 `estimatedTotalHits` / `nbHits`、Brave 风格 `web.results` 嵌套结果容器，并支持 `totalResults: "1,234"` 这类安全千分位总量字符串；显式 `result_fields` 支持 `$['@odata.count']` / `$["@odata.count"]` 这类 bracket quoted 特殊字段键；provider planner 支持 Gemini/Vertex 风格 `candidates[].content.parts[].functionCall{name,args}` 与 Bedrock/Claude Converse 风格 `content[].toolUse{name,input}`，`args`/`input` 支持对象或 JSON 字符串；trace/export/display 输出 shape 不变。

## 当前验证基线

- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability`：`35/35` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue`：`66/66` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task`：`361/361` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings`：`216/216` 通过
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`：`1960/1960` 通过
- provider-tool targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k nested_web_results`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k paginated`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k formatted_total`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bracket_quoted`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k graphql_connection_total`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k estimated_total_hits_alias`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k provider_search`，`5/5` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k http_json`，`523/523` 通过
- provider planner targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_use_string_input`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bedrock`，`1/1` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k gemini`，`2/2` 通过；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_plan_provider`，`45/45` 通过
- usage observability targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k usage_dashboard`，`40/40` 通过
- RAG targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag`，`79/79` 通过
- RAG route targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route`，`2/2` 通过
- Result summary targeted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary`，`30/30` 通过
- RAG source/version/shared/route/runtime/error targeted：sensitive knowledge_base_id redaction、nested metadata value redaction、query hit id redaction、runtime helper output redaction、runtime shared retrieve scope、runtime knowledge_base_id redaction、route service identifier redaction、route document_versions source/document_id redaction、legacy sensitive collection suffix redaction、invalid version metadata filtering、version alias canonicalization、reserved metadata override、private `shared-*` shadow 隔离、status/list/400/503 error redaction 均通过
- RAG runtime/export targeted：safe version metadata、legacy chunk shape、chunk object metadata alignment、parallel runtime chunk metadata、export knowledge_base_id redaction、result summary/output/preview/observation knowledge_base_id redaction 均通过
- `backend/.venv/bin/python -m py_compile` 本轮相关 backend route/test 模块：通过
- backend e2e main phase：baseline / main / export consistency / cancel-timeout 通过
- frontend node tests：runtime debug modal utils / knowledge base governance modal utils / workbench utils / audit logs modal utils / task detail utils / stream store utils / model settings utils，当前 `121/121` 通过
- frontend build：`cd frontend && npm run build` 通过
- frontend type contract：`npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts` 通过
- frontend targeted TS：本轮涉及的 runtime debug modal/rag results/utils、knowledge base governance modal/utils、i18n、workbench main path e2e 与 usage dashboard e2e 通过 targeted `tsc`
- backend queue e2e phase：低并发 `8011` 覆盖 queued cancel、safe queue snapshot、settings diagnostics 与 followup completion
- frontend targeted Chromium：`workbench-edge-cases.spec.ts:824` 与 `workbench-main-path.spec.ts:436` 均通过，覆盖 GitHub frontend-e2e 暴露的 reload/background session stream 与 reload recovery cancel 回归
- frontend full Chromium：默认 `8000/3001` 通过，`51 passed / 1 skipped`；覆盖新增知识库版本明细展开，低并发 queued 专项在 full 阶段按预期 skip
- frontend targeted Chromium：`e2e/usage-dashboard.spec.ts:1543`，`1/1` 通过，覆盖真实 RAG ingest 后展开知识库版本明细、source/document 文档组摘要、文档组删除与状态归零
- frontend RAG Chromium：`e2e/workbench-main-path.spec.ts:352` 与 `e2e/workbench-main-path.spec.ts:443`，`2/2` 通过，覆盖真实 RAG ingest/query 后的查询级召回摘要、质量分布、召回使用建议、召回质量筛选、召回来源筛选、未知来源筛选、组合筛选空结果提示、命中来源摘要、召回质量标签与 distance 解释
- frontend task center governance Chromium：`e2e/usage-dashboard.spec.ts:372`，`1/1` 通过，覆盖 Task Center registry profile/source 请求与列表可见性过滤
- frontend task detail replay Chromium：`e2e/usage-dashboard.spec.ts:1329`，`3/3` 通过，覆盖 Task Center/任务详情语义统计、统计卡下钻与语义过滤计数一致性
- frontend remote error observability Chromium：`e2e/workbench-remote-errors.spec.ts:479`，`1/1` 通过，覆盖 Task Center audit failure hint 回放、失败来源诊断分组、诊断来源 chip 本地下钻、Failure URL 预设直达与可读失败说明、Needs attention / Failed status 观测筛选、Audit Logs 服务端 keyword 请求、任务详情 audit failure hint 恢复与失败轨迹快捷定位
- frontend usage/audit-to-detail Chromium：`e2e/usage-dashboard.spec.ts:774`，`1/1` 通过
- frontend queue phase：低并发 `8011/3001` 通过，`1/1`
- frontend diagnostics finalize：`scripts/ci_finalize_e2e_for_workflow.sh --scope frontend --summary-file /tmp/frontend-e2e-finalize-summary.md --event-name push --ref refs/heads/main` 在 `strict_level=any` 下通过，error-context counters 为 0
- GitHub checks：`7550120 fix: 保留客户端断流运行任务` 已 `2/2` 通过
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过
- `git diff --check`：通过
- 后续运行 backend slice、启动 backend、跑 backend e2e 和提交时，先按 `../docs/development-runbook.md` 使用固定 venv 与提权边界，避免重复触发本机端口 / `.git/index.lock` 权限错误。

## 下一步后端计划

1. 当前主线：`provider-tool-expansion`，进度约 64%；本轮完成 Brave 风格 `web.results` 嵌套搜索结果容器的 `documents_total/hit_count` 归一化；下一步继续按小红测补真实 provider/tool 协议输出差异。
2. 已封板主线：`real-tool-execution`、`queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening`、`production-reliability-hardening`、`observability-experience`、`rag-product-experience`。
3. 后续候选主线：`ci-release-engineering`；继续保持 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 入口、SSE / trace / export 外部契约、runbook 提权流程与单文件规模治理稳定。

## 后续候选主线

- `ci-release-engineering`：把 backend slice、targeted RAG、queue phase、full e2e 和 diff hygiene 固化成更清晰的分层门禁。

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
- `scripts/tool_runtime_slice/`：`test_tool_runtime_slice.py` 的主题 mixin 包，承接 provider/source、provider-tool expansion、planner、settings/registry、http_json、task/export/governance、trace provider source、runtime/result/rag 等 slice 测试；当前最大主题模块约 4.7k 行
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
- `TASK_EXECUTION_OWNER_ID`：当前 backend 执行实例 ID，多实例部署时应为每个实例设置唯一稳定值
- `TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC`：running 任务刷新 DB heartbeat 的最小间隔，默认 `2.0`
- `TASK_EXECUTION_STALE_AFTER_SEC`：启动恢复时接管其他实例 stale running 任务的阈值，默认 `0` 关闭

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- registry 治理语义已封板，不优先继续扩大旧 fallback 兼容面，也不继续维护已归档的 runtime spec 历史文档。
- 文档只保留高信号当前状态，不继续累积按天流水账。
