---
name: InsightAgent 开发计划
overview: test-maintainability-hardening 已完成封板；runtime-dependency-modernization 已完成 Node 模块模式与 Python 3.14 FastAPI 兼容两个切片。
current_focus:
  mainline: runtime-dependency-modernization
  status: 40%
  latest_change: 新增后端 runtime dependency contract，精确约束 requirements 与已安装 FastAPI 0.118.3，并验证 Python 3.14 路由注册不再触发 asyncio.iscoroutinefunction DeprecationWarning；Starlette 保持 0.46.2
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/app/services/tool_runtime_execution.py 2864 行；tool_runtime_slice 最大测试主题 http_json_request_validation.py 2403 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - 默认 settings 根据 provider/model/api_key 自动选择 remote 或 canonical mock
  - SSE 事件、TraceStep、result summary、safe output、JSON/Markdown export shape 保持稳定
  - SSE error.diagnostic 与 failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性
  - 任务详情页 trace_semantic URL 参数兼容支持 planner/retrieval/calculator/failure，未知值回退 all；语义切换与 operator next-action 提示仅使用既有 status、failure hint/source 与 semantic failure stats 做本地展示，状态文字/色调与轮询控制优先使用 status_normalized，均不改变任务、trace 或 export payload
  - Workbench Inspector 语义筛选只调整前端本地 trace 筛选状态；保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload
  - Task Center failure source 诊断 chips 与状态筛选只调整前端本地状态；状态、失败摘要和观测筛选统一优先使用 status_normalized，显式 failure_hint/failure_source 优先于 trace 文本推断，不改变任务列表 API 与 trace/export payload
  - Task Center 与任务详情页 operator next-action 提示只由现有 status、failure hint/source 与 semantic failure stats 本地派生；Audit Logs operator next-action 提示只由现有 event_type、event_detail 与 task_id 本地派生；不新增后端字段，不改变任务/审计 API、SSE、trace 或 export payload
  - Knowledge Governance operator next-action、共享范围说明与破坏性操作禁用只由现有 query 状态、chroma_reachable、knowledge_base_id 和用户角色本地派生；Knowledge Governance <-> RAG 往返仅切换、聚焦并展开已有前端弹窗，不新增后端字段，不改变 shared RAG 权限或 API shape
  - Runtime Debug RAG 状态加载失败支持原位刷新，缓存状态在刷新失败时继续可见；失败恢复与跨库反馈隔离仅使用现有 query/mutation 状态和 reset，保留输入草稿，不改变 RAG 请求/响应、权限或审计契约
  - Task Center、Audit Logs 与知识库治理加载错误、陈旧数据保留及原位重试只调整前端 query/presentation 状态，不改变任务、审计或 RAG API shape
  - SSE close 后失败摘要兜底只在流关闭但本地尚未进入 terminal phase 时补拉任务/trace 并映射低敏 failure hint，不改变 SSE、任务、trace 或 export payload
  - 全局 HTTP 响应追加安全 header，仅增加响应头，不改变业务响应体、SSE event、trace/delta 或 export body shape
  - Access token 解析要求 JWT header 为 alg=HS256、typ=JWT；签名、过期和 subject 校验语义保持不变
  - Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常
  - 生产环境禁止使用默认 INSIGHT_AGENT_JWT_SECRET 或其首尾空白包装值签发或验签 access token；开发默认值仍只允许在非生产环境使用
  - 生产环境默认 INSIGHT_AGENT_JWT_SECRET 及其首尾空白包装值也不能作为 refresh token 哈希或 secret 加密派生材料；/health.operations 按同一口径报告 default_jwt_secret
  - 生产环境禁止 INSIGHT_AGENT_CORS_ORIGINS 包含 wildcard *；非生产 CORS 调试行为保持不变
  - 鉴权依赖对 token parser 异常统一返回低敏 401 invalid token，保留 WWW-Authenticate: Bearer，不向客户端回显内部配置或解析细节
  - Auth token 签发与刷新会在创建/轮换 refresh token 和写入 auth session 前先校验 access token 签发配置；生产默认 JWT secret 错误不留下会话存储副作用
  - /health 保持既有字段不变，新增 operations readiness/readiness_level/warnings/warning_summary/risk_domains/readiness_checks、部署配置、SLO 阈值口径、备份恢复演练、runbook/值班响应、应急响应演练新鲜度、队列、执行实例、超时与 Chroma probe 摘要，不暴露数据库连接串、API key、密钥、联系人、runbook URL 原文或完整敏感连接信息
  - /health.operations、release gate、previous summary、artifact guard、trend/export diagnostics 的 operator-facing 摘要只聚合低敏状态、主行动、最高严重级别、失败/告警计数、关注阶段/风险域/scope 与原因枚举，不回显连接串、API key、密钥、联系人、runbook URL、artifact 路径、命令输出、日志正文、环境变量或外部服务响应
  - operator summary contract 只校验 summary JSON/Markdown 中的低敏状态、主行动、严重级别和标量列表字段，不启动服务、不读取外部日志
  - release gate trend 对缺少 operator_summary 的旧 artifact 按既有 result、step summary 与失败标签派生低敏兼容摘要；新格式仍执行严格 operator contract
  - GitHub release-gate workflow 以 /tmp/release-gate-summary.md 作为跨 step 稳定 Markdown，当前 step summary 展示、operator 契约校验与 artifact 上传复用同一内容
  - backend/scripts/tool_runtime_slice 主题文件保持 <= 2500 行；拆分主题由 _partN 承载测试，原主题模块作为稳定组合 facade
  - tool runtime full slice 与有效 -k 筛选沿用原生 unittest 语义；显式 -k 零匹配时输出筛选表达式并保持退出码 5
  - tool runtime --list-tests 可单独或结合 -k 列出实际匹配测试 ID 与总数而不执行；零匹配继续返回退出码 5
  - tool runtime --list-selections 动态校验六个维护选择器，任一零匹配即返回 5；不能与 -k 组合，误用时稳定返回 2
  - release gate 首个失败步骤保留原退出码并输出 FAIL decision/operator summary；空 focus phase 不触发 Bash set -u 二次失败
  - release gate 失败路径 fixture 不依赖 backend/.venv 等可选 workflow 环境，只用 fake-node 在 frontend 首步注入确定性退出码
  - queued/running/cancel/reconnect 与 task recovery 语义保持稳定
  - data/insightagent.plan.back.md 是只读备份计划，永远不修改
