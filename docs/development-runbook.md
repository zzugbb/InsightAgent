# 开发运行手册

从仓库根目录执行下方命令；最新结果与运行实例范围见[验证基线](validation-baseline.md)。本手册维护命令、权限和排障规则，具体协议见专题文档。

## 快速规则

- Python 使用 `backend/.venv/bin/python`（Python 3.14）；前端使用已安装的 Node 24+ 与 npm，不为常规检查重装依赖。
- slice / Node tests / lint / 静态检查通常不需提权。Docker、本机监听/访问、浏览器 e2e、写 `.git/index` 通常需提权；不要用首次失败反复探测权限。
- 原始完整计划 `data/insightagent.plan.back.md` 永远只读。开发实时计划已删除，不重新创建；同步三个 README、受影响专题和验证基线。
- 现有服务先查端口和健康；测试用独立 fixture，不重建开发 PostgreSQL/Chroma。旧 Chroma `/chroma/chroma` 挂载可能漏掉实际 `/data`，先按[备份说明](local-stack-backup-restore.md)保护数据。
- 沿用主题模块与 facade；后端 slice 主题 <=2500 行，临近上限拆 `_partN.py`。更改数量级或接口时同步审查调用方和契约。
- 不输出真实 env、Key、密码、token、业务正文和原始异常。审批通道连接失败时重试同一必要操作，不绕过拒绝。

