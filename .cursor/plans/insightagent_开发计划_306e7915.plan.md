---
name: InsightAgent 开发计划
overview: real-tool-execution、queue-and-concurrency-lite、concurrency-fairness-policy、registry-governance 与 rag-governance-hardening 均已封板；当前主线为 production-reliability-hardening。
current_focus:
  - 当前主线：production-reliability-hardening，进度约 48%；已完成 queue scope cleanup、session delete waiting cleanup、startup orphan running cleanup、execution owner/heartbeat 归属治理、stale heartbeat 接管开关、active stream race 防双执行与 terminal start/wait race 防误复活。
  - 最近封板主线：rag-governance-hardening 已 100% 封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口均已完成治理收口。
  - 最近封板主线：registry-governance；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口。
  - 已封板主线：real-tool-execution、queue-and-concurrency-lite、concurrency-fairness-policy、registry-governance、rag-governance-hardening。
  - 本轮新增 terminal wait race 治理：等待执行槽位时只允许 pending/queued 切 queued；若 queued mark 竞争失败，不继续等待，也不覆盖 terminal DB 状态。
  - 后续候选方向为 rag-product-experience、observability-experience、provider-tool-expansion、ci-release-engineering。
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
  - 测试/e2e/启动/提交先按 docs/development-runbook.md 使用固定依赖与提权边界，避免重复用失败探测环境
  - 控制单文件规模，新增测试/实现优先落到主题文件；主题文件明显膨胀时先拆新文件/新模块，沿用 test_tool_runtime_slice 与 tool_runtime facade 拆分经验
validation_baseline:
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1924/1924)
  backend_production_reliability_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability (20/20)
  backend_queue_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue (66/66)
  backend_task_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task (356/356)
  backend_settings_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings (216/216)
  backend_rag_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag (78/78)
  backend_rag_route_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route (2/2)
  backend_result_summary_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary (30/30)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (77/77)
  frontend_lint: cd frontend && npm run lint
  frontend_type_contract: npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  backend_e2e_queue: TASK_QUEUE_MAX_CONCURRENT=1 backend 上 queue phase current-turn fresh passed (queued cancel + safe wait_position + settings diagnostics + followup completion + typed queue governance checks)
  frontend_queue_phase: low-concurrency backend/frontend scripts/ci_run_frontend_e2e.sh --phase queue current-turn fresh passed (1 passed); default full skips this low-concurrency-only test
  frontend_running_cancel_chromium: default backend/frontend targeted Chromium passed (running task cancel reaches server terminal state and clears live UI)
  frontend_multitask_task_center_chromium: default backend/frontend targeted Chromium passed (task center separates active session tasks from global concurrent tasks)
  frontend_reload_isolation_chromium: default backend/frontend targeted Chromium passed (reload keeps background session stream detached until that session is active)
  frontend_chromium_e2e: full Chromium current-turn fresh passed, 50 passed / 1 skipped against real backend/frontend services
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: production-reliability-hardening 进度约 48%；本轮新增 terminal wait race 防误复活；production_reliability 20/20、queue 66/66、task 356/356、settings 216/216、backend full slice 1924/1924、相关 py_compile 通过；本轮未重跑 frontend/e2e；data/insightagent.plan.back.md 无 diff。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档只保留当前状态、验证基线、后续候选主线、稳定契约和少量高信号摘要。
  - id: test-runtime-slice-split
    status: completed
    content: backend/scripts/test_tool_runtime_slice.py 已缩为兼容入口，测试主体拆到 backend/scripts/tool_runtime_slice/ 主题 mixin；二次细分后入口 363 行、最大主题模块约 4.7k 行，原入口命令保持不变。
  - id: tool-runtime-facade-split
    status: completed
    content: app/services/tool_runtime.py planner、execution、HTTP JSON、registry facade 拆分已完成，planner/provider planner 抽到 app/services/tool_runtime_planning.py，runtime context/result/attempt/trace/rag/plan-item execution 抽到 app/services/tool_runtime_execution.py，HTTP JSON/diagnostics 抽到 app/services/tool_runtime_http_json.py，registry/file-backed/provider-source 治理抽到 app/services/tool_runtime_registry.py；下一轮不再继续拆分。
  - id: queue-and-concurrency-lite
    status: completed
    content: 已封板；queued 状态、进程内执行槽位、安全 queue snapshot、queued cancel、恢复/隔离与低并发/full e2e 基线均已收口。
  - id: concurrency-fairness-policy
    status: completed
    content: 已 100% 封板；per-user/per-session 限额默认关闭，capacity-aware FIFO、settings diagnostics、前后端 typed 契约、backend queue e2e 与 full Chromium 基线均已收口，外部 SSE / trace / export shape 保持稳定。
  - id: development-runbook
    status: completed
    content: 新增 docs/development-runbook.md 并同步 AGENTS/README/backend/frontend/实时计划，固化 backend venv、frontend npm、本机端口/e2e 提权与 .git/index.lock 提交流程。
  - id: single-file-size-governance
    status: completed
    content: 新增单文件规模治理规则；后续不把历史大文件作为默认追加点，测试/实现优先进入主题文件，必要时先拆新主题文件或新模块。
  - id: registry-governance
    status: completed
    content: 已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口；通过 backend/full frontend/e2e fresh 复验。
  - id: rag-governance-hardening
    status: completed
    content: 已 100% 封板；RAG 来源/metadata、版本摘要、知识库标识、reserved alias、shared/private 边界、route/runtime trace/export/display、错误出口、前端治理表和 trace 搜索均已完成治理收口并通过完整复验。
  - id: next-mainline-candidates
    status: completed
    content: 已选择 production-reliability-hardening 作为当前主线；其余候选保留为后续方向。
  - id: production-reliability-hardening
    status: in_progress
    content: 进度约 48%；已完成 queue scope cleanup、session delete waiting cleanup、startup orphan running cleanup、execution owner/heartbeat 归属治理、stale heartbeat 接管开关、active stream race 防双执行与 terminal start/wait race 防误复活。下一步优先围绕异常退出后的队列清理、持久化边界、失败自愈与 e2e 稳定性补红测。
