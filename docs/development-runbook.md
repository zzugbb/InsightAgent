# Development Runbook

本文件记录当前 Codex 沙箱下 InsightAgent 的高频运行、e2e 与提交路径。目标是后续开发直接走正确命令和权限，不再用失败来探测环境。

## 快速规则

- 后端 Python 统一用 `backend/.venv/bin/python`，不要临时找系统 Python 或重装依赖。
- 前端 Node 依赖已在 `frontend/node_modules`，常规检查在 `frontend/` 下用 `npm` 脚本。
- 单元/slice/lint 通常不需要提权。
- 访问本机 Docker、监听本机端口、访问本机 e2e 服务、写 `.git/index` 通常需要提权。
- `data/insightagent.plan.back.md` 永远不要修改。
- `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 虽在 `.gitignore` 范围内，但当前是 tracked 文件，文档同步和提交必须包含它。
- 每个主线确认封板后，整理 `README.md`、`backend/README.md`、`frontend/README.md` 与实时计划文件：仅收敛“进度/封板状态相关块”，保留当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要；删除或收缩按轮流水账、旧失败过程和重复验证清单。
- 文档收敛不是把整份 README 改成短状态页；接口范围、运行方式、关键实现位置、SSE/Trace 契约、Memory/RAG 说明、文档维护约定等长期参考章节应保留，除非对应功能真的被删除或迁移。
- 控制单文件规模：新增测试/实现优先落到主题文件；主题文件明显膨胀时先拆出新主题文件或新模块，再继续追加。历史上的 `backend/scripts/test_tool_runtime_slice.py` 和 `app/services/tool_runtime.py` 已按该规则拆成 slice 主题包与 facade 模块。
- `backend/scripts/tool_runtime_slice` 主题文件保持 <= 2500 行；临近上限时拆到 `_partN.py`，原主题文件保留为组合 facade，后续新增测试进入有余量的分片。
- `test_tool_runtime_slice.py -k <pattern>` 沿用 unittest 子串筛选；有效筛选与 full slice 行为不变，显式筛选零匹配时会打印 pattern 并以退出码 5 结束。
- `test_tool_runtime_slice.py --list-tests [-k <pattern>]` 只列出发现到的测试 ID 与总数，不执行测试；可用于提交前确认 selector 的真实覆盖范围。
- `test_tool_runtime_slice.py --list-selections` 动态列出六个维护选择器及其覆盖数，任一选择器零匹配时返回 5；该命令不能与 `-k` 组合。
- tooling fixture 会同时在 release-gate 与 backend/frontend E2E workflow 中运行；失败注入测试不能假设 E2E runner 存在 `backend/.venv`，应在首个无依赖命令上注入确定性退出码。
- 本地 PostgreSQL/Chroma 离线备份与隔离恢复见 [`docs/local-stack-backup-restore.md`](local-stack-backup-restore.md)；备份前必须停止对应 Compose 项目，恢复只写入全新项目卷。`compose.full.yml` 与 `docker-compose.yml` 的 Chroma 持久卷现挂载 `/data`，与当前镜像日志中的 persist path 一致；旧容器若曾使用 `/chroma/chroma`，重建前先保存容器内 `/data`，不能假设旧命名卷包含数据。
- 后端请求观测日志为单行 JSON，字段为 `event=http_request`、服务端 `request_id`、method、路由模板、status_code、duration_ms；原始 URL/query/header/body 和异常正文不进入该日志。`X-Request-ID` 对已配置 CORS 来源可读。流式响应耗时到流关闭为止，SSE 建连后的业务失败不能只用 HTTP 200 判断，应结合 SSE/Trace 失败事件。
- 远端 OpenAI 兼容提供方每次实际 HTTP 尝试输出 `event=llm_http_attempt` 单行 JSON：`mode`、`outcome`、`status_family`、`duration_ms`、`usage_available`，无模型、主机、密钥、提示词或响应正文。`outcome` 描述本次 HTTP/流处理结果，不代表最终任务成功；`stream_options` 不兼容后的 400 回退会记两次尝试。用 `backend/.venv/bin/python backend/scripts/summarize_provider_attempts.py <日志文件>` 离线汇总；该数量是上游 HTTP 尝试数，不是任务数、账单调用数或 token 用量。目标环境仍需验证采集、留存和告警。
- A2 试点部署前用 [`docs/pilot-deployment-preflight.md`](pilot-deployment-preflight.md) 的镜像配方、只读预检与演练记录模板；后端 `requirements.pilot.lock` 约束试点镜像的完整安装版本，Docker 构建期会运行 `pip check` 并比较 `pip freeze`。变更直接依赖后须在隔离环境重新解析并更新锁，再构建候选镜像验证。`scripts/check_pilot_deploy_config.py` 只输出固定检查码。`backend/.venv/bin/python scripts/smoke_pilot_images.py --backend-image <本地后端镜像> --frontend-image <本地前端镜像> --expected-api-base-url <前端构建时 API 地址>` 先在禁网容器中核对非 root 默认 embedding，再用临时 Docker 栈验证生产模式/mock 模型下的后台导入、真实 Chroma 检索、任务 SSE/Trace/delta/导出、步骤恢复、排队取消，以及前端静态资源和浏览器 API 地址；需本机 Docker/端口及 Node/Playwright，不能替代真实模型、目标 HTTPS/访问边界或升级回滚验证。后端默认 embedding 在构建期准备，候选镜像不能依赖首次运行下载模型。无服务自测用 `backend/.venv/bin/python scripts/test_pilot_task_smoke.py`，已接入 tooling 门禁。

- 生产单机试点使用 `compose.pilot.yml` 和 `backend/.venv/bin/python scripts/pilot_compose.py check|up|stop|restart|down --env-file <仓库外配置> --project <固定名称>`；入口校验匹配的内部 PostgreSQL 凭据、模型配置、loopback 主机端口和镜像摘要，不打印 Compose 解析值。`up` 等待健康，`down` 保留卷。HTTPS 代理由目标环境提供。无环境/key 时保持未验证；Docker Compose 操作需提权。隔离持久化验证为 `scripts/smoke_pilot_compose.py`，仅使用随机新项目与 mock，结束删除自己的测试卷；命令和范围见[试点部署](pilot-deployment-preflight.md)。

## 不需要提权的常用命令

后台 RAG 导入的状态、幂等、批次进度和重启口径见 [RAG 后台导入](rag-background-ingest.md)。专项静态测试用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_ingest`（原任务专项与批次专项一起执行）；真实数据库锁与中断恢复用 `backend/.venv/bin/python backend/scripts/test_rag_ingest_postgres.py`，加 `--with-chroma` 验证 400 切块实际批量写入与部分失败。两者需要提权访问 Docker/本机随机端口，自动清理独立测试容器。backend-e2e workflow 使用 `--with-chroma`。

