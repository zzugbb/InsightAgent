# InsightAgent

可观测 AI Agent 平台，覆盖会话、任务执行、Trace、Memory、RAG、鉴权、持久化、导出、运行态诊断与 CI/release 门禁。

## 当前状态

- `provider-tool-expansion` 已 100% 封板。
- `ci-release-engineering` 已 100% 封板。
- 当前主线为 `production-runtime-hardening`，进度约 15%；SSE `error` payload 已追加低敏 `diagnostic` 摘要，不改变旧字段。
- 后续开发继续保持 SSE / trace / export / e2e 外部契约兼容，并维持 backend/app、backend/scripts 与 frontend 源码单文件 <= 3000 行边界。

## 当前验证基线

- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto --summary-file /tmp/release-gate-check.md --json-summary-file /tmp/release-gate-check.json` 通过；非 PR 环境保守解析为 backend/frontend/tooling/hygiene 全量。
- Backend：full slice `1984/1984`；module boundary `4/4`；targeted production_reliability `36/36`、reconnect `8/8` 通过。
- Frontend：node tests `122/122`、`npm run lint`、`npm run build` 通过。
- E2E 基线：backend main 通过；frontend full Chromium `52 passed / 1 skipped`；queue 阶段已纳入 backend/frontend CI workflow。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check`、备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 稳定契约

- SSE 事件、`TraceStep`、result summary、safe output、JSON/Markdown export shape 保持稳定；`error.diagnostic` 只包含低敏分类、recoverability、HTTP 状态族与 detail 存在性。
- 默认 settings 仍按 provider/model/api_key 自动选择 `remote` 或 canonical `mock`。
- queued/running/cancel/reconnect 与 task recovery 语义保持稳定。
- `data/insightagent.plan.back.md` 是只读备份计划，永远不参与同步或修改。

## 核心边界

- `PostgreSQL` 保存用户、会话、消息、任务、trace、usage、设置与审计，是完整历史和回放账本。
- `Chroma Memory` 使用会话级 collection `memory_{session_id}`，服务当前对话的语义记忆。
- `Chroma RAG` 使用知识库 collection `kb_{user_hash}_{knowledge_base_id}`，服务跨会话复用资料。
- Chroma 默认连接 `127.0.0.1:8001`；不可达时 Memory/RAG 接口返回 503，任务后的 memory 摘要写入保持 best-effort。
- 仓库主目录为 `backend/`、`frontend/`、`data/`；完整启动和门禁细节以 runbook 为准。

## 运行与门禁

```bash
docker compose up -d chroma
./start_insightagent.command
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

详细测试、e2e、启动和提交流程以 [`docs/development-runbook.md`](docs/development-runbook.md) 为准。

## 下一步

- `product-ux-polish`：Workbench/Task Center 高频操作、trace 回放可读性与治理页面效率。
