# InsightAgent Backend

FastAPI 后端承担任务生命周期、工具驱动 Agent 执行、流式回答和执行证据持久化。模型可选择显式 mock 演示或 OpenAI-compatible remote；工具检索、计算与配置的 HTTP 请求执行真实逻辑。

[项目概览](../README.md) · [架构](../docs/architecture.md) · [配置](../docs/configuration.md) · [契约](../docs/runtime-contracts.md)

## 本地运行

从项目根目录准备 Python 3.14 环境、安装依赖，并按[根 README](../README.md#快速开始)启动 PostgreSQL / Chroma。已有环境统一使用 `backend/.venv/bin/python`。

```bash
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

开发模板见 [.env.example](.env.example)，实际 `.env` 不进入版本控制。配置优先级、用户模型设置、Key 继承与轮换统一见[配置指南](../docs/configuration.md)。

健康 `/health`、交互接口 `/docs`、运行时契约 `/openapi.json`。生产镜像运行非 root Uvicorn、锁定依赖并准备 embedding 缓存；使用 [Dockerfile.pilot](Dockerfile.pilot) 与[部署预检](../docs/pilot-deployment-preflight.md)，不能把开发 reload 栈当作部署。

## 执行与稳定契约

独立[公开展示](../showcase/README.md)已准备专用合成案例：真实 glm-5.3 检索/计算，受控 fixture 失败及真实模型独立恢复分支。公开站只回放经过字段白名单与来源核对的记录，不访问本后端、不公开 Key 或完整应用 API；后端源码与运行契约不变。来源见[素材说明](../showcase/data/README.md)，结果见[验收基线](../docs/acceptance.md#公开项目展示)，当前尚未公开发布。

模型规划 → 工具执行 → 安全 Observation → 有界反馈 → 最终流式回答。检索、计算与配置的 HTTP 请求执行真实逻辑；任务状态、回答、Trace 与用量由后端统一保存。

| 需要了解 | 权威说明 |
| --- | --- |
| 上下文、证据预算与反馈轮次 | [Agent 上下文与反馈](../docs/architecture.md#agent-上下文与反馈) |
| DAG、参数绑定、工具配置与只读并发 | [工具执行](../docs/tool-execution.md) |
| SSE/Trace、成功事务、回答结束、用量与恢复 | [运行时契约](../docs/runtime-contracts.md) |
| 后台导入、部分写入与权限 | [RAG 导入](../docs/rag-background-ingest.md) |
| 日志与凭据保护、接口兼容性 | [安全政策](../SECURITY.md)、[API 变更流程](../docs/api-changelog.md) |

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

SSE、REST Trace、增量同步与导出消费同一执行记录；工具事件按 `step_id` 对齐，`seq` 递增但不保证连续。完成事务原子保存成功状态、回答、Trace 与用量，再发送 `done`。

远端流缺少有效结束信号时保存失败 Trace；重连读取已有记录。完整事件、错误字段、delta 分页和结束判断见[运行时契约](../docs/runtime-contracts.md)。

## Memory / Chroma / Embedding

PostgreSQL 是完整业务账本，Chroma 是 Memory / RAG 向量存储。默认连接 `127.0.0.1:8001`；collection 命名、共享权限和自动历史边界见[架构说明](../docs/architecture.md)。

embedding 在后端 Python 客户端计算，API 与导入 worker 都需要模型缓存；试点镜像构建期准备缓存。Chroma 不可达时 Memory/RAG 接口返回 503，任务后的摘要写入不阻塞成功回答。

后台导入由 PostgreSQL 持久队列与监管 worker 驱动。双存储没有跨库事务，失败后需复核部分写入；幂等、取消及恢复见[导入契约](../docs/rag-background-ingest.md)。

## 检查与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k security
backend/.venv/bin/python backend/scripts/check_api_surface.py
bash scripts/ci_run_release_gate.sh --phase backend
```

数据库/HTTP 集成使用隔离资源，命令和权限见[运行手册](../docs/development-runbook.md)。历史 SQLite 迁移入口 `scripts/migrate_sqlite_to_postgres.py` 仅用于已有数据迁移，当前运行时只支持 PostgreSQL；含密码的连接串不要写进共享命令记录。

后端源码基线、静态/集成检查、真实模型结果和镜像范围统一见[验证基线](../docs/acceptance.md#验证基线)。

工作台的弹窗分层、响应式布局和标识展示由前端维护。知识库 Collection 在页面详情中查看或复制，API、路由及导出仍使用完整标识；页面费用标签明确为估算，不改变后端用量来源与计算口径。

开发遵循[维护规则](../AGENTS.md)与[贡献指南](../CONTRIBUTING.md)，沿用主题模块和兼容 facade。
