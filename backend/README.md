# InsightAgent Backend

FastAPI 后端，提供 Auth、会话/任务、SSE、Trace、PostgreSQL、Memory、RAG、导出、usage、审计与 tool runtime 能力；默认演示路径为 canonical `mock`，也支持 OpenAI-compatible `remote`。

## 当前状态

- `provider-tool-expansion` 与 `ci-release-engineering` 均已 100% 封板；当前主线为 `production-runtime-hardening`，进度约 15%。
- Provider/tool 兼容能力已覆盖 HTTP JSON search 总量/命中归一化、GraphQL connection、常见搜索 API 别名、多 provider planner tool call 输出与 JSON 字符串参数。
- CI/release 工程已覆盖 release gate、release readiness matrix、backend main/timeout/queue service-backed e2e、artifact diagnostics、main push artifact `fail-on-missing` 与多 health URL 失败诊断。
- SSE `error` payload 已追加低敏 `diagnostic` 摘要，便于运行态错误按分类、recoverability 与 HTTP 状态族定位。
- `backend/app` 与 `backend/scripts` 所有 Python 源码均低于 3000 行；`tool_runtime.py` 与 `test_tool_runtime_slice.py` 保持兼容入口，新增实现继续落到主题模块。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto --summary-file /tmp/release-gate-check.md --json-summary-file /tmp/release-gate-check.json` 通过。
- Full slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，`1984/1984` 通过。
- Targeted：`production_reliability 36/36`、`reconnect 8/8`、registry/http_json/provider/runtime/trace/export/usage 通过。
- Module boundary：`PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py`，`4/4` 通过，包含 3000 行规模边界。
- E2E 基线：backend main 通过；timeout/queue 已纳入 backend CI workflow。
- Hygiene：`py_compile`、`git diff --check`、备份计划 diff 检查通过。

## 稳定契约

- SSE 事件、REST `TraceStep`、result summary、safe output 与 JSON/Markdown export shape 保持稳定。
- `tool_start/tool_end` 与 trace action 节点通过 `step_id` 对齐。
- remote provider 错误在 SSE `error` 中保持结构化 `code / fatal / retryable / detail / status_code`，并追加低敏 `diagnostic`。
- Memory/RAG collection 命名、Chroma 503 降级、shared knowledge base 权限语义保持稳定。

## 关键入口

- `app/services/tool_runtime.py`：tool runtime 兼容 facade。
- `app/services/tool_runtime_planning.py`：planner/provider planner 与 payload normalization。
- `app/services/tool_runtime_http_json.py`、`tool_runtime_http_json_execution.py`、`tool_runtime_http_json_response.py`：HTTP JSON provider 执行与响应归一化。
- `app/services/tool_runtime_registry.py` 与 registry 子模块：tool registry、provider source、runtime artifacts 与 diagnostics。
- `app/services/chat_persistence_service.py` 与 chat persistence 子模块：会话/任务持久化、trace 展示、usage 与 export。
- `scripts/tool_runtime_slice/`：后端 slice 测试主题包；`backend/scripts/test_tool_runtime_slice.py` 是兼容入口。

## 本地运行

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

测试、e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。
