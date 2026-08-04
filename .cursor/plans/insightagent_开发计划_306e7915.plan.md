---
name: InsightAgent 开发计划
overview: real-tool-execution 与 queue-and-concurrency-lite 当前验收基线均已完成收尾；tool-runtime-productionization 已归档，不再作为活跃 spec 维护。
current_focus:
  - 当前无新主线开发；concurrency-fairness-policy 已 100% 封板，默认关闭 per-user/per-session 限额并保持外部 SSE / trace / export shape 稳定。
  - 已封板主线：real-tool-execution、queue-and-concurrency-lite、concurrency-fairness-policy。
  - 进入下一主线前保持四份活跃文档瘦身，只保留当前状态、验证基线、稳定契约和少量高信号摘要。
  - 候选下一主线：registry-governance；后续候选：rag-governance-hardening。
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
  - 测试/e2e/启动/提交先按 docs/development-runbook.md 使用固定依赖与提权边界，避免重复用失败探测环境
validation_baseline:
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1776/1776)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (76/76)
  frontend_type_contract: npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  backend_e2e_queue: TASK_QUEUE_MAX_CONCURRENT=1 backend 上 queue phase current-turn fresh passed (queued cancel + safe wait_position + settings global/current-user/current-session active/waiting/available counts + followup completion); helper now also checks queued snapshot structure consistency, queued snapshot count/wait_position/scope count integer types, scope available slots field dependencies, scope active/waiting count bounds, typed integer settings max_concurrent/counts/governance limits, numeric poll interval, exact pressure_state enum values, typed boolean settings status/governance flags, non-negative governance limits, and required governance diagnostics fields
  frontend_queue_phase: low-concurrency backend/frontend scripts/ci_run_frontend_e2e.sh --phase queue latest fresh passed (1 passed); default full skips this low-concurrency-only test
  frontend_running_cancel_chromium: default backend/frontend targeted Chromium passed (running task cancel reaches server terminal state and clears live UI)
  frontend_multitask_task_center_chromium: default backend/frontend targeted Chromium passed (task center separates active session tasks from global concurrent tasks)
  frontend_reload_isolation_chromium: default backend/frontend targeted Chromium passed (reload keeps background session stream detached until that session is active)
  frontend_chromium_e2e: full Chromium current-turn fresh passed, 50 passed / 1 skipped against real backend/frontend services
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: concurrency-fairness-policy 已封板；最新完整 Chromium fresh 为 50 passed / 1 skipped，backend queue/settings/full slice 与 frontend node/type/lint 均保持通过。当前轮只做四文档瘦身同步，不进入下一主线。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档只保留当前状态、验证基线、候选下一主线、稳定契约和少量高信号摘要。
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
  - id: registry-governance
    status: in_progress
    content: 维护线；保持 registry / profile / provider source / selected source / diagnostics_summary / loader_factory 的统一治理语义。
  - id: rag-governance-hardening
    status: pending
    content: 后续补知识库版本化、来源治理与更细粒度 shared 规则。