从仓库根目录运行：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py --list-tests -k queue
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py --list-selections
backend/.venv/bin/python scripts/test_local_stack_snapshot.py
backend/.venv/bin/python backend/scripts/check_api_surface.py
backend/.venv/bin/python backend/scripts/summarize_provider_attempts.py <日志文件>
python3 -m py_compile backend/app/config.py backend/app/services/chat_execution_service.py backend/app/services/task_queue_service.py
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_release_readiness_matrix.sh --format markdown
bash scripts/ci_download_previous_release_gate_summary.sh --workflow release-gate.yml --branch main --current-run-id 123 --summary-file /tmp/previous-release-gate-download-summary.md --json-summary-file /tmp/previous-release-gate-download-summary.json
bash scripts/ci_release_gate_trend_summary.sh --current-json /tmp/release-gate-summary.json --summary-file /tmp/release-gate-trend-summary.md --json-summary-file /tmp/release-gate-trend-summary.json
bash scripts/ci_assert_operator_summary_contract.sh --summary-json /tmp/release-gate-summary.json --summary-kind release_gate --markdown /tmp/release-gate-summary.md
git diff --check
git diff --cached --check
git diff -- data/insightagent.plan.back.md
```

`scripts/ci_run_release_gate.sh` 是不启动本机服务的发布前门禁聚合入口：`auto` 在 PR 中按 changed files 选择 backend/frontend 阶段，并始终跑 tooling 与 hygiene；非 PR 或 diff 不可解析时保守跑全量。`backend` 跑 full slice 与 module boundary，`frontend` 跑 node tests、lint、Next 16 默认 Turbopack production build 与显式 webpack fallback build，`tooling` 跑 CI/e2e tooling 自测，`hygiene` 跑 compileall、diff whitespace 与备份计划 diff；可用 `--dry-run` 查看命令清单，可用 `--summary-file` / `--json-summary-file` 输出 CI 摘要，摘要包含 `summary_kind`、`summary_schema_version`、`service_required`、resolved phases、逐步结果、`step_summary` 聚合计数、`failed_step_labels`、release/rollback `decision_summary` 与 `operator_summary`。首个步骤失败时保留原退出码，并在退出前写出失败 decision/operator summary；空 focus phase 不应触发 `set -u` 二次失败。
后端 full slice 已检查 `backend/api_surface_baseline.json` 是否匹配运行时 OpenAPI。更改接口时按 [`docs/api-changelog.md`](api-changelog.md) 核对兼容性、更新指纹与记录；指纹变更提示人工审查，不能替代 SSE/Trace/export 运行时契约测试。
`scripts/ci_download_previous_release_gate_summary.sh` 通过 GitHub CLI 尝试下载同分支上一条 successful `release-gate-summary` artifact，不启动服务；缺少 `gh`、分支、run id、历史 run 或 artifact 时写 `release_gate_previous_summary_download` 低敏诊断和 `operator_summary` 并返回成功。
`scripts/ci_release_gate_trend_summary.sh` 只读取当前和可选上一份 release gate JSON summary，不启动服务；输出 baseline/improved/regressed/changed/unchanged、步骤计数 delta、新增/移除失败步骤标签，Markdown 直接展示当前/上一份 operator 状态、主行动和关注阶段，并在 JSON 中透传 release/rollback `decision_summary` 与 `operator_summary`。旧 release gate artifact 尚无 `operator_summary` 时，会按既有 result、step summary 与失败标签派生低敏兼容摘要，避免历史基线阻断后置契约校验。GitHub release-gate workflow 会生成 previous download 诊断并上传 `release-gate-trend-summary` artifact。
`scripts/ci_assert_operator_summary_contract.sh` 只读取 summary JSON 和可选 Markdown，不启动服务；校验低敏 `operator_summary` 必需字段、状态/严重级别枚举、标量列表值，以及 Markdown 是否暴露 operator 状态与主行动。该检查已纳入 tooling 自测、release-gate workflow 与 release readiness matrix。workflow 将 release Markdown 固定写入 `/tmp/release-gate-summary.md`，追加到当前 step summary 后仍使用原文件完成后置校验和 artifact 上传；不要跨 step 读取 `$GITHUB_STEP_SUMMARY`，GitHub 会为每个 step 提供不同文件。

`scripts/ci_release_readiness_matrix.sh` 只生成发布候选检查矩阵，支持 `--format markdown|json` 与 `--output <path>`。矩阵明确区分不需要服务的静态 release gate、previous summary 下载诊断、operator summary contract、需要已启动服务的 backend/frontend e2e，以及 e2e 后置 artifact-stage guard；并保留 release visibility summary、rollback decision log 与 artifact retention policy 三类发布/回滚可见性检查项。它不启动服务，也不替代下方 service-backed e2e 命令。
GitHub backend/frontend e2e workflow 已按矩阵覆盖低并发 queue 阶段；backend 失败诊断可重复传 `--secondary-health-url`，用于同时采集 timeout 与 queue 实例。
artifact-stage guard 的 main 分支严格度为 `fail-on-missing`，PR 严格度为 `fail-on-empty`；手动 `workflow_dispatch` 可用 `artifact_stage_strict_level` 覆盖。`ci_assert_artifact_stage_health.sh` 的 Markdown/JSON 输出包含低敏 `operator_summary`，用于区分可继续、需复核 warning、需补齐 artifact 的值班行动。
release-gate、backend-e2e 与 frontend-e2e 上传的发布/e2e artifacts 显式保留 `14` 天。
`scripts/ci_export_diagnostics_overview.sh` 会汇总 backend/frontend diagnostics 与 artifact guard 结果，并输出低敏 `operator_summary`，只包含状态、主行动、告警计数、guard 失败数、关注 scope 与阻塞 guard scope。

前端检查：

```bash
cd frontend
npm run lint
node --test --experimental-strip-types \
  lib/stores/chat-stream-store-utils.node.test.ts \
  app/components/workbench/runtime-debug-modal-utils.node.test.ts \
  app/components/workbench/audit-logs-modal-utils.node.test.ts \
  app/components/workbench/model-settings-modal-utils.node.test.ts \
  app/components/workbench/task-queue-diagnostics-contract.type.test.ts \
  app/components/workbench/utils.node.test.ts \
  app/components/workbench/usage-accounting.node.test.ts \
  app/components/workbench/answer-notices.node.test.ts \
  app/components/workbench/trace-flow-layout.node.test.ts \
  app/components/workbench/knowledge-base-governance-modal-utils.node.test.ts \
  app/components/workbench/knowledge-import-utils.node.test.ts \
  app/components/workbench/task-center-pagination.node.test.ts \
  app/components/workbench/workbench-runtime-notice.node.test.ts \
  app/components/workbench/workbench-ui-state.node.test.ts \
  app/components/workbench/workbench-layout.node.test.ts \
  app/components/workbench/workbench-trace-sync.node.test.ts \
  app/components/workbench/workbench-recovery.node.test.ts \
  app/runtime-dependency-contract.node.test.ts \
  app/source-file-size.node.test.ts \
  app/tasks/task-detail-page-utils.node.test.ts