## 静态检查

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k security
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py --list-tests -k queue
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py --list-selections
backend/.venv/bin/python backend/scripts/check_api_surface.py
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_run_release_gate.sh --phase frontend
```

`-k` 是 unittest 子串筛选，零匹配退出码 5；`--list-tests` 仅发现、不执行，`--list-selections` 列出六个维护选择器且不可与 `-k` 同用。前端 Node 文件列表以门禁脚本 `FRONTEND_NODE_TESTS` 为准，不在文档重复维护。

## CI 与诊断

`scripts/ci_run_release_gate.sh` 是不启动本机服务的发布前门禁聚合入口：`auto` 在 PR 中按 changed files 选择 backend/frontend 阶段，并始终跑 tooling 与 hygiene；非 PR 或 diff 不可解析时保守跑全量。`backend` 跑 full slice 与 module boundary，`frontend` 跑 node tests、lint、Next 16 默认 Turbopack production build 与显式 webpack fallback build，`tooling` 跑 CI/e2e tooling 自测，`hygiene` 跑 compileall、diff whitespace、备份计划 diff，以及 `scripts/check_conflict_markers.sh` 对受 git 管理文本文件的行首冲突标记扫描；可用 `--dry-run` 查看命令清单，可用 `--summary-file` / `--json-summary-file` 输出 CI 摘要，摘要包含 `summary_kind`、`summary_schema_version`、`service_required`、resolved phases、逐步结果、`step_summary` 聚合计数、`failed_step_labels`、release/rollback `decision_summary` 与 `operator_summary`。首个步骤失败时保留原退出码，并在退出前写出失败 decision/operator summary；空 focus phase 不应触发 `set -u` 二次失败。
后端 full slice 已检查 `backend/api_surface_baseline.json` 是否匹配运行时 OpenAPI。更改接口时按 [`docs/api-changelog.md`](api-changelog.md) 核对兼容性、更新指纹与记录；指纹变更提示人工审查，不能替代 SSE/Trace/export 运行时契约测试。
`scripts/ci_download_previous_release_gate_summary.sh` 通过 GitHub CLI 尝试下载同分支上一条 successful `release-gate-summary` artifact，不启动服务；缺少 `gh`、分支、run id、历史 run 或 artifact 时写 `release_gate_previous_summary_download` 低敏诊断和 `operator_summary` 并返回成功。
`scripts/ci_release_gate_trend_summary.sh` 只读取当前和可选上一份 release gate JSON summary，不启动服务；输出 baseline/improved/regressed/changed/unchanged、步骤计数 delta、新增/移除失败步骤标签，Markdown 直接展示当前/上一份 operator 状态、主行动和关注阶段，并在 JSON 中透传 release/rollback `decision_summary` 与 `operator_summary`。旧 release gate artifact 尚无 `operator_summary` 时，会按既有 result、step summary 与失败标签派生低敏兼容摘要，避免历史基线阻断后置契约校验。GitHub release-gate workflow 会生成 previous download 诊断并上传 `release-gate-trend-summary` artifact。
`scripts/ci_assert_operator_summary_contract.sh` 只读取 summary JSON 和可选 Markdown，不启动服务；校验低敏 `operator_summary` 必需字段、状态/严重级别枚举、标量列表值，以及 Markdown 是否暴露 operator 状态与主行动。该检查已纳入 tooling 自测、release-gate workflow 与 release readiness matrix。workflow 将 release Markdown 固定写入 `/tmp/release-gate-summary.md`，追加到当前 step summary 后仍使用原文件完成后置校验和 artifact 上传；不要跨 step 读取 `$GITHUB_STEP_SUMMARY`，GitHub 会为每个 step 提供不同文件。

`scripts/ci_release_readiness_matrix.sh` 只生成发布候选检查矩阵，支持 `--format markdown|json` 与 `--output <path>`。矩阵明确区分不需要服务的静态 release gate、previous summary 下载诊断、operator summary contract、需要已启动服务的 backend/frontend e2e，以及 e2e 后置 artifact-stage guard；并保留 release visibility summary、rollback decision log 与 artifact retention policy 三类发布/回滚可见性检查项。它不启动服务，也不替代下方 service-backed e2e 命令。
GitHub backend/frontend e2e workflow 已按矩阵覆盖低并发 queue 阶段；backend 失败诊断可重复传 `--secondary-health-url`，用于同时采集 timeout 与 queue 实例。
artifact-stage guard 的 main 分支严格度为 `fail-on-missing`，PR 严格度为 `fail-on-empty`；手动 `workflow_dispatch` 可用 `artifact_stage_strict_level` 覆盖。`ci_assert_artifact_stage_health.sh` 的 Markdown/JSON 输出包含低敏 `operator_summary`，用于区分可继续、需复核 warning、需补齐 artifact 的值班行动。
本机检查、业务 RAG、真实模型人工指引与证据导出见[验收指南](acceptance.md)；没有提供输入或只返回 manual/skipped 的阶段不能计作完成。

GitHub `backend-e2e` / `frontend-e2e` 的 “Validate e2e tooling fixtures” 步骤使用 `if: always()`，主 e2e 失败时仍运行 `test_ci_e2e_tooling.sh` 并写入 artifact guard 摘要占位，避免 finalize 把 guard 摘要缺失计入主因噪音。`frontend-e2e` 失败诊断重跑使用 `scripts/ci_rerun_frontend_e2e_diagnostics.sh`：仅在存在 `test-results/.last-run.json` 且记录失败时调用 Playwright `--last-failed`（与主跑共用输出目录，不用独立 `--output`）；脚本恒以退出码 0 结束，但在 step summary 与 `/tmp/frontend-e2e-rerun-diagnostics.{md,json}` 如实标注 `diagnostic_gate_result` 与 `playwright_exit_code`，不以 `continue-on-error` 伪装成功。
release-gate、backend-e2e 与 frontend-e2e 上传的发布/e2e artifacts 显式保留 `14` 天。
`scripts/ci_export_diagnostics_overview.sh` 会汇总 backend/frontend diagnostics 与 artifact guard 结果，并输出低敏 `operator_summary`，只包含状态、主行动、告警计数、guard 失败数、关注 scope 与阻塞 guard scope。

请求日志只含 request ID、method、路由模板、状态码和完整响应耗时；SSE 建连 HTTP 200 不能说明任务成功。Provider 日志 `llm_http_attempt` 仅含模式、结果、状态族、尝试耗时与 usage 可用性；400 兼容回退可产生两次尝试，不等于任务数或账单调用数。

```bash
backend/.venv/bin/python backend/scripts/summarize_provider_attempts.py <日志文件>
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

汇总 request/stream 耗时 count/min/max/mean（毫秒），缺失/非法值单独计数，无样本为 null；包含错误/回退，不推算首 token、供应商推理时间或成本。tooling fixture 在 release/backend/frontend workflow 都运行；故障注入在首个无依赖命令触发，不假设 e2e runner 有 backend/.venv。`/dev/fd` 沙箱限制可能影响 shell fixture，按权限流程重跑并保留首次结果。