logging_rule: 本计划文件只保存当前作战地图和少量高信号里程碑，不再保存按天流水账。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `tool-runtime-productionization` 已归档；当前活跃判断以代码、三份 README 与本计划文件为准。
- `real-tool-execution` 当前验收基线已完成：provider/source/settings/file-backed 组合中的 real search / real calc 已稳定贯通真实上游协议、preview/output/result-summary、trace/observation/export 与 e2e 回归。
- `queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance` 与 `rag-governance-hardening` 已封板：queued 状态、进程内执行槽位、capacity-aware FIFO、可选 per-user/per-session 限额、settings diagnostics、前端可观测入口、registry/provider source 治理、RAG 来源/版本/shared 边界治理与 e2e 基线均已收口。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程先普通尝试，失败后按 runbook 提权。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出：覆盖常见 REST/JS 字段别名、GraphQL connection、Elastic/OpenSearch hits、Azure/OData、organic search、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1924/1924`。
- Backend production reliability slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability`，当前 `20/20`。
- Backend queue slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue`，当前 `66/66`。
- Backend task slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task`，当前 `356/356`。
- Backend settings slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings`，当前 `216/216`。
- Backend RAG slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag`，当前 `78/78`。
- Backend RAG route slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route`，当前 `2/2`。
- Backend result summary slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary`，当前 `30/30`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Backend e2e queue phase：`TASK_QUEUE_MAX_CONCURRENT=1` backend 上 queued cancel、queued SSE safe wait_position、settings diagnostics、typed queue governance checks 与 followup completion current-turn fresh 通过。
- Frontend node tests：workbench utils / stream store utils / model settings utils，当前 `77/77`。
- Frontend lint：`cd frontend && npm run lint` 通过。
- Frontend type contract：TaskQueueDiagnostics 基础运行态计数、governance 字段必填与 pressure_state/waiting_policy 枚举契约通过。
- Frontend queue phase：低并发 backend/frontend 下 selected session 恢复 queued 任务、Inspector 排队位置与 queued cancel current-turn fresh 通过；默认 full Chromium 下该专项显式 skip。
- Frontend running cancel Chromium：默认 backend/frontend 下 UI cancel 后服务端 terminal、Inspector phase 与 composer 恢复通过。
- Frontend multi-task Chromium：默认 backend/frontend 下 Task Center 当前会话与全局多任务隔离通过。
- Frontend reload isolation Chromium：默认 backend/frontend 下刷新后后台会话 stream 不误恢复、切回原会话恢复并可取消通过。
- Frontend Chromium e2e：本轮真实 backend/frontend 服务下 full 基线 `50 passed / 1 skipped`；低并发 queued 专项在 full 阶段按预期 skip，已由 frontend queue phase 单独覆盖。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 最近封板主线

- `queue-and-concurrency-lite`：queued 状态、进程内执行槽位、queued cancel、恢复/隔离与低并发/full e2e 基线已收口。
- `concurrency-fairness-policy`：可选 per-user/per-session 限额、capacity-aware FIFO、settings diagnostics、typed 契约与 full Chromium 封板复验已收口。
- `registry-governance`：已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口，不改变 settings/preflight/trace/export/audit/SSE 可见字段 shape。

## Pre-flight Cleanup

- 文档瘦身：四份活跃文档只保留当前状态、当前验证基线、下一主线、稳定契约与少量高信号能力摘要。
- 测试拆分：`backend/scripts/test_tool_runtime_slice.py` 已缩为兼容入口，测试主体拆到 `backend/scripts/tool_runtime_slice/` mixin 包并保持原入口命令不变；`registry_provider_source_aliases.py` 承接 provider source 冲突 alias 可回写测试，避免继续膨胀既有 settings/task usage 长文件。
- 主题包摘要：provider/source、planner、settings/registry、http_json request/response/mapping/error、task trace/export/session/usage、registry governance/file diagnostics/runtime models、runtime result/attempt/observation/rag execution。
- `tool_runtime.py` 拆分放在测试拆分之后分阶段推进，优先抽旁路模块并保留现有 import facade；planner 已抽到 `backend/app/services/tool_runtime_planning.py`，runtime context/result/attempt/trace/rag/plan-item execution 已抽到 `backend/app/services/tool_runtime_execution.py`，HTTP JSON/diagnostics 已抽到 `backend/app/services/tool_runtime_http_json.py`，registry/file-backed/provider-source 治理已抽到 `backend/app/services/tool_runtime_registry.py`；pre-flight 拆分到此收口。

## 后续维护线

- 当前主线为 `production-reliability-hardening`，进度约 `48%`；后续继续以先红测、再实现、再 targeted/full slice 的方式推进。
- 后续候选主线：`rag-product-experience`、`observability-experience`、`provider-tool-expansion`、`ci-release-engineering`；正式开启前先补主线验收边界和首批红测计划。
- 新 provider/source 协议：按 `real-tool-execution` 已完成验收基线增量补红测和局部归一化，不扩大外部契约。

## 维护约定

- 本计划文件是实时快照，不是历史日志仓库。
- 重要历史事实保留为摘要；旧失败过程、重复验证清单和按轮流水账不继续堆积。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