validation_baseline:
  release_gate: bash scripts/ci_run_release_gate.sh --phase all --summary-file /tmp/release-gate-runtime-dependency-modernization-slice2-summary.md --json-summary-file /tmp/release-gate-runtime-dependency-modernization-slice2-summary.json passed，覆盖 backend/frontend/tooling/hygiene 全量；JSON summary 复核为 result=PASS、decision_summary.release_decision=approve、operator_summary.status=ready，9 个步骤全过、0 失败
  backend: runtime dependency contract 2/2；full slice 2020/2020；module boundary 9/9；FastAPI 0.118.3 / Starlette 0.46.2 通过 pip check，Python 3.14 路由注册无 asyncio.iscoroutinefunction DeprecationWarning；security 17/17；production operations health 11/11
  frontend: runtime dependency contract 3/3；手动扩展 node tests 153/153；release gate 内置 frontend node 清单 153/153 且无 MODULE_TYPELESS_PACKAGE_JSON 告警；runtime debug targeted 12/12；RAG 状态刷新、失败恢复与跨库反馈隔离已纳入主路径且 8 个 Chromium 用例可正常收集；npm run lint passed；npm run build passed；本轮 rendered QA 未启动本机服务
  e2e: backend main/timeout/queue 与 frontend smoke/full/queue 最近验证通过；frontend full Chromium 56 passed / 1 skipped；targeted Chromium remote network/401/cancel、trace delta retry、Audit Logs/Task Center/知识库治理错误恢复 passed；tooling failure fixture 已移除可选 venv 依赖，并通过无 venv 干净副本和 backend/frontend scope 回归
  hygiene: py_compile、git diff --check、git diff --cached --check、backup plan diff clean
completed_mainlines:
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - production-runtime-hardening：SSE/failure audit diagnostic、前端审计详情 reason、reconnect provider 错误消息映射，后续运维体验已补 /health.operations 与 release/artifact/trend operator-facing 摘要及契约门禁
  - source-size-maintenance：tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界
  - ci-release-engineering：静态 release gate、PR auto routing、summary artifact、readiness matrix、service-backed e2e workflow queue、artifact strict policy
  - product-ux-polish：语义 Trace、normalized 状态/失败诊断、治理与观测列表错误恢复、operator next-action、跨视图知识库往返，以及 Runtime Debug RAG 状态/写入/检索恢复与跨库反馈隔离
  - production-operations-readiness：/health.operations 非敏感运维 readiness、部署/SLO/备份恢复/runbook/演练摘要、warning_summary、risk_domains、readiness_checks 与 readiness_level
  - security-hardening：安全 header、JWT header/默认密钥/CORS 硬阻断、refresh token 输入收敛、认证错误低敏化、auth session 副作用保护与 secret material 默认凭据阻断
  - release-observability-polish：release readiness matrix、artifact retention、release gate summary/trend summary、previous artifact 下载诊断与 release/rollback decision_summary
  - test-maintainability-hardening：四个大测试主题稳定 facade + 双分片、2500 行主题门禁、零匹配诊断、测试预览与六个维护选择器
next_candidate_mainlines:
  - runtime-dependency-modernization：当前 40%，已完成 Node 模块模式与 Python 3.14 FastAPI 兼容两个切片；后续核对 Next 工具链约束
next_steps:
  - 为 Next 15.2.4、eslint-config-next 与 Node 24 建立可由红测证明的工具链兼容约束，再评估局部升级或配置调整