## 本机服务与 e2e

先检查已有端口和服务（本机访问通常需提权）：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3001 -sTCP:LISTEN
curl -sS http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3001
```

缺少服务时分别开终端启动，不重复启动已有实例：

```bash
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --hostname 127.0.0.1 --port 3001
```

服务准备后运行：

```bash
bash scripts/ci_run_backend_e2e.sh --phase main --base-url http://127.0.0.1:8000 --log-dir /tmp
bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001
```

低并发 queue 使用独立后端 `8011`，设置 `TASK_QUEUE_MAX_CONCURRENT=1 TASK_QUEUE_POLL_INTERVAL_SEC=0.1`；前端通过 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8011` 指向该实例。backend/frontend 队列检查均用 `--phase queue` 与对应地址，不改变默认 full 的并发基线。测试后仅停止自己启动的会话，再检查端口，无权停他人服务。

键盘专项在 `frontend/` 运行：

```bash
npx playwright test e2e/composer-keyboard.spec.ts --project=chromium --project=firefox --project=webkit --workers=1 --reporter=list --output=/tmp/insightagent-composer-keyboard-results
# CI 生产构建路径：webServer 执行 npm run build && npm run start
CI=1 npx playwright test e2e/composer-keyboard.spec.ts --project=chromium
```

业务 API 用 fixture，三浏览器覆盖1440/390px；composition/isComposing/229 不等于真实操作系统输入法全面验收。错误覆盖层检查 `nextjs-portal [data-nextjs-dialog]` 为0，生产环境不要求裸 portal 存在。非CI playwright.config.ts 会启动 dev；已有本机服务须按配置判断复用，避免重复拉起。

## 隔离专项入口

下表命令均为 `backend/.venv/bin/python backend/scripts/<文件>`；需要 Docker/随机本机端口，创建独立数据资源并自动清理，模型为本地替身，不请求真实供应商。静态 selector 与浏览器命令见各专题；下表描述覆盖范围，不宣称在每次文档维护中重跑。

| 主题 | 文件 |
| --- | --- |
| [Agent 上下文/反馈](agent-core-alignment.md) | `test_agent_core_scenarios_postgres.py`、`test_agent_feedback_postgres.py`、`test_agent_tool_context_postgres.py` |
| [依赖](tool-dependencies.md) / [任务并发](task-tool-parallel.md) / [HTTP 并发](http-read-parallel.md) | `test_tool_dependencies_postgres.py`、`test_task_parallel_postgres.py`、`test_http_parallel_postgres.py` |
| [分支](task-reruns.md) / [步骤恢复](task-checkpoints.md) | `test_task_rerun_postgres.py`、`test_task_checkpoint_postgres.py` |
| [原子成功/终态](task-completion.md) | `test_task_completion_postgres.py`、`test_task_terminal_postgres.py` |
| [回答提示](answer-completion.md) / [流结束](provider-stream-completion.md) / [用量](usage-accounting.md) | `test_answer_completion_postgres.py`、`test_provider_stream_postgres.py`、`test_usage_accounting_postgres.py` |
| [RAG 导入](rag-background-ingest.md) | `test_rag_ingest_postgres.py --with-chroma`（实际400切块与部分失败） |
| [规划等待与恢复](real-model-acceptance.md) | `test_provider_planning_wait_postgres.py` |

这些场景已接入 backend-e2e；前端 Trace/导入/恢复/回答 fixture 由 full Chromium 发现。备份自测、生产镜像锁定依赖/embedding、试点 Compose、真实模型与业务工具分别见[恢复](local-stack-backup-restore.md)、[部署](pilot-deployment-preflight.md)、[验收](acceptance.md)，不混算。

## 提交路径

普通沙箱写 `.git/index.lock` 常被拒，检查 diff 后可直接申请提权 stage/commit。指定本次变更文件，不加入实际 env 或原始计划：

```bash
git diff --check
git add <本次变更文件>
git diff --cached --check
git diff --cached -- data/insightagent.plan.back.md
git commit -m "docs: 整理项目文档"
git status --short
git log -1 --oneline
```

提交使用简体中文 Conventional Commits。本地提交与 Git 推送分别处理，新的本地检查不沿用旧 CI 绿作远端验证；历史交接记录从 Git 查询。
