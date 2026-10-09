# 开发运行手册

从仓库根目录执行下方命令；最新结果与运行实例范围见[验证基线](acceptance.md#验证基线)。本手册维护命令、权限和排障规则，具体协议见专题文档。

## 快速规则

- Python 使用 `backend/.venv/bin/python`（Python 3.14）；前端使用已安装的 Node 24+ 与 npm，不为常规检查重装依赖。
- slice / Node tests / lint / 静态检查通常不需提权。Docker、本机监听/访问、浏览器 e2e、写 `.git/index` 通常需提权；不要用首次失败反复探测权限。
- 原始完整计划 `data/insightagent.plan.back.md` 永远只读。开发实时计划已删除，不重新创建；同步三个 README、受影响专题和验证基线。
- 现有服务先查端口和健康；测试用独立 fixture，不重建开发 PostgreSQL/Chroma。旧 Chroma `/chroma/chroma` 挂载可能漏掉实际 `/data`，先按[备份说明](pilot-deployment-preflight.md#开发栈备份恢复)保护数据。
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

### 选择门禁

[发布门禁](../scripts/ci_run_release_gate.sh)不启动服务。PR 的 `auto` 按变更选择后端/前端阶段，始终检查 tooling 与 hygiene；修改 CI、脚本、Compose 或本手册时跑全量。非 PR 或 diff 无法解析时也跑全量。

| 阶段 | 检查范围 |
| --- | --- |
| `backend` | full slice、模块边界；包含 OpenAPI 基线比对 |
| `frontend` | Node tests、lint、Turbopack 与 webpack 双生产构建 |
| `tooling` | CI/e2e 工具自测 |
| `hygiene` | compileall、差异空白、原始计划 diff、跟踪文本的冲突标记 |
| `all` | 上述全部阶段 |

查看命令用 `--dry-run`；实际运行可同时保存两种摘要：

```bash
bash scripts/ci_run_release_gate.sh --phase hygiene \
  --summary-file /tmp/release-gate-summary.md \
  --json-summary-file /tmp/release-gate-summary.json
```

摘要包含逐步结果、失败标签、发布/回滚决策和 `operator_summary`（状态、主行动、关注阶段）。首个失败保留原退出码并写摘要；排障先看失败步骤，DRY-RUN 不能视为通过。更改接口按[API 变更流程](api-changelog.md)审查；OpenAPI 指纹不替代 SSE/Trace/导出测试。

### 查找诊断与产物

摘要读取与校验不启动服务；前端失败重跑需要服务和浏览器权限。参数以对应脚本的 `--help` 为准。

| 目的 | 入口 | 输出与失败处理 |
| --- | --- | --- |
| 选择静态和服务验收范围 | [ci_release_readiness_matrix.sh](../scripts/ci_release_readiness_matrix.sh) | Markdown/JSON 检查矩阵；包含发布可见性、回滚记录与产物保留检查，不执行矩阵中的验收 |
| 下载同分支上次成功门禁 | [ci_download_previous_release_gate_summary.sh](../scripts/ci_download_previous_release_gate_summary.sh) | 下载诊断；缺 `gh` 或历史产物时成功退出并明确缺项，不算已有对照基线 |
| 比较当前与上次结果 | [ci_release_gate_trend_summary.sh](../scripts/ci_release_gate_trend_summary.sh) | 趋势、步骤变化与失败标签；旧摘要缺 operator 字段时派生兼容摘要 |
| 校验摘要格式 | [ci_assert_operator_summary_contract.sh](../scripts/ci_assert_operator_summary_contract.sh) | 校验 JSON 必需字段、枚举及 Markdown 展示；失败先检查源摘要 |
| 校验 e2e 产物是否齐全 | [ci_assert_artifact_stage_health.sh](../scripts/ci_assert_artifact_stage_health.sh) | guard 与 operator 摘要；main 用 `fail-on-missing`，PR 用 `fail-on-empty`，手动运行可指定严格度 |
| 汇总 e2e 诊断 | [ci_export_diagnostics_overview.sh](../scripts/ci_export_diagnostics_overview.sh) | 状态、主行动、告警和阻塞 scope，不包含业务正文 |
| 重跑前端失败案例 | [ci_rerun_frontend_e2e_diagnostics.sh](../scripts/ci_rerun_frontend_e2e_diagnostics.sh) | 已有服务与失败记录时执行 `--last-failed`；仅为诊断，检查报告中的 `playwright_exit_code` 与 `diagnostic_gate_result` |

```bash
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

服务验收命令见[下一节](#本机服务与-e2e)，业务与真实模型操作见[验收指南](acceptance.md)。缺输入、manual 或 skipped 阶段均不计作通过。

### CI 排障规则

- release-gate、backend-e2e、frontend-e2e 的产物保留 **14 天**。先下载对应 run 的摘要/日志；本机临时文件不是持久产物。
- release workflow 使用 `/tmp/release-gate-summary.md` 校验和上传；不要跨 step 读取 `$GITHUB_STEP_SUMMARY`，各 step 文件不同。
- backend/frontend e2e 覆盖独立低并发 queue；后端诊断可重复传 `--secondary-health-url`，同时检查 timeout 与 queue 实例。
- e2e 主跑失败后，`if: always()` 的 tooling 检查仍产生 guard 摘要，避免缺失产物掩盖主因。前端诊断重跑共用主跑输出目录，只有 `.last-run.json` 记录失败才执行；入口退出 0 不代表失败案例通过。
- tooling fixture 的故障注入从无依赖命令开始，不假设 e2e runner 存在 `backend/.venv`。shell fixture 受 `/dev/fd` 沙箱限制时，按权限流程重跑并保留首次结果。

### Provider 与请求日志

请求日志包含 request ID、method、路由模板、状态码和响应耗时；SSE 建连 200 不证明任务成功。`llm_http_attempt` 仅记录模式、结果、状态族、尝试耗时与用量可用性，400 兼容回退可能产生两次尝试。

```bash
backend/.venv/bin/python backend/scripts/summarize_provider_attempts.py <日志文件>
```

汇总 request/stream 耗时 count/min/max/mean（毫秒）；缺失/非法值单独计数，无样本为 null。样本包含错误和回退，不能据此推算首 token、供应商推理时间、任务数或账单成本。

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
| [Agent 上下文/反馈](architecture.md#agent-上下文与反馈) | `test_agent_core_scenarios_postgres.py`、`test_agent_feedback_postgres.py`、`test_agent_tool_context_postgres.py` |
| [依赖](tool-execution.md#依赖与结果绑定) / [任务并发](tool-execution.md#任务内并发) / [HTTP 并发](tool-execution.md#http-只读并发) | `test_tool_dependencies_postgres.py`、`test_task_parallel_postgres.py`、`test_http_parallel_postgres.py` |
| [分支](runtime-contracts.md#完整任务分支重跑) / [步骤恢复](runtime-contracts.md#实验性步骤恢复) | `test_task_rerun_postgres.py`、`test_task_checkpoint_postgres.py` |
| [原子成功/终态](runtime-contracts.md#成功提交与终态竞争) | `test_task_completion_postgres.py`、`test_task_terminal_postgres.py` |
| [回答提示](runtime-contracts.md#流结束与回答完整性) / [流结束](runtime-contracts.md#流结束与回答完整性) / [用量](runtime-contracts.md#用量口径) | `test_answer_completion_postgres.py`、`test_provider_stream_postgres.py`、`test_usage_accounting_postgres.py` |
| [RAG 导入](rag-background-ingest.md) | `test_rag_ingest_postgres.py --with-chroma`（实际400切块与部分失败） |
| [规划等待与恢复](acceptance.md#真实模型记录) | `test_provider_planning_wait_postgres.py` |

这些场景已接入 backend-e2e；前端 Trace/导入/恢复/回答 fixture 由 full Chromium 发现。备份自测、生产镜像锁定依赖/embedding、试点 Compose、真实模型与业务工具分别见[恢复](pilot-deployment-preflight.md#开发栈备份恢复)、[部署](pilot-deployment-preflight.md)、[验收](acceptance.md)，不混算。

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