logging_rule: 本文件的状态块保持收敛；正文中的稳定能力摘要、验证口径、维护规则和主线地图不应被整段删除。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`（含后续运维体验）、`product-ux-polish`（含下一阶段）、`production-operations-readiness`、`security-hardening`、`release-observability-polish` 与 `test-maintainability-hardening` 均已 100% 封板。
- 最近封板：`test-maintainability-hardening` 已 100% 封板；四个大测试主题完成稳定 facade + 双分片治理，2500 行主题门禁、零匹配诊断、测试预览与六个维护选择器均已纳入稳定测试入口。
- 当前主线：`runtime-dependency-modernization` 40%；Node 模块模式与 Python 3.14 FastAPI 兼容两个切片已完成，FastAPI 精确 pin 到 `0.118.3` 后目标弃用告警消失。
- 当前本机运行/提交路径以 `docs/development-runbook.md` 为准；代码规模治理保持 `backend/app`、`backend/scripts` 与 `frontend` 源码单文件 <= 3000 行。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、OpenAI Chat/Responses、Gemini/Vertex functionCall、Bedrock/Claude Converse toolUse、Anthropic Messages mixed text/tool_use content、顶层 message/delta wrapper、tool_call 单数容器、tool_calls/toolCalls 映射容器、camelCase toolCalls/toolInvocations/toolName/functionName、嵌套 tool 对象、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出与 planner 协议：覆盖常见 REST/JS 字段别名、GraphQL connection pageInfo.totalCount + edges、Elastic/OpenSearch hits、Azure/OData、Meilisearch/Algolia estimatedTotalHits / nbHits、Brave web.results、Bing webPages.totalEstimatedMatches、SearXNG/元搜索 number_of_results、Crossref/学术检索 total-results/message.items、PubMed/NCBI ESearch count/idlist、Europe PMC hitCount/resultList.result、Google Custom Search queries.request[].totalResults/items、Serper/Google Search searchInformation.totalResults/organic、引用型 citations/search_results、organic search、分页型 data/records + meta.page/pagination/paging total、安全千分位总量字符串、显式 result_fields bracket quoted 特殊字段键、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。
- release 工程：静态 release gate、PR auto routing、结构化 Markdown/JSON summary、previous summary 下载诊断、baseline/delta 友好的 release gate trend summary、release/rollback decision_summary、release readiness matrix、backend/frontend queue workflow、artifact diagnostics 与 main 分支严格策略已落地。

## 当前验证基线

- Release gate all：`runtime-dependency-modernization` 第二切片核对 PASS，覆盖 backend/frontend/tooling/hygiene；JSON summary 为 `result=PASS`、`release_decision=approve`、`operator_status=ready`，9/9。
- Backend：runtime dependency contract `2/2`；full slice `2020/2020`；module boundary `9/9`；FastAPI `0.118.3` / Starlette `0.46.2` 通过 `pip check`，Python 3.14 路由注册无目标弃用告警；security `17/17`；production operations health `11/11`。
- Frontend：runtime dependency contract `3/3`；release gate 内置 node 清单与扩展 node tests 均为 `153/153`，且 Node 24 `MODULE_TYPELESS_PACKAGE_JSON` 告警已消除；runtime debug targeted `12/12`；RAG 状态刷新、失败恢复与跨库反馈隔离已纳入主路径且 8 个 Chromium 用例可正常收集；`npm run lint` 与 `npm run build` 通过；本轮 rendered QA 未启动本机服务。
- E2E/CI：backend main/timeout/queue 与 frontend smoke/full/queue 最近验证通过；tooling failure fixture 已移除可选 venv 依赖，并通过无 venv 干净副本与两个 scope 回归。
- Hygiene：`py_compile`、`git diff --check`、`git diff --cached --check` 与备份计划 diff 检查通过；`data/insightagent.plan.back.md` 无修改。

## 当前主线

- 当前主线：`runtime-dependency-modernization` 40%；已完成 Node 模块模式告警治理与 Python 3.14 FastAPI 兼容约束，后端 runtime dependency contract 已纳入 full slice。
- 下一切片：为 Next 15.2.4、eslint-config-next 与 Node 24 建立工具链兼容约束，再评估局部升级或配置调整。
- 后续实现继续保持外部 SSE/trace/export/display/e2e 契约稳定。
- 新 provider/source 协议仍按 `real-tool-execution` 与 `provider-tool-expansion` 封板基线增量补红测和局部归一化，不扩大外部契约。

## 文档收敛边界

- 主线封板后，四份活跃文档的“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”需要收敛。
- README / backend README / frontend README / 实时计划中的长期参考章节、接口范围、运行约定、关键实现位置、SSE/Trace 与 Memory/RAG 说明不应被整段删除。
- 旧失败过程、按轮流水账、重复验证清单和阶段内细碎过程描述应删除或压缩为高信号摘要。

## 维护约定

- `data/insightagent.plan.back.md` 是只读备份计划，永远不要修改。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 测试、e2e、服务启动、端口和提交权限以 `docs/development-runbook.md` 为准。
