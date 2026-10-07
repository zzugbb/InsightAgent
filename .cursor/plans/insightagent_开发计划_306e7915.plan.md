---
name: InsightAgent 开发计划
overview: next-major-upgrade-readiness 已 100% 封板；project-completion-audit 1/3（约 33%）完成，历史 GLM 成功链路已核实、历史实时请求 HTTP 429；用户确认当前无真实 key/部署环境，限定步骤恢复已完成本地验证；项目总完成度未量化。
current_focus:
  mainline: project-completion-audit
  status: 静态盘点 1/3 完成；限定步骤恢复已落地、写入并行延期；用户确认无真实 key/部署环境，当前成功调用及目标运行/签收待实证
  latest_change: 2026-10-07 限定内建顺序计划的实验性步骤恢复落地；6 个静态专项、9 个 PostgreSQL 与完整 Chromium 77 passed/1 skipped；取消竞态、串行失败 Trace 与前端 failed 轮询截断 SSE 已修复，写入并行及 HTTP/DAG checkpoint 延期
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/app/services/tool_runtime_execution.py 2864 行；tool_runtime_slice 最大测试主题 http_json_request_validation.py 2403 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - failed 状态轮询不提前截断活动 SSE，提供方具体诊断由 SSE/关闭兜底处理；取消/超时仍终止本地连接
  - HTTP 并发需 execution.parallel_read_only=true 且固定 GET/无请求体；资格绑定工厂 runner，配置与上下文冻结，未声明工具保持串行。GET 只读性由配置者确认，见[HTTP 读取契约](../../docs/http-read-parallel.md)。
  - 显式工具图最多 32 节点/128 边，绑定仅限已投影预览标量到 query/expression；图错误拒绝整图，失败/取消/超时阻止依赖调用。Trace.meta 的 plan_node_id/depends_on 为可选扩展，详见[依赖契约](../../docs/tool-dependencies.md)。
  - 任务内并发默认关闭（`TASK_TOOL_MAX_CONCURRENT=1`）；仅就绪的内建检索/计算及明确配置只读的 HTTP GET 可并发，进程最多 8 个读取线程，Trace/终态写入由协调线程串行处理；并发事件允许交错，Trace.meta 增加兼容可选分组信息，详见[并发契约](../../docs/task-tool-parallel.md)。
  - 完整分支重跑从本人已终结任务复制/编辑 prompt，不复制历史结果；实验性 checkpoint 保留输入/计划并复用内建顺序计划的成功前缀。两者均创建独立会话、幂等保存 queued 任务并由既有 stream 执行，原任务和 SSE/Trace/export shape 不变；复用步骤标注来源并清零本任务 token/cost，详见[步骤恢复](../../docs/task-checkpoints.md)
  - 后台导入新增可空 progress 确认计数，失败/中断保留已确认批次；默认每批 128 切块并遵守 Chroma 上限，每任务最多 5000 切块（超限 422，调用方分拆或降低 overlap）；进度不延长整任务超时，同步 ingest 与 SSE/Trace/export 保持原契约
  - 后台 RAG 导入为兼容扩展；同用户/同键/同参数返回原任务，只允许提交者查询/取消，共享写入限管理员；只取消排队任务，中断不自动重放，终结后清理原始载荷，同步 ingest 保持兼容
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
  - HTTP 响应追加服务端生成的 X-Request-ID，低敏 JSON 请求日志仅含 request ID、方法、路由模板、状态码与完整响应耗时；原始 URL/query/header/body 与异常正文不进入日志，SSE 业务失败仍需结合事件/Trace
  - 运行时 OpenAPI 操作/组件指纹与 backend/api_surface_baseline.json 对齐；漂移必须按 docs/api-changelog.md 人工审查兼容性并更新记录，指纹不证明 SSE/Trace/export 运行时语义兼容
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
  - Next 16.3.5 与 eslint-config-next 精确对齐，React / React DOM 固定 19.2.8；React Compiler refs / set-state-in-effect 无例外；ESLint 9.39.5 在 React/import/jsx-a11y 插件正式兼容 ESLint 10 前保持锁定
  - data/insightagent.plan.back.md 是只读备份计划，永远不修改
