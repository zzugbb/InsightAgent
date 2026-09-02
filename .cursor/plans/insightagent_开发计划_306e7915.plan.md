---
name: InsightAgent 开发计划
overview: provider-tool-expansion、ci-release-engineering、production-runtime-hardening、product-ux-polish 与 production-operations-readiness 已 100% 封板。
current_focus:
  mainline: security-hardening
  status: 约 40%
  latest_change: 生产环境阻断默认 JWT secret 的 access token 签发与验签，默认开发密钥只允许非生产使用
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/scripts/tool_runtime_slice/planning_provider.py 2923 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - 默认 settings 根据 provider/model/api_key 自动选择 remote 或 canonical mock
  - SSE 事件、TraceStep、result summary、safe output、JSON/Markdown export shape 保持稳定
  - SSE error.diagnostic 与 failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性
  - 任务详情页 trace_semantic URL 参数兼容支持 planner/retrieval/calculator/failure，未知值回退 all；语义切换仅同步 URL 并清理本地筛选，状态文字/色调与轮询控制优先使用 status_normalized，均不改变任务、trace 或 export payload
  - Workbench Inspector 语义筛选只调整前端本地 trace 筛选状态；保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload
  - Task Center failure source 诊断 chips 与状态筛选只调整前端本地状态；状态、失败摘要和观测筛选统一优先使用 status_normalized，显式 failure_hint/failure_source 优先于 trace 文本推断，不改变任务列表 API 与 trace/export payload
  - Task Center、Audit Logs 与知识库治理加载错误、陈旧数据保留及原位重试只调整前端 query/presentation 状态，不改变任务、审计或 RAG API shape
  - SSE close 后失败摘要兜底只在流关闭但本地尚未进入 terminal phase 时补拉任务/trace 并映射低敏 failure hint，不改变 SSE、任务、trace 或 export payload
  - 全局 HTTP 响应追加安全 header，仅增加响应头，不改变业务响应体、SSE event、trace/delta 或 export body shape
  - Access token 解析要求 JWT header 为 alg=HS256、typ=JWT；签名、过期和 subject 校验语义保持不变
  - Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常
  - 生产环境禁止使用默认 INSIGHT_AGENT_JWT_SECRET 签发或验签 access token；开发默认值仍只允许在非生产环境使用
  - /health 保持既有字段不变，新增 operations readiness/readiness_level/warnings/warning_summary/risk_domains/readiness_checks、部署配置、SLO 阈值口径、备份恢复演练、runbook/值班响应、应急响应演练新鲜度、队列、执行实例、超时与 Chroma probe 摘要，不暴露数据库连接串、API key、密钥、联系人、runbook URL 原文或完整敏感连接信息
  - queued/running/cancel/reconnect 与 task recovery 语义保持稳定
  - data/insightagent.plan.back.md 是只读备份计划，永远不修改
validation_baseline:
  release_gate: bash scripts/ci_run_release_gate.sh --phase all --summary-file /tmp/release-gate-all-summary.md --json-summary-file /tmp/release-gate-all-summary.json passed，覆盖 backend/frontend/tooling/hygiene 全量；无 backend/.venv fixture 下 release readiness / release gate JSON 校验 passed
  backend: full slice 2009/2009；module boundary 4/4；security 9/9；default_secret 2/2；security_refresh 2/2；auth 1/1；production_operations 12/12；production_operations_health 10/10；production_reliability 39/39；reconnect 9/9
  frontend: workbench utils targeted 78/78；store utils targeted 16/16；task detail targeted 10/10；audit targeted 10/10；knowledge governance targeted 6/6；手动扩展 node tests 141/141；release gate 内置 frontend node 清单 140/140；npm run lint passed；npm run build passed
  e2e: backend main/timeout/queue passed；backend tooling scope local passed；frontend queue Chromium local 1/1 passed；backend finalize + artifact-stage guard main push fail-on-missing passed，included_count=20、missing_count=0；frontend full Chromium 56 passed / 1 skipped；targeted Chromium remote network/401/cancel、trace delta retry、Audit Logs/Task Center/知识库治理错误恢复 passed；commit 6ea51c7 的 GitHub backend-e2e run 33373178443、frontend-e2e run 33373178435、release-gate run 33373178464 均 completed success
  hygiene: py_compile、git diff --check、git diff --cached --check、backup plan diff clean
