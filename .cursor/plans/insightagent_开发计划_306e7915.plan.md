---
name: InsightAgent 开发计划
overview: real-tool-execution 当前验收基线已完成收尾；下一核心主线切到 queue-and-concurrency-lite。tool-runtime-productionization 已归档，不再作为活跃 spec 维护。
current_focus:
  - 当前核心主线：queue-and-concurrency-lite；已完成 queued 状态标准化、label/rank、create 默认 queued、进程内执行槽位、queued SSE state、安全 queue snapshot、queued cancel 等待项移除、前端排队位置展示、queued recover/cancel Chromium 专项与低并发 backend queue 专项 e2e，下一步补 running cancel / 多任务 / 跨 session 前端专项 e2e
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
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1719/1719)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (71/71)
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  backend_e2e_queue: TASK_QUEUE_MAX_CONCURRENT=1 backend 上 queue phase passed (queued cancel + safe wait_position + followup completion)
  frontend_queued_recover_chromium: low-concurrency backend/frontend targeted Chromium passed (queued task recovery shows queue position and can be cancelled)
  frontend_chromium_e2e: full Chromium rerun 47/47 against real backend/frontend lifecycle
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: queue-and-concurrency-lite 继续推进前端专项 e2e：新增 queued task recovery Chromium 用例，低并发 backend/frontend 下验证 selected session 恢复 queued 任务、Inspector 显示 Queued #1、cancel 后 SSE 返回 cancelled 且不误发 done；完整 backend slice 1719/1719、frontend node tests 71/71、frontend lint 与 targeted Chromium 均通过。上一基线中的 backend e2e main phase、backend queue phase、CI tooling all 与完整 Chromium 47/47 保持为最近完整常规 e2e 基线；本轮未重跑完整 Chromium。
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
    status: in_progress
    content: 当前核心主线；已补 queued 状态标准化、label/rank、stream gate、create 默认 queued、进程内执行槽位、queued wait SSE state、安全 queue snapshot、queued cancel 等待项移除、前端排队位置展示、queued recover 初始 phase、低并发 backend queue 专项 e2e 与前端 queued recover/cancel Chromium 专项，下一步补 running cancel / 多任务 / 跨 session 前端专项 e2e。
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
- 当前核心主线是 `queue-and-concurrency-lite`。进入主线前的文档瘦身、测试文件拆分与 `tool_runtime.py` facade 拆分已完成；当前已完成队列可观测、取消/恢复细化、低并发 backend queue 专项 e2e 与前端 queued recover/cancel Chromium 专项，`queued` 已进入后端状态标准化、label/rank、create 默认状态、进程内执行槽位、SSE 等待 state、queued cancel 等待项移除与前端排队位置展示。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程直接提权，避免每轮重复触发权限失败。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出：覆盖常见 REST/JS 字段别名、GraphQL connection、Elastic/OpenSearch hits、Azure/OData、organic search、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1719/1719`；本轮 targeted：`-k queue`、`-k cancel`、`-k task`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Backend e2e queue phase：`TASK_QUEUE_MAX_CONCURRENT=1` backend 上 queued cancel / safe wait_position / followup completion 已通过。
- Frontend node tests：workbench utils / stream store utils / model settings utils，当前 `71/71`。
- Frontend queued recover Chromium：低并发 backend/frontend 下 selected session 恢复 queued 任务、Inspector 排队位置与 queued cancel 通过。
- Frontend Chromium e2e：真实 backend/frontend 生命周期内最终 full 复跑 `47/47`；remote 429 单条复跑也通过。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 下一核心主线：queue-and-concurrency-lite

目标：把任务执行从“单次请求跑通”推进到“多任务、多会话、取消/恢复都可靠”。

首轮建议契约：

1. 后端状态模型：`queued / running / completed / failed / cancelled / timeout`；`queued` 标准化、label/rank、create 默认 queued 与 stream gate 已完成。
2. 单机队列：进程内执行槽位、默认 `TASK_QUEUE_MAX_CONCURRENT=32` 与安全等待诊断已完成，低并发排队语义由 slice 覆盖，后续扩到按用户/按 session。
3. 取消语义：queued 任务可取消且会移出等待队列，已有低并发 backend queue e2e 与前端 queued cancel Chromium 专项；running 任务沿用现有 cancel/timeout 契约，下一步补前端专项 e2e。
4. 恢复语义：刷新或 reconnect 时区分 queued、running、terminal，前端 queued recover 初始 phase 与 selected session 恢复专项已通过，不改变外部 SSE / trace / export shape。
5. 前端体验：active task 识别已扩到 `queued/pending/running`，live phase 已能显示当前任务排队位置，并在 terminal/local cancel 时清理 queue snapshot；下一步补 running cancel、多任务与跨 session 专项体验。
6. e2e：backend queue phase 与前端 queued recover/cancel Chromium 已覆盖 queued 基线；下一步覆盖前端多任务并发、取消 running、刷新恢复、跨 session 切换，并择机复跑完整 Chromium。

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