validation_baseline:
  source: 2026-10-07 full release gate 10/10、步骤恢复 PostgreSQL 9/9、内建并发回归 6/6、完整 Chromium 77 passed/1 skipped；无真实 key/部署环境，外部验收未验证
  current_audit: 历史 glm-5.1 provider-usage 完成任务 10 条，含工具/RAG Trace；一条历史任务 JSON/Markdown 导出构建通过；此前最小 GLM 调用 HTTP 429，未重试；本轮无真实 key，不发起请求
  backup_restore_fixture: scripts/local_stack_snapshot.py 安全测试通过；修正 Compose Chroma /data 挂载后，隔离 fixture 的 PostgreSQL 测试行与 Chroma 测试文档均从新项目卷恢复读回；目标环境 RPO/RTO 未验证
  tooling_current: bash scripts/ci_run_release_gate.sh --phase tooling passed，包含快照工具与 A2 六镜像摘要预检测试；后端/前端 Docker build --check 无告警
  pilot_images_current: 本机 ARM64 后端/前端 Docker 构建通过，基础镜像均以 sha256 摘要固定；后端锁定 84 个直接/传递依赖版本并核对镜像内安装结果；隔离联调验证生产模式后端、PostgreSQL 注册/会话写读、Chroma 探测、前端 HTML/CSS 与浏览器实际 API 地址，临时资源已清理；未推送目标仓库
  async_rag_ingest: 持久化、幂等、取消与中断恢复落地；新增分批写入、确认进度与 5000 切块预算；沿用前轮 21/21 PostgreSQL/Chroma 隔离集成基线，包含实际 40 文档/400 切块，原始载荷终结后清理
  http_read_parallel: 固定 GET/无请求体且 parallel_read_only=true；15 个静态专项、7 个本机 HTTP/PostgreSQL 场景通过；真实端点只读性/限流/延迟待实证
  tool_dependencies: 显式 DAG 最多 32 节点/128 边，仅公开预览标量绑定 query/expression；25 个静态专项与 7 个 PostgreSQL 场景通过；HTTP/DAG checkpoint 与写入并行延期，目标图生成质量待验证
  task_tool_parallel: 默认 1（串行），1–4 配置仅并发内建与明确声明的 HTTP 读取；15 个专项与 6 个 PostgreSQL 场景通过，进程最多 8 个读取线程；取消/超时丢弃迟到结果
  task_checkpoints: 实验性内建顺序计划，成功前缀复用、独立分支与失败重试；6 个静态专项、9/9 PostgreSQL，HTTP/DAG checkpoint 延期；新 Trace 标注来源且复用 token/cost 归零
  task_reruns: 完整任务分支支持编辑输入、独立会话、幂等与来源分页；7 个既有专项进入门禁，11/11 PostgreSQL 本轮回归通过；原任务/Trace/usage 不变
  backend_current: full slice 2129/2129、module boundary 9/9；6 个步骤恢复专项进入门禁，OpenAPI 51 操作/88 组件；步骤恢复 PostgreSQL 9/9、内建并发回归 6/6
  release_gate: /tmp/insightagent-checkpoint-release.md 与 .json，full gate 10/10 PASS；Turbopack/webpack 双构建通过
  frontend: node tests 184/184、lint 0 error / 2 个既有 warning、Turbopack/webpack 双构建 passed；ESLint 10 外部兼容约束仍保留
  e2e_current: 隔离 PostgreSQL/Chroma mock 栈、TASK_TOOL_MAX_CONCURRENT=2，完整 Chromium 77 passed/1 skipped；桌面/手机恢复与同键重试通过，临时资源清理
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
  - runtime-dependency-modernization：Node 24 ESM、Python 3.14 FastAPI、Next 15.5.25、ESLint CLI flat config、审计安全补丁锁定与最终 service-backed e2e
  - next-major-upgrade-readiness：Next 16.3.5 / React 19.2.8、原生 flat ESLint、React Compiler 规则无例外、Turbopack/webpack 双构建与 full Chromium 验证；ESLint 10 作为上游兼容动作显式保留
next_candidate_mainlines:
  - 试点收尾实施主线：由 project-completion-audit 的真实环境证据与范围/签收结论确定具体切片，不预先宣称剩余工作已知
  - eslint-10-adoption：非试点阻塞；等待 eslint-plugin-react 官方兼容版本，并确认 import/jsx-a11y peer 范围支持 ESLint 10；不使用 force/peer override
next_steps:
  - GLM 到期期间暂停真实请求；按用户授权将限定步骤恢复纳入，写入并行及 HTTP/DAG checkpoint 延期；续用或换有效兼容账号后补当前成功链路；试点环境确定后按 docs/pilot-deployment-preflight.md 预检并完成部署/恢复/回滚实证，项目总完成度暂不估百分比
  - ESLint 10 保留为非阻塞维护候选，三个插件正式兼容后再补依赖契约红测并运行完整门禁
