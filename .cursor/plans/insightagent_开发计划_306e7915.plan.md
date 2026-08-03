---
name: InsightAgent 开发计划
overview: real-tool-execution 与 queue-and-concurrency-lite 当前验收基线均已完成收尾；tool-runtime-productionization 已归档，不再作为活跃 spec 维护。
current_focus:
  - 当前核心主线：concurrency-fairness-policy；进度约 99.8%；已完成可选按用户/按 session 并发执行槽位上限，默认 0 关闭，开启后同用户/同会话上限不会阻塞其他用户/会话；等待队列已保持 capacity-aware oldest eligible FIFO，槽位紧张时新任务不会抢在已可执行的旧等待任务前面，空槽足够时仍可并行填充，并已补同一 active task 重复 acquire 的非拥有 slot 释放防护、旧等待项互斥 eligibility 容量估算与旧等待项预占 scope quota 后的当前任务准入判断；settings 已暴露只读 task_queue_diagnostics，包含全局、当前用户与可选 current session active/waiting/available 安全计数，其中当前用户 available 会按全局空槽与 per-user 剩余额度共同收敛，当前会话 available 会按全局空槽与 per-session 剩余额度共同收敛；同时包含基础计数字段存在性、governance 必填字段、当前用户/当前会话限额触顶、has_waiting_tasks/saturated 一致性、pressure_state 派生一致性、waiting_policy 与 capacity-aware FIFO 标记，前端运行设置已带 activeSessionId 展示队列 fairness/运行态/当前用户与当前会话计数/可用槽位/限额触顶/压力状态/等待策略摘要，前端 TaskQueueDiagnostics 类型已将 waiting_policy 与 capacity_aware_fifo_enabled 收紧为必填，后端 SettingsSummaryResponse 已用 TaskQueueDiagnosticsSummary typed 契约固定 required governance 字段且保持 scope 字段 optional，settings URL helper 已覆盖 API base 尾斜杠归一化与 encoded session_id，backend queue e2e 脚本已加入 idle/压力诊断断言并复用已被 slice 覆盖的安全 queue snapshot helper、queued SSE queue snapshot 基础字段与结构一致性、has_waiting_tasks/saturated/pressure_state 一致性、当前用户/当前会话可用槽位一致性、available slots 字段依赖与治理字段必填校验；backend queue e2e 已本轮 fresh 复验，frontend queue phase 与 full Chromium 保持上一轮 fresh 复验结果，外部 SSE / trace / export shape 保持不变
  - queue-and-concurrency-lite 首轮主线已完成：queued 状态标准化、label/rank、create 默认 queued、进程内执行槽位、queued SSE state、安全 queue snapshot、queued cancel 等待项移除、前端排队位置展示、queued recover/cancel Chromium 专项、running cancel 终态专项、Task Center session/global 多任务隔离、刷新后后台会话 stream 不误恢复、低并发 backend/frontend queue phase 与完整 Chromium 均已 fresh 复验
  - pre-flight cleanup 已完成文档瘦身、test_tool_runtime_slice 主题拆分与 tool_runtime.py planner/execution/HTTP JSON/registry facade 拆分；当前 facade 约 3.0k 行，继续开发时保持原测试入口命令不变
  - registry-governance 作为维护线，继续统一 selected source、settings/preflight、tool details、per-tool diagnostics、runtime semantic、trace/export 语义
  - rag-governance-hardening 作为后续候选，补知识库版本化、来源治理与更细粒度 shared 规则
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
  - 测试/e2e/启动/提交先按 docs/development-runbook.md 使用固定依赖与提权边界，避免重复用失败探测环境
