# InsightAgent Backend

FastAPI 后端承担任务生命周期、工具驱动 Agent 执行、流式回答和执行证据持久化。模型可选择显式 mock 演示或 OpenAI-compatible remote；工具检索、计算与配置的 HTTP 请求执行真实逻辑。

[项目概览](../README.md) · [架构](../docs/architecture.md) · [配置](../docs/configuration.md) · [契约](../docs/runtime-contracts.md)

## 本地运行

从项目根目录准备 Python 3.14 环境、安装依赖，并按[根 README](../README.md#快速开始)启动 PostgreSQL / Chroma。已有环境统一使用 `backend/.venv/bin/python`。

```bash
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

`backend/.env.example` 是开发模板，实际 `backend/.env` 不进入版本控制。环境变量覆盖文件值；模型设置按用户保存到数据库，并继承未显式覆盖的服务端默认配置。remote 缺 Key / 地址会明确报错。设置摘要仅返回 `api_key_configured`，Key 加密入库；配置继承、清除和轮换边界见[配置指南](../docs/configuration.md)。

健康 `/health`、交互接口 `/docs`、运行时契约 `/openapi.json`。生产镜像运行非 root Uvicorn、锁定依赖并准备 embedding 缓存；使用 [Dockerfile.pilot](Dockerfile.pilot) 与[部署预检](../docs/pilot-deployment-preflight.md)，不能把开发 reload 栈当作部署。

## 执行与稳定契约

- 模型规划 → 工具执行 → 安全 Observation → 有界反馈 → 最终流式回答。默认最多 3 轮、32 工具节点；DAG 最多 128 边，仅公开预览标量可绑定到 query / expression。
- `task_retrieve` 调用实际 Chroma 知识检索；`calc_eval` 使用 AST 白名单求值。HTTP JSON 工具显式执行配置无效时拒绝，不静默回退模板；普通提示里的测试故障标记不触发工具失败。
- 独立内建读取/计算及明确声明只读的固定 HTTP GET 可有界并发，默认串行；进程最多 8 个读取线程。Trace、审计、终态与消息由协调线程写入，取消/超时丢弃迟到结果。
- 完成事务原子保存状态、最终 Trace、usage、assistant 消息与会话时间；提交后写 best-effort Memory 并发送 done。竞争落败不插入成功回答。
- 规划和回答用量分阶段保存，汇总优先 overall，缺项按已知 final + planning 回退；未知消耗不补成零，费用为配置单价估算。
- 失败重连读取历史，不能自动重放模型或工具。分支重跑创建独立会话；实验性 checkpoint 仅支持内建顺序计划。
- 安全 header、服务端 request ID、路由模板日志与固定错误分类不回显凭据或业务正文。OpenAPI 指纹差异按[API 变更流程](../docs/api-changelog.md)审查，不能只凭指纹认定语义兼容。

取消、错误、完整性提示、工具依赖、并发与后台导入的细节见[运行时契约索引](../docs/runtime-contracts.md)。

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
- `GET /api/sessions/{session_id}`
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
- `POST /api/tasks/{task_id}/reruns`（HTTP 201，独立会话、幂等 queued 分支；可选 checkpoint_step_id 创建限定步骤恢复）
- `GET /api/tasks/{task_id}/checkpoints`（本人实验性步骤恢复候选，不返回结果正文）
- `GET /api/tasks/{task_id}/reruns?limit=&offset=`（本人来源与直接分支分页）
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`
- `GET /api/tasks/usage/summary`
- `GET /api/tasks/usage/dashboard`
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/ingest-jobs`（HTTP 202，幂等受理）
- `GET /api/rag/ingest-jobs`（当前用户任务列表）
- `GET /api/rag/ingest-jobs/{job_id}`
- `POST /api/rag/ingest-jobs/{job_id}/cancel`（仅排队任务）
- `POST /api/rag/query`
- `GET /api/rag/knowledge-bases`
- `POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}/documents`
- `GET /api/audit/logs`（当前用户范围内的审计记录）

补充约定：

- `/health`、注册、登录和 refresh 有各自公开入口；会话/任务/设置/RAG 以及 auth 的 me、会话管理、退出等受保护操作需要 `Authorization: Bearer <token>`，用户列表另要求 admin。
- `GET /api/tasks*` 相关响应包含 `status_normalized`、`status_label`、`status_rank`。
- usage 接口支持来源维度统计：`provider / estimated / mixed / legacy`。
- `shared-*` 知识库走共享命名空间；admin 可写，普通用户只读。

完整 schema 以 `/openapi.json` 和 [api_surface_baseline.json](api_surface_baseline.json) 为准；当前 51 操作 / 89 组件。新增接口属于兼容扩展，后台 5000 切块限制等输入收紧已记录在[变更记录](../docs/api-changelog.md)。

## 关键实现位置

下表服务文件位于 `app/services/`，对应契约见[技术文档](../docs/README.md)。继续沿用主题模块与兼容 facade，避免扩大主编排文件。

| 职责 | 入口 |
| --- | --- |
| 配置 / 存储 / schema | `app/config.py`、`app/db.py`、`app/schemas/trace.py` |
| HTTP 路由 / 模型 | `app/api/routes/`、`app/providers/` |
| 任务生命周期 / 队列 | `chat_execution_service.py`、`task_queue_service.py` |
| 分支 / checkpoint | `task_rerun_{service,schema}.py`、`task_checkpoint_service.py`、`app/api/routes/task_reruns.py` |
| 调度 / DAG / 并发 | `task_tool_{execution,parallel}.py`、`tool_plan_dependencies.py`、`tool_http_parallel_policy.py` |
| 运行时 facade / 规划 / 单工具 | `tool_runtime.py`、`tool_runtime_planning.py`、`tool_runtime_display.py`、`tool_runtime_execution.py`、`tool_runtime_execution_flow.py` |
| HTTP JSON / 脱敏 | `tool_runtime_http_json.py`、`tool_runtime_http_json_execution.py`、`tool_runtime_http_json_response.py` |
| 注册表 / 来源 / 诊断 | `tool_runtime_registry.py` 及 `_settings.py`、`_runtime.py`、`_public.py` 主题模块 |
| 持久化 / Trace / 导出 / 用量 | `chat_persistence_service.py`、`chat_persistence_trace_export.py`、`chat_persistence_usage.py`；账本 `tasks.usage_json` |
| 历史 / 模型证据 | `conversation_context.py`、`agent_knowledge_context.py`、`agent_tool_context.py` |
| Memory / RAG / 导入 | `chroma_memory_service.py`、`chroma_rag_service.py`、`rag_ingest_{jobs,schema,worker,runner}.py`、`rag_chunking.py`、`app/api/routes/rag_ingest.py` |
| 设置 / 认证 / 审计 | `settings_service.py`、`auth_service.py`、`auth_session_service.py`、`audit_service.py` |
| 回归入口 | `scripts/tool_runtime_slice/` 主题包，`scripts/test_tool_runtime_slice.py` 兼容入口 |

## SSE 与 TraceStep 契约

事件为 `start / state / trace / tool_start / tool_end / heartbeat / token / cancelled / timeout / done / error`。`trace.data.step` 与 REST `TraceStep` 同构，工具事件按 `step_id` 对齐。delta 默认 200、最大 500 条；seq 递增但不保证连续，最终回答更新也必须可见。

远端流必须收到 `[DONE]` 或已知首 choice `finish_reason` 才能正常结束；部分输出 EOF 保存失败 Trace，不写成功消息、不发送 done、不自动重试。error 的 `code / fatal / retryable / detail / status_code` 保持兼容，diagnostic 只含低敏分类。见[流结束](../docs/runtime-contracts.md#流结束与回答完整性)、[成功事务](../docs/runtime-contracts.md#成功提交与终态竞争)与[回答完整性](../docs/runtime-contracts.md#流结束与回答完整性)。

## Memory / Chroma / Embedding

PostgreSQL 是完整业务账本；`memory_{session_id}` 是会话语义记忆，`kb_{user_hash}_{knowledge_base_id}` 是知识库。默认通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 `127.0.0.1:8001`，`shared-*` 库普通用户只读、管理员可写。

应用未显式传自定义 embedding；当前后端 Python 客户端的默认函数采用 ONNX MiniLM，导入 worker 与 API 都需要可用模型缓存。试点镜像构建期下载/校验/预热，禁网运行已有验证。Chroma 不可达时 Memory/RAG 接口返回 503，任务后的摘要写入不阻塞成功回答。自动对话历史来自 PostgreSQL 快照，不能把 Memory 调试接口说成已接入长期自动召回。

后台导入由 PostgreSQL 持久队列与监管 worker 驱动；幂等、分批确认进度、排队取消、权限复核与中断恢复见[导入契约](../docs/rag-background-ingest.md)。PostgreSQL 与 Chroma 没有跨库事务，失败后先复核部分写入，不自动重放。

## 检查与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k security
backend/.venv/bin/python backend/scripts/check_api_surface.py
bash scripts/ci_run_release_gate.sh --phase backend
```

数据库/HTTP 集成使用隔离资源，命令和权限见[运行手册](../docs/development-runbook.md)。历史 SQLite 迁移入口 `scripts/migrate_sqlite_to_postgres.py` 仅用于已有数据迁移，当前运行时只支持 PostgreSQL；含密码的连接串不要写进共享命令记录。

本地实现与工程收尾完成，后续按可复现问题维护。当前测试数量、配置脱敏回归、真实模型结果及镜像范围统一见[验证基线](../docs/acceptance.md#验证基线)，外部就绪未验收。写入并行与 HTTP/DAG checkpoint 延期。

沿用主题模块与 facade，不向历史大文件无限追加；新增测试放入有余量的主题。开发后同步三个 README 与受影响专题，验证集中在验证基线；开发实时计划已删除，原始备份计划永远只读。