logging_rule: 本文件的状态块保持收敛；正文中的稳定能力摘要、验证口径、维护规则和主线地图不应被整段删除。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`（含后续运维体验）、`product-ux-polish`（含下一阶段）、`production-operations-readiness`、`security-hardening`、`release-observability-polish`、`test-maintainability-hardening`、`runtime-dependency-modernization` 与 `next-major-upgrade-readiness` 均已 100% 封板。
- 最近封板：`next-major-upgrade-readiness` 已 100% 封板；Next 16 / React 19.2、原生 flat ESLint、React Compiler 规则无例外、双构建与 full Chromium 已验证，未修改外部运行时契约。
- 当前主线：`project-completion-audit` 1/3（约 33%）完成；[审计清单](../../docs/project-completion-audit.md)已核实历史 GLM 成功任务、工具/RAG Trace 与导出，前期审计调用 HTTP 429 且用户确认服务到期；限定步骤恢复纳入、写入工具并行延期，试点部署/恢复与用户签收仍缺证据。
- A2 试点镜像配方与六镜像摘要预检已准备：84 个后端依赖版本锁定，非 root 用户和构建期默认 embedding 缓存已验证；当前 ARM64 前后端生产镜像通过任务、导出、步骤恢复及取消联调。目标部署、TLS 与回滚仍缺实证。
- A4 [后台 RAG 导入](../../docs/rag-background-ingest.md)的持久化/分批进度与[完整任务分支重跑](../../docs/task-reruns.md)已完成本地闭环；[任务内工具并发](../../docs/task-tool-parallel.md)支持内建检索/计算有界并发；[工具依赖与结果引用](../../docs/tool-dependencies.md)支持显式 DAG、重复工具、拓扑波次与公开预览标量绑定；[HTTP 读取并发](../../docs/http-read-parallel.md)支持明确声明只读的固定 GET、配置冻结和生命周期协调。[实验性步骤恢复](../../docs/task-checkpoints.md)已实现内建顺序计划的独立分支、成功前缀复用与当前设置复核。OpenAPI 为 51 操作 / 88 组件；写入工具并行及 HTTP/DAG checkpoint 明确延期，目标运行与用户验收待完成。
- 非阻塞维护候选：`eslint-10-adoption` 的 React/import/jsx-a11y 三个插件 peer 范围均排除 ESLint 10；React 官方修复尚未发布，预检的 1 个外部兼容动作概括这组约束，不强制覆盖 peer。
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

- 功能验证基线（上一轮）：2026-10-07 full release gate `10/10`（backend/frontend/tooling/hygiene），步骤恢复 PostgreSQL `9/9`、完整重跑回归 `11/11`、内建并发回归 `6/6`，隔离 mock 栈完整 Chromium `77 passed / 1 skipped`。queue 专用 skip 保留独立验证路径。
- 后端 full slice `2129/2129`、module boundary `9/9`，步骤恢复含 6 个静态专项；OpenAPI `51` 操作 / `88` 组件与提交基线一致。
- 前端 node `184/184`，lint `0 error / 2` 个既有 warning，Turbopack/webpack 双构建通过；桌面与 390×844 手机验证恢复、结果复用、来源往返与未知送达同键重试，手机详情横向溢出与 failed 轮询提前截断 SSE 诊断已修复，无相关控制台错误/框架覆盖层。
- 既有 HTTP/依赖 PostgreSQL `7/7`、`7/7`，RAG PostgreSQL/Chroma `21/21` 与 400 切块实写沿用此前明确基线；不计作本轮新增验证或目标环境吞吐。
- 外部证据：已核对历史 10 条 GLM 成功任务与一条导出；用户再次确认当前无真实 key、无部署环境，本轮没有真实模型请求。试点部署/TLS/升级回滚、恢复 RPO/RTO 与用户签收仍未验证。
- 本轮镜像验证：ARM64 前后端生产构建、禁网 embedding、后台导入/检索、2 个完成任务、Trace/delta/JSON v1.0/Markdown、复用 2 个工具步骤与 1 个排队取消通过；旧镜像被新增检查拒绝。tooling 门禁与 hygiene 3/3 通过（含 5 个 smoke 自测与 6 种失败注入）。详情与镜像来源见[试点镜像记录](../../docs/pilot-deployment-preflight.md)；临时容器/网络已清理，未推送或部署到目标环境，备份计划无修改。

## 当前主线

- 当前主线：`project-completion-audit` 1/3 完成；无真实 key/部署环境期间保留未验证状态；限定步骤恢复本地完成、写入工具并行延期，续用或换有效兼容账号后补当前成功链路；目标部署/恢复待环境具备，再做用户签收。项目总完成百分比暂不估算。
- 非阻塞维护候选：`eslint-10-adoption` 等待 [eslint-plugin-react 官方兼容性议题](https://github.com/jsx-eslint/eslint-plugin-react/issues/3977) 与 [修复 PR](https://github.com/jsx-eslint/eslint-plugin-react/pull/4022) 对应的正式发布，并核对 import/jsx-a11y 兼容版本；届时补依赖红测后再受控升级。
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