```

## 需要提权的本机服务

普通沙箱下，backend 访问 `127.0.0.1:5432` PostgreSQL / Chroma 或 frontend 监听 `127.0.0.1:3001` 会经常遇到 `Operation not permitted` / `EPERM`。后续需要启动项目或跑 e2e 时，直接按流程申请提权启动：

后端，工作目录 `backend/`：

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端，工作目录 `frontend/`：

```bash
npm run dev -- --hostname 127.0.0.1 --port 3001
```

健康检查也需要提权访问本机端口：

```bash
curl -sS http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3001
```

如果提权审批因为审核通道连接中断被拒，不要绕路用等价命令规避；重新发起同一必要命令的明确审批。

## e2e 路径

[回答完整性提示](answer-completion.md)：静态 `-k answer_completion`（9 个）、独立数据库 `backend/scripts/test_answer_completion_postgres.py`（14 个；包含空流回退后的增量/回放、消息分页/筛选独立性、历史 completion 传递/隔离与旧 Trace 容错，Docker/本机 HTTP 提权并自动清理）；会话静态 `-k conversation_context`（11 个，白名单与 JSON 预算）；前端 `answer-notices.node.test.ts`（9 个，消息/任务/活动流版本优先）。浏览器用 `npx playwright test e2e/answer-completion.spec.ts --project=chromium --workers=1 --reporter=list --output=/tmp/insightagent-answer-completion-e2e-results`，需要本机服务/浏览器提权；1440px 英文/390px 中文，Enter 发送、超过一页任务、筛选、刷新、详情与返回聊天，仅业务 API fixture。

[任务终态边界](task-completion.md)：静态 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_terminal_usage`（5 个）；集成 `backend/.venv/bin/python backend/scripts/test_task_terminal_postgres.py`（10 个，需要 Docker/本机随机端口提权，自动清理）。覆盖生成结束/回退/保存跨时限、迟到决策、取消竞争、失败已知用量与汇总/导出；前端仅规划记录用 `usage-accounting.node.test.ts` 验证。仅本地模型替身，已接入 backend-e2e。

