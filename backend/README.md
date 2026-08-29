# InsightAgent Backend

FastAPI 后端，提供 Auth、会话/任务、SSE、Trace、PostgreSQL、Memory、RAG、导出、usage 与审计能力；默认演示路径为 canonical `mock`，也支持 OpenAI-compatible `remote`。

## 当前状态

- `provider-tool-expansion` 已 100% 封板，当前进入维护收口；后续候选主线为 `ci-release-engineering`。
- HTTP JSON provider search 总量/命中归一化、provider planner 多协议工具调用解析、JSON 字符串参数和 reconnect 稳定错误码已完成。
- runtime 与测试结构治理完成：`backend/app` 与 `backend/scripts` 所有 Python 文件均低于 3000 行，当前最大文件为 `scripts/tool_runtime_slice/planning_provider.py` 2923 行。
- 项目级源码体积边界已扩展到前端源文件；生成锁文件不纳入拆分目标，`frontend/app/globals.css` 已拆为主题样式模块。
- 外部 SSE / trace / export / display shape、queued/running/cancel/reconnect 语义保持稳定。

## 当前验证基线

- Full slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，`1983/1983` 通过。
- Targeted：`registry 534/534`、`http_json 531/531`、`provider 538/538`、`runtime 163/163`、`trace 188/188`、`export 184/184`、`usage 63/63` 通过。
- Module boundary：`PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py`，`4/4` 通过，包含 3000 行文件规模边界。
- Frontend contract checks：node tests `122/122`、`npm run lint`、`npm run build` 通过。
- E2E：backend main 既有基线通过；本轮 targeted Chromium `workbench-main-path` `5/5` 通过。
- `py_compile`、`git diff --check` 通过；`data/insightagent.plan.back.md` 无 diff。

## Runtime 模块索引

- `app/services/module_export_utils.py`：拆分模块函数 rebinding 工具，保持原 facade monkeypatch 与 helper 查找语义。
- `app/services/tool_runtime.py`：稳定 facade，汇总旧导出路径，2547 行。
- `app/services/tool_runtime_planning.py`：planner、provider planner 与 payload normalization。
- `app/services/tool_runtime_display.py`：tool 显示名、语义分类、输出归一化与 `run_tool` 旧导出实现。
- `app/services/tool_runtime_execution.py`：runtime context、attempt 与前半段执行语义，2864 行。
- `app/services/tool_runtime_execution_flow.py`：trace event、RAG follow-up、iteration 与 service effects。
- `app/services/tool_runtime_http_json.py`：HTTP JSON request/template/mapping 核心，2522 行。
- `app/services/tool_runtime_http_json_execution.py`：HTTP JSON runner、execution spec、summary、diagnostics，1270 行。
- `app/services/tool_runtime_http_json_response.py`：响应读取、解码、错误格式化和敏感信息脱敏，1750 行。
- `app/services/tool_runtime_registry.py`：registry/file/provider-source facade，2768 行。
- `app/services/tool_runtime_registry_settings.py`：settings override、provider artifacts 与 diagnostics 实现。
- `app/services/tool_runtime_registry_runtime.py`：registry service action、preflight、runtime artifacts 实现，1781 行。
- `app/services/tool_runtime_registry_public.py`：兼容 wrapper 安装器，190 行。
- `app/services/chat_persistence_service.py`：会话/任务持久化与治理列处理，1755 行。
- `app/services/chat_persistence_trace_export.py`：Trace 展示、响应摘要与任务 export。
- `app/services/chat_persistence_usage.py`：usage summary/dashboard 与 session export response summary。
- `scripts/tool_runtime_slice/`：按主题组织的测试包；`test_tool_runtime_slice.py` 保留兼容入口。

## HTTP 接口范围

- Auth：`/api/auth/register`、`login`、`refresh`、`logout`、`me`、`sessions`。
- Settings：`GET/PUT /api/settings`、`POST /api/settings/validate`。
- Sessions：会话 CRUD、消息、Memory、usage 与 JSON/Markdown export。
- Tasks：创建、查询、详情、取消、SSE stream、trace/delta、usage 与 JSON/Markdown export。
- RAG：status、ingest、query、knowledge-bases、clear、delete。
- 其他：`GET /health`、审计日志接口。

除 `/health` 与 `/api/auth/*` 外，业务接口需要 `Authorization: Bearer <token>`。

## SSE / Trace 契约

- 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- `event: trace` 的 `data.step` 与 REST `TraceStep` 同构；action 的 `tool_start/tool_end` 与 trace 通过 `step_id` 对齐。
- remote provider 错误在 SSE `error` 中保持结构化 `code / fatal / retryable / detail / status_code`。
- `TraceStep`、result summary、safe output 由实时流、REST、export 与前端回放共享。

## Memory / RAG 边界

- Memory collection：`memory_{session_id}`；RAG collection：`kb_{user_hash}_{knowledge_base_id}`。
- Chroma 连接：`CHROMA_HOST`、`CHROMA_PORT`、`CHROMA_PROBE`；默认 `127.0.0.1:8001`。
- Chroma 不可达时 Memory/RAG 操作返回 503，任务结束后的 Memory 摘要写入为 best-effort。
- `shared-*` 知识库：admin 可写，普通用户只读。

## 本地运行

```bash
cd backend
backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

从仓库根目录执行测试：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
```

测试、e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。
