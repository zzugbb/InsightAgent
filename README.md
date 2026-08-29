# InsightAgent

可观测 AI Agent 平台，覆盖会话、任务执行、Trace、Memory、RAG、鉴权、持久化、导出与运行态诊断。

## 当前状态

- `provider-tool-expansion` 已 100% 封板；provider search 总量/命中归一化、provider planner 多协议工具调用解析、JSON 字符串参数与 reconnect 稳定错误码均已收口。
- 当前主线为 `ci-release-engineering`，进度约 65%；release gate 已支持 PR diff 自动分层、手动阶段选择、Markdown/JSON 摘要和 GitHub Actions summary artifact；release readiness matrix 与 backend/frontend e2e workflow 已覆盖静态门禁、service-backed main/timeout/queue、smoke/full/queue 与 artifact guard。
- 阶段 5 基础产品化闭环保持可演示：Auth、PostgreSQL、SSE、Trace、Memory、RAG、任务恢复、导出、usage dashboard、审计。
- 前端全局样式治理已完成：`frontend/app/globals.css` 已拆为 `frontend/app/styles/` 主题模块，原文件仅保留有序 `@import` facade。
- 当前可维护源码体积边界覆盖 backend/app、backend/scripts 与 frontend 源码；排除生成锁文件后所有源码均低于 3000 行，当前最大文件为 `planning_provider.py` 2923 行。
- 当前不改变 SSE / trace / export / e2e 外部契约。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto` 通过，非 PR 环境保守解析为 backend/frontend/tooling/hygiene 全量；summary 输出与 release readiness matrix 通过。
- Backend full slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，`1983/1983` 通过。
- Backend targeted：`registry 534/534`、`http_json 531/531`、`provider 538/538`、`runtime 163/163`、`trace 188/188`、`export 184/184`、`usage 63/63` 通过。
- Module boundary：`backend/scripts/test_tool_runtime_module_boundaries.py`，`4/4` 通过，包含 3000 行文件规模边界。
- Frontend：node tests `122/122`，`npm run lint`、`npm run build` 通过；新增 frontend source size boundary 测试。
- E2E：backend main 既有基线通过；backend/frontend queue 已纳入 CI workflow 编排；full Chromium 既有基线 `52 passed / 1 skipped`；本轮 targeted Chromium `workbench-main-path` `5/5` 通过。
- Hygiene：`py_compile`、`git diff --check`、备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 稳定契约

- SSE 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- `trace` 事件的 `data.step` 与 REST `TraceStep` 同构；`tool_start/tool_end` 通过同一 `step_id` 对齐 action 节点。
- 实时流、REST trace、任务/会话 JSON 与 Markdown export、前端回放共用同一结果摘要与安全输出语义。
- 默认 settings 仍按 provider/model/api_key 自动选择 `remote` 或 canonical `mock`；queued/running/cancel/reconnect 语义不变。
- `data/insightagent.plan.back.md` 是只读备份计划，永远不参与同步或修改。

## 目录与运行

```text
InsightAgent/
├── backend/   FastAPI + PostgreSQL + Chroma
├── frontend/  Next.js + React + Ant Design
└── data/      运行数据与只读计划备份
```

```bash
docker compose up -d chroma
./start_insightagent.command
```

详细测试、e2e、启动和提交流程以 [`docs/development-runbook.md`](docs/development-runbook.md) 为准。
不启动服务的发布前门禁可运行：

```bash
bash scripts/ci_run_release_gate.sh --phase auto
```

CI 调试时可追加 `--summary-file <path>` 与 `--json-summary-file <path>` 输出步骤摘要。
发布候选检查范围可生成 Markdown/JSON 矩阵：

```bash
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

## 活跃文档

- [`backend/README.md`](backend/README.md)：后端模块、接口和后端验证基线。
- [`frontend/README.md`](frontend/README.md)：前端能力、回放契约和前端验证基线。
- [实时计划](.cursor/plans/insightagent_开发计划_306e7915.plan.md)：当前状态、约束、验证与候选主线。
