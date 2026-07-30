---
name: InsightAgent 开发计划
overview: real-tool-execution 当前验收基线已完成收尾；下一核心主线切到 queue-and-concurrency-lite。tool-runtime-productionization 已归档，不再作为活跃 spec 维护。
current_focus:
  - 下一核心主线：单机任务排队、并发治理、queued/running/cancel/recover 状态机与 e2e
  - pre-flight cleanup 已完成文档瘦身与 test_tool_runtime_slice 主题拆分；tool_runtime.py planner/execution/HTTP JSON facade 拆分已推进，当前 facade 约 7.2k 行，继续开发时保持原测试入口命令不变
  - registry-governance 作为维护线，继续统一 selected source、settings/preflight、tool details、per-tool diagnostics、runtime semantic、trace/export 语义
  - rag-governance-hardening 作为后续候选，补知识库版本化、来源治理与更细粒度 shared 规则
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
validation_baseline:
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1710/1710)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (68/68)
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  frontend_chromium_e2e: full Chromium first pass 47/47 against real backend/frontend lifecycle
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: tool_runtime.py HTTP JSON facade 拆分完成后，facade / runtime / result_summary / rag_followup / http_json / registry / tool_plan targeted tests 与完整 backend slice 1710/1710 均通过；本轮尚未重跑 full-stack e2e / Chromium e2e。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档压缩为当前状态、验证基线、下一主线、维护前置项和稳定契约，不再保留流水账。
  - id: test-runtime-slice-split
    status: completed
    content: backend/scripts/test_tool_runtime_slice.py 已缩为兼容入口，测试主体拆到 backend/scripts/tool_runtime_slice/ 主题 mixin；二次细分后入口 363 行、最大主题模块约 4.7k 行，原入口命令保持不变。
  - id: tool-runtime-facade-split
    status: in_progress
    content: app/services/tool_runtime.py planner、execution、HTTP JSON facade 拆分已完成，planner/provider planner 抽到 app/services/tool_runtime_planning.py，runtime context/result/attempt/trace/rag/plan-item execution 抽到 app/services/tool_runtime_execution.py，HTTP JSON/diagnostics 抽到 app/services/tool_runtime_http_json.py；后续仅保留 registry 候选。
  - id: queue-and-concurrency-lite
    status: pending
    content: 下一核心主线；补 queued/running/terminal 状态模型、单机队列、并发上限、queued cancel、running cancel/recover、stream reconnect 与 e2e。
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
- 下一核心主线是 `queue-and-concurrency-lite`。进入主线前的文档瘦身与测试文件拆分已完成；`backend/scripts/test_tool_runtime_slice.py` 保留为兼容入口，`tool_runtime.py` 已开始 facade 拆分并抽出 planner、execution 与 HTTP JSON 模块。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出：覆盖常见 REST/JS 字段别名、GraphQL connection、Elastic/OpenSearch hits、Azure/OData、organic search、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1710/1710`；本轮 targeted：`facade`、`runtime`、`result_summary`、`rag_followup`、`http_json`、`registry`、`tool_plan`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Frontend node tests：workbench utils / stream store utils / model settings utils，当前 `68/68`。
- Frontend Chromium e2e：真实 backend/frontend 生命周期内首跑 `47/47`。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 下一核心主线：queue-and-concurrency-lite

目标：把任务执行从“单次请求跑通”推进到“多任务、多会话、取消/恢复都可靠”。

首轮建议契约：

1. 后端状态模型：`queued / running / completed / failed / cancelled / timeout`。
2. 单机队列：全局队列 + 最小并发上限，后续再扩到按用户/按 session。
3. 取消语义：queued 任务可取消；running 任务沿用现有 cancel/timeout 契约。
4. 恢复语义：刷新或 reconnect 时区分 queued、running、terminal，不改变外部 SSE / trace / export shape。
5. 前端体验：Task Center 展示等待中/运行中/终态，composer 在 queued/running/cancel 后稳定恢复。
6. e2e：覆盖多任务并发、取消 queued、取消 running、刷新恢复、跨 session 切换。

## Pre-flight Cleanup

- 文档瘦身：四份活跃文档只保留当前状态、当前验证基线、下一主线、稳定契约与少量高信号能力摘要。
- 测试拆分：`backend/scripts/test_tool_runtime_slice.py` 已缩为兼容入口，测试主体拆到 `backend/scripts/tool_runtime_slice/` mixin 包并保持原入口命令不变；入口 363 行，最大主题模块约 4.7k 行。
- 主题包摘要：provider/source、planner、settings/registry、http_json request/response/mapping/error、task trace/export/session/usage、registry governance/file diagnostics/runtime models、runtime result/attempt/observation/rag execution。
- `tool_runtime.py` 拆分放在测试拆分之后分阶段推进，优先抽旁路模块并保留现有 import facade；planner 已抽到 `backend/app/services/tool_runtime_planning.py`，runtime context/result/attempt/trace/rag/plan-item execution 已抽到 `backend/app/services/tool_runtime_execution.py`，HTTP JSON/diagnostics 已抽到 `backend/app/services/tool_runtime_http_json.py`，后续仅保留 registry 候选。

## 后续维护线

- `registry-governance`：继续统一 selected source、settings/preflight、tool details、per-tool diagnostics、runtime semantic、trace/search/export 的安全摘要与错误语义。
- `rag-governance-hardening`：补知识库版本化、来源治理与更细粒度 shared 规则。
- 新 provider/source 协议：按 `real-tool-execution` 已完成验收基线增量补红测和局部归一化，不扩大外部契约。

## 维护约定

- 本计划文件是实时快照，不是历史日志仓库。
- 重要历史事实保留为摘要；旧失败过程、重复验证清单和按轮流水账不继续堆积。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