[任务成功保存专项](task-completion.md)：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_completion_atomic`（5 个静态测试）；`backend/.venv/bin/python backend/scripts/test_task_completion_postgres.py`（6 个独立 PostgreSQL 场景，需要 Docker/本机随机端口提权，自动清理）。用数据库触发器验证助手插入/会话更新失败回滚，并检查并发完成、终态/权限竞争、外部读取、回放/导出与下一轮上下文；已接入 backend-e2e，模型仅本地替身。

[任务总用量专项](usage-accounting.md)：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k usage_accounting`（8 个后端静态测试）；`backend/.venv/bin/python backend/scripts/test_usage_accounting_postgres.py`（3 个独立 PostgreSQL 场景，需 Docker/随机端口提权，自动清理）；前端计算专项 `usage-accounting.node.test.ts`（6 个，已纳入 release gate）。核对多轮任务的 summary/dashboard/趋势/榜单/会话导出、overall 优先与旧数据回退、混合来源筛选和用户隔离；模型仅本地替身，已接入 backend-e2e。

[远端模型流结束专项](provider-stream-completion.md)：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k provider_stream_completion`（12 个静态测试）；`backend/.venv/bin/python backend/scripts/test_provider_stream_postgres.py`（6 个真实本机 HTTP/独立 PostgreSQL 场景）。后者需要 Docker/随机端口提权并自动清理，仅使用本地模型协议替身，已纳入 backend-e2e。验证部分 EOF 失败、批量 Trace 边界后的尾部、delta/导出、失败重连不重放、400 兼容回退及正常结束帧。

公开 HTTP 工具结果的模型证据专项：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k agent_tool_context`（7 个静态边界）；`backend/.venv/bin/python backend/scripts/test_agent_tool_context_postgres.py`（3 个真实本机 HTTP/独立 PostgreSQL 场景，模型为本地替身，需提权访问 Docker/随机端口，自动清理；已纳入 backend-e2e）。核对同命中数/不同正文的分支、单轮最终回答、公开字段与嵌套脱敏、Trace/delta/导出一致性。