completed_mainlines:
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - production-runtime-hardening：SSE/failure audit diagnostic、前端审计详情 reason、reconnect provider 错误消息映射
  - source-size-maintenance：tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界
  - ci-release-engineering：静态 release gate、PR auto routing、summary artifact、readiness matrix、service-backed e2e workflow queue、artifact strict policy
  - product-ux-polish：语义 Trace、normalized 状态/失败诊断、治理与观测列表错误恢复及伪空态治理
  - production-operations-readiness：/health.operations 非敏感运维 readiness、部署/SLO/备份恢复/runbook/演练摘要、warning_summary、risk_domains、readiness_checks 与 readiness_level
next_candidate_mainlines:
  - release-observability-polish：发布/回滚可见性、artifact 保留策略与门禁趋势摘要
next_steps:
  - security-hardening 优先从鉴权会话、密钥/安全头、限流与依赖安全审计中选择可红测证明的小切片
logging_rule: 本文件的状态块保持收敛；正文中的稳定能力摘要、验证口径、维护规则和主线地图不应被整段删除。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`、`product-ux-polish` 与 `production-operations-readiness` 均已 100% 封板。
- `security-hardening` 已进入，当前约 40%；后端已补全局安全响应头，收紧 access/refresh token 输入边界，并在生产环境阻断默认 JWT secret 的签发与验签；业务 payload 与 SSE/trace/export 契约不变。
- `production-operations-readiness` 封板摘要：`/health.operations` 已完成非敏感运维 readiness 摘要、部署配置校验、SLO 阈值口径、备份恢复演练、runbook/值班响应摘要、应急响应演练新鲜度、告警等级汇总、按域风险汇总、readiness_checks 固定清单与 readiness_level。
- 生产运行态封板摘要：SSE `error.diagnostic` 与 failure audit detail 默认对齐低敏 `reason` 枚举，前端审计详情可展示该低敏原因；reconnect 保留 provider 错误 code 并补齐安全消息映射。旧 `code/fatal/retryable/detail/status_code` 与 audit `status_code/retryable` 字段不变。
- 产品体验封板摘要：语义 Trace、Task Center/任务详情 normalized 状态与失败诊断、Task Center/Audit Logs/知识库治理加载恢复、伪空态治理、任务详情 failure hint code 映射与 SSE close 后失败摘要兜底已收口。
- 后端/frontend e2e 后置门禁摘要：release-gate JSON summary 已移除 Python 子进程转义依赖，backend artifact 清单覆盖 main/timeout/queue 产物且不再列 finalize 后才生成的 failure diagnostics，本地 boot wrapper 优先走 `backend/.venv/bin/python -m uvicorn`；无 venv runner JSON 校验 fallback、frontend queue runtime API base URL、queue 慢加载稳定性与 export diagnostics 范围均已修复，commit `6ea51c7` 对应 GitHub 三条 workflow 均 success。
- 运维就绪摘要：`/health` 新增 `operations` 字段，返回 readiness、readiness_level、非敏感 warnings、warning_summary 告警等级计数、risk_domains 按域风险计数、readiness_checks 固定清单、deployment 配置摘要、SLO 阈值口径摘要、backup_restore 摘要、runbook 摘要、应急响应演练新鲜度、任务队列并发、执行实例 stale recovery、任务超时与 Chroma probe 状态；既有健康字段保持兼容。
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

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `2009/2009`。
- Backend targeted：`security 9/9`、`default_secret 2/2`、`security_refresh 2/2`、`auth 1/1`、`production_operations 12/12`、`production_operations_health 10/10`、`production_reliability 39/39`、`reconnect 9/9`、registry/http_json/provider/runtime/trace/export/usage 通过。
- Module boundary：`cd backend && PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py`，当前 `4/4`，包含 3000 行规模边界。
- Frontend node tests：workbench utils targeted `78/78`、store utils targeted `16/16`、task detail targeted `10/10`、audit targeted `10/10`、knowledge governance targeted `6/6`；手动扩展当前 `141/141`，release gate 内置 frontend node 清单 `140/140`，包含 frontend source size boundary。
- Frontend lint/build：`cd frontend && npm run lint`、`cd frontend && npm run build` 通过。
- E2E：backend main、timeout、queue 三段通过；backend tooling scope 本地复验通过；frontend queue Chromium 专项本地复绿；backend finalize + artifact-stage guard 在 main push `fail-on-missing` 下通过，`included_count=20`、`missing_count=0`；frontend full Chromium `56 passed / 1 skipped`；targeted Chromium remote network/401/cancel、trace delta retry、Audit Logs/Task Center/知识库治理错误恢复通过；commit `6ea51c7` 的 GitHub `backend-e2e` run `33373178443`、`frontend-e2e` run `33373178435`、`release-gate` run `33373178464` 均 completed success。
- Release gate：`bash scripts/ci_run_release_gate.sh --phase all --summary-file /tmp/release-gate-all-summary.md --json-summary-file /tmp/release-gate-all-summary.json` 通过，覆盖 backend/frontend/tooling/hygiene 全量。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check`、备份计划 diff 检查通过。

