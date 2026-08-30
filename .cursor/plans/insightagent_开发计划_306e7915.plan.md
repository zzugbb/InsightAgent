---
name: InsightAgent 开发计划
overview: provider-tool-expansion 与 ci-release-engineering 已 100% 封板；当前推进 production-runtime-hardening。
current_focus:
  mainline: production-runtime-hardening
  status: 35% 开发中
  latest_change: SSE error.diagnostic 与 provider task_failed audit detail 对齐低敏 reason 枚举，保留旧字段
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/scripts/tool_runtime_slice/planning_provider.py 2923 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - 默认 settings 根据 provider/model/api_key 自动选择 remote 或 canonical mock
  - SSE 事件、TraceStep、result summary、safe output、JSON/Markdown export shape 保持稳定
  - SSE error.diagnostic 与 provider failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性
  - queued/running/cancel/reconnect 与 task recovery 语义保持稳定
  - data/insightagent.plan.back.md 是只读备份计划，永远不修改
validation_baseline:
  release_gate: bash scripts/ci_run_release_gate.sh --phase auto --summary-file /tmp/release-gate-check.md --json-summary-file /tmp/release-gate-check.json passed，非 PR 保守跑 backend/frontend/tooling/hygiene 全量
  backend: full slice 1986/1986；module boundary 4/4；production_reliability 38/38；reconnect 8/8
  frontend: node tests 122/122；npm run lint passed；npm run build passed
  e2e: backend main passed；frontend full Chromium 52 passed / 1 skipped；backend/frontend queue 已纳入 CI workflow
  hygiene: py_compile、git diff --check、git diff --cached --check、backup plan diff clean
completed_mainlines:
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - source-size-maintenance：tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界
  - ci-release-engineering：静态 release gate、PR auto routing、summary artifact、readiness matrix、service-backed e2e workflow queue、artifact strict policy
next_candidate_mainlines:
  - product-ux-polish：Workbench/Task Center 高频操作、trace 回放可读性与治理页面效率
next_steps:
  - 继续收敛 provider registry 运行态诊断、远端 provider 失败可观测性与发布后回归策略
logging_rule: 本文件的状态块保持收敛；正文中的稳定能力摘要、验证口径、维护规则和主线地图不应被整段删除。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `provider-tool-expansion` 与 `ci-release-engineering` 均已 100% 封板；当前推进 `production-runtime-hardening`，进度约 35%。
- 当前生产运行态重点：SSE `error.diagnostic` 与 provider `task_failed` 审计 detail 已对齐低敏 `reason` 枚举，保留旧 `code/fatal/retryable/detail/status_code` 与 audit `status_code/retryable` 字段；后续继续收敛 provider registry 运行态诊断、远端 provider 失败可观测性与发布后回归策略。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程先普通尝试，失败后按 runbook 提权。
- 代码规模治理已纳入常规边界：`backend/app`、`backend/scripts` 与 `frontend` 源码保持单文件 <= 3000 行；`frontend/package-lock.json` 等生成锁文件不作为拆分对象。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、OpenAI Chat/Responses、Gemini/Vertex functionCall、Bedrock/Claude Converse toolUse、Anthropic Messages mixed text/tool_use content、顶层 message/delta wrapper、tool_call 单数容器、tool_calls/toolCalls 映射容器、camelCase toolCalls/toolInvocations/toolName/functionName、嵌套 tool 对象、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出与 planner 协议：覆盖常见 REST/JS 字段别名、GraphQL connection pageInfo.totalCount + edges、Elastic/OpenSearch hits、Azure/OData、Meilisearch/Algolia estimatedTotalHits / nbHits、Brave web.results、Bing webPages.totalEstimatedMatches、SearXNG/元搜索 number_of_results、Crossref/学术检索 total-results/message.items、PubMed/NCBI ESearch count/idlist、Europe PMC hitCount/resultList.result、Google Custom Search queries.request[].totalResults/items、Serper/Google Search searchInformation.totalResults/organic、引用型 citations/search_results、organic search、分页型 data/records + meta.page/pagination/paging total、安全千分位总量字符串、显式 result_fields bracket quoted 特殊字段键、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。
- release 工程：静态 release gate、PR auto routing、Markdown/JSON summary、release readiness matrix、backend/frontend queue workflow、artifact diagnostics 与 main push strict policy 已落地。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1986/1986`。
- Backend targeted：`production_reliability 38/38`、`reconnect 8/8`、registry/http_json/provider/runtime/trace/export/usage 通过。
- Module boundary：`cd backend && PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py`，当前 `4/4`，包含 3000 行规模边界。
- Frontend node tests：当前 `122/122`，包含 frontend source size boundary。
- Frontend lint/build：`cd frontend && npm run lint`、`cd frontend && npm run build` 通过。
- E2E：backend main 通过；frontend full Chromium `52 passed / 1 skipped`；backend/frontend queue 阶段已纳入 CI workflow。
- Release gate：`bash scripts/ci_run_release_gate.sh --phase auto --summary-file /tmp/release-gate-check.md --json-summary-file /tmp/release-gate-check.json` 通过；非 PR 环境保守跑 backend/frontend/tooling/hygiene 全量。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check`、备份计划 diff 检查通过。

## 最近封板主线

- `ci-release-engineering`：已 100% 封板；release gate、release readiness matrix、backend/frontend queue workflow、artifact diagnostics、main push `fail-on-missing` 与多 health URL 失败诊断均已收口。
- `source-size-maintenance`：已封板；tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界。
- `provider-tool-expansion`：已 100% 封板；provider search 总量/命中归一化、显式 result_fields 特殊键、provider planner 多协议工具调用容器/别名/JSON 字符串参数解析与 failed reconnect 稳定错误码复原均已收口，旧 SSE/trace/export/display shape 不变。
- `rag-product-experience`：已 100% 封板；知识库治理版本明细、source/document 文档组、文档组删除、Runtime Debug RAG query 召回摘要、质量分布、筛选与 distance 解释均已收口。
- `observability-experience`：已封板；失败线索、来源分类、跨视图 Failure 回放、Task Center 观测筛选、Audit Logs 服务端 keyword、Trace Failure 语义统计与过滤一致性均已收口。
- `production-reliability-hardening`：已封板；任务队列清理、owner/heartbeat、guarded terminal writes、reconnect/断流语义、race 防误复活与 GitHub checks 均已收口。
- `rag-governance-hardening`：已封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口均已完成治理收口。
- `registry-governance`：已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口。

## 后续维护线

- 当前主线：`production-runtime-hardening`，继续按先红测、再实现、再 targeted/full slice 的方式推进。
- 后续候选：`product-ux-polish`，聚焦 Workbench/Task Center 高频操作、trace 回放可读性与治理页面效率。
- 新 provider/source 协议：按 `real-tool-execution` 与 `provider-tool-expansion` 封板基线增量补红测和局部归一化，不扩大外部契约。

## 文档收敛边界

- 主线封板后，四份活跃文档的“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”需要收敛。
- README / backend README / frontend README / 实时计划中的长期参考章节、接口范围、运行约定、关键实现位置、SSE/Trace 与 Memory/RAG 说明不应被整段删除。
- 旧失败过程、按轮流水账、重复验证清单和阶段内细碎过程描述应删除或压缩为高信号摘要。

## 维护约定

- `data/insightagent.plan.back.md` 是只读备份计划，永远不要修改。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 测试、e2e、服务启动、端口和提交权限以 `docs/development-runbook.md` 为准。