聊天输入键盘专项为 `frontend/e2e/composer-keyboard.spec.ts`，使用 API fixture 模拟 composition/isComposing/229 确认事件、Shift+Enter 换行与正常发送；运行 `cd frontend && npx playwright test e2e/composer-keyboard.spec.ts --project=chromium --project=firefox --project=webkit --workers=1 --reporter=list --output=/tmp/insightagent-composer-keyboard-results`，需要前端服务、本机端口及浏览器提权。三浏览器各覆盖 1440px/390px；这不代替操作系统输入法人工验收。新 spec 自动纳入 frontend full Chromium 发现范围。

[Agent 核心对齐](agent-core-alignment.md)：静态反馈边界用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k agent_feedback`；会话和模型证据专项分别为 `-k conversation_context`、`-k agent_knowledge_context`。核心场景用 `backend/.venv/bin/python backend/scripts/test_agent_core_scenarios_postgres.py`（独立 PostgreSQL/Chroma、实际知识写入/检索与本地 Provider，自动清理；已进入 backend-e2e）；持久化/条件分支/必填输入与绑定/实际输入防重复/非法图规划用量/取消用 `backend/.venv/bin/python backend/scripts/test_agent_feedback_postgres.py`（16 个；需提权访问 Docker/随机本机端口，独立 PostgreSQL 与本地模型替身，自动清理）。前端专项为 `e2e/trace-flow.spec.ts` 和知识文件导入 `e2e/knowledge-import.spec.ts`，业务 API 全部使用 fixture，需临时前端服务与浏览器权限。文件解码/预算专项为 `knowledge-import-utils.node.test.ts`，已进入 frontend node 门禁。

[步骤恢复（实验功能）](task-checkpoints.md)专项使用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_checkpoint`；实际快照复用、幂等、失败重试与取消/超时用 `backend/.venv/bin/python backend/scripts/test_task_checkpoint_postgres.py`，需提权访问 Docker/随机本机端口，独立 PostgreSQL/mock 自动清理，已接入 backend-e2e workflow。前端专项为 `e2e/task-checkpoints.spec.ts`，桌面/手机截图输出到 `/tmp`。