logging_rule: 本计划文件只保存当前作战地图和少量高信号里程碑，不再保存按天流水账。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `tool-runtime-productionization` 已归档；当前活跃判断以代码、三份 README 与本计划文件为准。
- `real-tool-execution` 当前验收基线已完成：provider/source/settings/file-backed 组合中的 real search / real calc 已稳定贯通真实上游协议、preview/output/result-summary、trace/observation/export 与 e2e 回归。
- `queue-and-concurrency-lite` 与 `concurrency-fairness-policy` 已封板：queued 状态、进程内执行槽位、capacity-aware FIFO、可选 per-user/per-session 限额、settings diagnostics、前端可观测入口与 e2e 基线均已收口。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程直接提权，避免每轮重复触发权限失败。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出：覆盖常见 REST/JS 字段别名、GraphQL connection、Elastic/OpenSearch hits、Azure/OData、organic search、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1776/1776`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Backend e2e queue phase：`TASK_QUEUE_MAX_CONCURRENT=1` backend 上 queued cancel / queued SSE safe wait_position、settings safe global/current-user active/waiting/available counts、基础计数字段存在性、queued snapshot count/wait_position/scope count 整数类型、整数型 max_concurrent/计数/治理限额字段、数值型 poll interval、精确 pressure_state 枚举、布尔型状态/治理标记、非负治理限额、governance 必填字段、has_waiting_tasks/saturated/pressure_state 必填、固定枚举值与派生一致性、current-user limit 与 available 一致性 / followup completion latest fresh 通过；脚本现额外校验 queued snapshot 基础计数字段、结构一致性、current session diagnostics、settings `task_queue_diagnostics`、scope available slots 字段依赖与 scope active/waiting 计数全局上界。
- Frontend node tests：workbench utils / stream store utils / model settings utils，当前 `76/76`。
- Frontend type contract：TaskQueueDiagnostics 基础运行态计数、governance 字段必填与 pressure_state/waiting_policy 枚举契约通过。
- Frontend queue phase：低并发 backend/frontend 下 selected session 恢复 queued 任务、Inspector 排队位置与 queued cancel 最近 fresh 通过；默认 full Chromium 下该专项显式 skip。
- Frontend running cancel Chromium：默认 backend/frontend 下 UI cancel 后服务端 terminal、Inspector phase 与 composer 恢复通过。
- Frontend multi-task Chromium：默认 backend/frontend 下 Task Center 当前会话与全局多任务隔离通过。
- Frontend reload isolation Chromium：默认 backend/frontend 下刷新后后台会话 stream 不误恢复、切回原会话恢复并可取消通过。
- Frontend Chromium e2e：真实 backend/frontend 服务下 full latest fresh 复跑 `50 passed / 1 skipped`；低并发 queued 专项在 full 阶段按预期 skip。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 最近封板主线

- `queue-and-concurrency-lite`：queued 状态、进程内执行槽位、queued cancel、恢复/隔离与低并发/full e2e 基线已收口。
- `concurrency-fairness-policy`：可选 per-user/per-session 限额、capacity-aware FIFO、settings diagnostics、typed 契约与 full Chromium 封板复验已收口。

## Pre-flight Cleanup

- 文档瘦身：四份活跃文档只保留当前状态、当前验证基线、下一主线、稳定契约与少量高信号能力摘要。
- 测试拆分：`backend/scripts/test_tool_runtime_slice.py` 已缩为兼容入口，测试主体拆到 `backend/scripts/tool_runtime_slice/` mixin 包并保持原入口命令不变；入口 363 行，最大主题模块约 4.7k 行。
- 主题包摘要：provider/source、planner、settings/registry、http_json request/response/mapping/error、task trace/export/session/usage、registry governance/file diagnostics/runtime models、runtime result/attempt/observation/rag execution。
- `tool_runtime.py` 拆分放在测试拆分之后分阶段推进，优先抽旁路模块并保留现有 import facade；planner 已抽到 `backend/app/services/tool_runtime_planning.py`，runtime context/result/attempt/trace/rag/plan-item execution 已抽到 `backend/app/services/tool_runtime_execution.py`，HTTP JSON/diagnostics 已抽到 `backend/app/services/tool_runtime_http_json.py`，registry/file-backed/provider-source 治理已抽到 `backend/app/services/tool_runtime_registry.py`；pre-flight 拆分到此收口。

## 后续维护线

- `registry-governance`：继续统一 selected source、settings/preflight、tool details、per-tool diagnostics、runtime semantic、trace/search/export 的安全摘要与错误语义。
- `rag-governance-hardening`：补知识库版本化、来源治理与更细粒度 shared 规则。
- 新 provider/source 协议：按 `real-tool-execution` 已完成验收基线增量补红测和局部归一化，不扩大外部契约。

## 维护约定

- 本计划文件是实时快照，不是历史日志仓库。
- 重要历史事实保留为摘要；旧失败过程、重复验证清单和按轮流水账不继续堆积。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