## 最近封板主线

- `product-ux-polish`：已 100% 封板；语义 Trace、normalized 状态/失败诊断、治理与观测列表错误恢复及伪空态治理已收口，外部契约不变。
- `production-runtime-hardening`：已 100% 封板；SSE/failure audit diagnostic 统一、provider call/selection failure 低敏 reason、前端审计详情 reason 展示与 reconnect provider 错误消息映射已收口，旧 SSE/trace/export/e2e 契约保持稳定。
- `ci-release-engineering`：已 100% 封板；release gate、release readiness matrix、backend/frontend queue workflow、artifact diagnostics、main push `fail-on-missing` 与多 health URL 失败诊断均已收口。
- `source-size-maintenance`：已封板；tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界。
- `provider-tool-expansion`：已 100% 封板；provider search 总量/命中归一化、显式 result_fields 特殊键、provider planner 多协议工具调用容器/别名/JSON 字符串参数解析与 failed reconnect 稳定错误码复原均已收口，旧 SSE/trace/export/display shape 不变。
- `rag-product-experience`：已 100% 封板；知识库治理版本明细、source/document 文档组、文档组删除、Runtime Debug RAG query 召回摘要、质量分布、筛选与 distance 解释均已收口。
- `observability-experience`：已封板；失败线索、来源分类、跨视图 Failure 回放、Task Center 观测筛选、Audit Logs 服务端 keyword、Trace Failure 语义统计与过滤一致性均已收口。
- `production-reliability-hardening`：已封板；任务队列清理、owner/heartbeat、guarded terminal writes、reconnect/断流语义、race 防误复活与 GitHub checks 均已收口。
- `rag-governance-hardening`：已封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口均已完成治理收口。
- `registry-governance`：已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口。

## 后续维护线

- 当前状态：`security-hardening` 已进入，当前约 40%；后端全局安全响应头、token 输入边界收紧与生产默认 JWT secret 硬阻断已按先红测再实现完成，后续继续从鉴权会话、限流与依赖安全审计中补红测。
- 后续候选：`release-observability-polish`。
- 新 provider/source 协议：按 `real-tool-execution` 与 `provider-tool-expansion` 封板基线增量补红测和局部归一化，不扩大外部契约。

## 文档收敛边界

- 主线封板后，四份活跃文档的“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”需要收敛。
- README / backend README / frontend README / 实时计划中的长期参考章节、接口范围、运行约定、关键实现位置、SSE/Trace 与 Memory/RAG 说明不应被整段删除。
- 旧失败过程、按轮流水账、重复验证清单和阶段内细碎过程描述应删除或压缩为高信号摘要。

## 维护约定

- `data/insightagent.plan.back.md` 是只读备份计划，永远不要修改。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 测试、e2e、服务启动、端口和提交权限以 `docs/development-runbook.md` 为准。