[HTTP 读取并发](http-read-parallel.md)专项用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k http_parallel`；真实本机 HTTP 的重叠、模板、503 重试、结果绑定、Trace/delta/export、取消与超时用 `backend/.venv/bin/python backend/scripts/test_http_parallel_postgres.py`。需要提权访问 Docker/随机本机端口，使用独立 PostgreSQL 和临时 HTTP fixture，自动清理，不请求真实供应商；已接入 backend-e2e workflow。

[工具依赖与结果引用](tool-dependencies.md)专项用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_dependency`；实际 Provider 规划、重复工具、Trace/delta/export、失败审计和依赖生命周期用 `backend/.venv/bin/python backend/scripts/test_tool_dependencies_postgres.py`，需要提权访问 Docker/随机本机端口，使用独立 PostgreSQL 与本地规划 fixture，自动清理，不请求远端模型。已接入 backend-e2e workflow。

[任务内工具并发](task-tool-parallel.md)默认 `TASK_TOOL_MAX_CONCURRENT=1`（串行）；设为 2 可验证内建独立检索/计算组合。静态专项使用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_parallel`；真实任务生命周期与导出用 `backend/.venv/bin/python backend/scripts/test_task_parallel_postgres.py`，需要 Docker/随机本机端口及提权，独立 PostgreSQL 与 mock，自动清理。已接入 backend-e2e workflow。

[任务分支重跑](task-reruns.md)专项用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_rerun`；原子创建、并发幂等、来源删除及既有 stream/export 闭环用 `backend/.venv/bin/python backend/scripts/test_task_rerun_postgres.py`。后者需要提权访问 Docker/随机本机端口，使用独立临时 PostgreSQL 和 mock，测试后清理；已加入 backend-e2e workflow。

Docker 依赖通常已启动，可先普通查看：

```bash
docker compose ps
```

backend/frontend 服务启动后，e2e 需要访问本机端口，直接申请提权运行：

```bash
bash scripts/ci_run_backend_e2e.sh --phase main --base-url http://127.0.0.1:8000 --log-dir /tmp
bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001
```

低并发队列专项 e2e 需要单独启动一个 backend，避免影响默认 full Chromium 并发基线：

```bash
TASK_QUEUE_MAX_CONCURRENT=1 TASK_QUEUE_POLL_INTERVAL_SEC=0.1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
bash scripts/ci_run_backend_e2e.sh --phase queue --base-url http://127.0.0.1:8011 --log-dir /tmp
```

低并发前端队列专项需要同时启动 backend 与 frontend，并让 frontend 指向 `8011`。backend 与 frontend 是两个长驻会话；测试脚本从仓库根目录单独运行：

```bash
TASK_QUEUE_MAX_CONCURRENT=1 TASK_QUEUE_POLL_INTERVAL_SEC=0.1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8011 npm run dev -- --hostname 127.0.0.1 --port 3001
bash scripts/ci_run_frontend_e2e.sh --phase queue --api-base-url http://127.0.0.1:8011 --frontend-base-url http://127.0.0.1:3001
```

单条 Chromium 复验在 `frontend/` 下运行，也需要提权：

```bash
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 npm run test:e2e -- e2e/workbench-remote-errors.spec.ts:527
```

跑完后停止本轮启动的 backend/frontend 会话，并确认端口无残留：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3001 -sTCP:LISTEN
```

## 提交路径

当前环境普通 `git add` / `git commit` 经常失败：

```text
fatal: Unable to create '.git/index.lock': Operation not permitted
```

后续提交可以在确认 diff 后直接申请提权 stage/commit。因为 `.cursor/` 被 ignore，实时计划文件需要强制 add：

```bash
git add README.md backend/README.md frontend/README.md <changed-files>
git add -f .cursor/plans/insightagent_开发计划_306e7915.plan.md
git diff --cached --check
git diff --cached -- data/insightagent.plan.back.md
git commit -m "<message>"
```

提交后最终核对：

```bash
git status --short
git log -1 --oneline
git diff -- data/insightagent.plan.back.md
git status --short --ignored .cursor/plans/insightagent_开发计划_306e7915.plan.md
```