validation_baseline:
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1756/1756)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (76/76)
  frontend_type_contract: npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  backend_e2e_queue: TASK_QUEUE_MAX_CONCURRENT=1 backend 上 queue phase fresh passed this round (queued cancel + safe wait_position + settings global/current-user/current-session active/waiting/available counts + followup completion); helper now also checks queued snapshot structure consistency, scope available slots field dependencies, and required governance diagnostics fields
  frontend_queue_phase: low-concurrency backend/frontend scripts/ci_run_frontend_e2e.sh --phase queue fresh passed this round (1 passed); default full skips this low-concurrency-only test
  frontend_running_cancel_chromium: default backend/frontend targeted Chromium passed (running task cancel reaches server terminal state and clears live UI)
  frontend_multitask_task_center_chromium: default backend/frontend targeted Chromium passed (task center separates active session tasks from global concurrent tasks)
  frontend_reload_isolation_chromium: default backend/frontend targeted Chromium passed (reload keeps background session stream detached until that session is active)
  frontend_chromium_e2e: full Chromium fresh passed this round, 50 passed / 1 skipped against real backend/frontend services
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: concurrency-fairness-policy 本轮增量：先补后端 schema 红测，锁住 SettingsSummaryResponse.task_queue_diagnostics 不再退回宽泛 dict，并补 required governance 字段与 optional scope 字段契约；随后用 TaskQueueDiagnosticsSummary TypedDict 收紧后端响应模型，保持实际 JSON 为普通 dict 且默认响应不新增 current_* 空字段，不改变外部 SSE / trace / export shape。已通过 targeted schema test、settings slice 200/200、完整 backend slice 1757/1757、前端 type contract、完整 frontend node tests 76/76、frontend lint、backend queue e2e phase fresh；本轮启动的 8011 服务已 Ctrl+C 正常退出，8011 端口残留检查无输出。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档压缩为当前状态、验证基线、下一主线、维护前置项和稳定契约，不再保留流水账。
  - id: test-runtime-slice-split
    status: completed
    content: backend/scripts/test_tool_runtime_slice.py 已缩为兼容入口，测试主体拆到 backend/scripts/tool_runtime_slice/ 主题 mixin；二次细分后入口 363 行、最大主题模块约 4.7k 行，原入口命令保持不变。
  - id: tool-runtime-facade-split
    status: completed
    content: app/services/tool_runtime.py planner、execution、HTTP JSON、registry facade 拆分已完成，planner/provider planner 抽到 app/services/tool_runtime_planning.py，runtime context/result/attempt/trace/rag/plan-item execution 抽到 app/services/tool_runtime_execution.py，HTTP JSON/diagnostics 抽到 app/services/tool_runtime_http_json.py，registry/file-backed/provider-source 治理抽到 app/services/tool_runtime_registry.py；下一轮不再继续拆分。
  - id: queue-and-concurrency-lite
    status: completed
    content: 首轮主线完成；已补 queued 状态标准化、label/rank、stream gate、create 默认 queued、进程内执行槽位、queued wait SSE state、安全 queue snapshot、queued cancel 等待项移除、前端排队位置展示、queued recover 初始 phase、低并发 backend/frontend queue phase、前端 queued recover/cancel Chromium 专项、running cancel 终态专项、Task Center session/global 多任务隔离、刷新后后台会话 stream 不误恢复与完整 Chromium 复验；后续按用户/按 session 并发策略可作为新主线增量推进。
  - id: concurrency-fairness-policy
    status: in_progress
    content: 当前核心主线，约 99.8%；已完成可选 TASK_QUEUE_MAX_CONCURRENT_PER_USER / TASK_QUEUE_MAX_CONCURRENT_PER_SESSION 执行槽位上限、capacity-aware oldest eligible FIFO 防插队、duplicate active task 非拥有 slot 释放防护、旧等待项互斥 eligibility 容量估算、旧等待项预占 scope quota 后的当前任务准入判断、queued SSE queue snapshot 基础字段存在性与结构一致性、settings task_queue_diagnostics 限额/基础字段存在性/governance 必填字段/全局与当前用户/当前会话 active/waiting/available 安全计数/当前用户与当前会话限额触顶/has_waiting_tasks/saturated/pressure_state 派生一致性/等待策略诊断、scope available slots 字段依赖、前端 diagnostics 类型契约、后端 SettingsSummaryResponse typed diagnostics 契约、前端 settings session URL helper 边界；前端运行设置可观测入口、backend queue e2e-like idle/压力诊断断言、安全 queue snapshot helper、当前用户/当前会话可用槽位一致性覆盖与本轮真实低并发 backend queue e2e fresh 复验完成，frontend queue phase/full Chromium 保持上一轮 fresh 复验，默认关闭并保持 SSE / trace / export 外形稳定；下一步主要是最终 diff/文档/提交收口。
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
- `queue-and-concurrency-lite` 首轮主线已完成。进入主线前的文档瘦身、测试文件拆分与 `tool_runtime.py` facade 拆分已完成；队列可观测、取消/恢复细化、低并发 backend/frontend queue phase、前端 queued recover/cancel Chromium 专项、running cancel 终态专项、Task Center session/global 多任务隔离、刷新后后台会话 stream 不误恢复与完整 Chromium 复验均已收口，`queued` 已进入后端状态标准化、label/rank、create 默认状态、进程内执行槽位、SSE 等待 state、queued cancel 等待项移除与前端排队位置展示。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程直接提权，避免每轮重复触发权限失败。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出：覆盖常见 REST/JS 字段别名、GraphQL connection、Elastic/OpenSearch hits、Azure/OData、organic search、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1756/1756`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Backend e2e queue phase：`TASK_QUEUE_MAX_CONCURRENT=1` backend 上 queued cancel / queued SSE safe wait_position、settings safe global/current-user active/waiting/available counts、基础计数字段存在性、governance 必填字段、has_waiting_tasks/saturated/pressure_state/current-user limit 与 available 一致性 / followup completion 本轮 fresh 通过；脚本现额外校验 queued snapshot 基础计数字段、结构一致性、current session diagnostics、settings `task_queue_diagnostics` 与 scope available slots 字段依赖。
- Frontend node tests：workbench utils / stream store utils / model settings utils，当前 `76/76`。
- Frontend type contract：TaskQueueDiagnostics governance 字段必填契约通过。
- Frontend queue phase：低并发 backend/frontend 下 selected session 恢复 queued 任务、Inspector 排队位置与 queued cancel 本轮 fresh 通过；默认 full Chromium 下该专项显式 skip。
- Frontend running cancel Chromium：默认 backend/frontend 下 UI cancel 后服务端 terminal、Inspector phase 与 composer 恢复通过。
- Frontend multi-task Chromium：默认 backend/frontend 下 Task Center 当前会话与全局多任务隔离通过。
- Frontend reload isolation Chromium：默认 backend/frontend 下刷新后后台会话 stream 不误恢复、切回原会话恢复并可取消通过。
- Frontend Chromium e2e：真实 backend/frontend 服务下 full 本轮 fresh 复跑 `50 passed / 1 skipped`；低并发 queued 专项在 full 阶段按预期 skip。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 最近完成主线：queue-and-concurrency-lite

目标：把任务执行从“单次请求跑通”推进到“多任务、多会话、取消/恢复都可靠”。

首轮建议契约：

1. 后端状态模型：`queued / running / completed / failed / cancelled / timeout`；`queued` 标准化、label/rank、create 默认 queued 与 stream gate 已完成。
2. 单机队列：进程内执行槽位、默认 `TASK_QUEUE_MAX_CONCURRENT=32` 与安全等待诊断已完成，低并发排队语义由 slice 覆盖，后续扩到按用户/按 session。
3. 取消语义：queued 任务可取消且会移出等待队列，已有低并发 backend queue e2e 与前端 queued cancel Chromium 专项；running cancel 已补前端终态专项，继续保持现有 cancel/timeout 外部契约。
4. 恢复语义：刷新或 reconnect 时区分 queued、running、terminal，前端 queued recover 初始 phase、selected session 恢复与后台会话 stream 不误恢复专项已通过，不改变外部 SSE / trace / export shape。
5. 前端体验：active task 识别已扩到 `queued/pending/running`，live phase 已能显示当前任务排队位置，并在 terminal/local cancel 时清理 queue snapshot；Task Center 当前会话/全局多任务隔离与刷新后跨 session 深水位体验已补专项。
6. e2e：backend queue phase、frontend queue phase、前端 queued recover/cancel、running cancel、Task Center 多任务、刷新恢复隔离与完整 Chromium 已覆盖取消/恢复/隔离基线；首轮主线 fresh 收尾复验已通过。

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
