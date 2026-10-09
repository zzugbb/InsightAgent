---
name: InsightAgent 开发计划
overview: project-completion-audit 本地开发与工程收尾已封板；用户将部署、用户签收与真实业务验收移出本次范围，条件具备后单独验收；已知规划回退风险保留。
current_focus:
  mainline: project-completion-audit
  status: 本地开发与工程收尾已封板；外部部署/用户签收/业务验收延期，外部试点就绪未验收
  latest_change: 2026-10-09 最终本地复核通过；后端2/2、前端4/4含双构建、tooling1/1、hygiene4/4；隔离RAG1/1与规划恢复5/5，文档链接及服务健康正常；仅更新验证记录
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/app/services/tool_runtime_execution.py 2864 行；tool_runtime_slice 最大测试主题 http_json_request_validation.py 2403 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2548、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - 规划响应校验失败或调用以空正文报错时，保存其实际用量并与先前规划相加；首轮规则回退仍可用，后续调用错误终结任务；部分字段及成本合计保持未知，上游 total 单列保留。无有效用量不估算，非法图仍返回原错误并终结任务。

  - 会话消息 completion 为可选兼容扩展（seq、两个白名单结束原因）；只匹配同用户/会话的 assistant 所属任务，任务分页或筛选不影响历史提示；原始正文与 SSE/Trace/export 兼容
  - 正常任务成功状态、Trace/usage、assistant 消息与会话更新时间在同一事务提交；回答保存失败则回滚并终结为失败，终态/执行实例竞争落败不插入回答。Memory 与 done 在提交后执行；消息正文及任务终态/SSE/export 字段形状不变。详见[成功保存契约](../../docs/task-completion.md)。
  - 任务/会话汇总、趋势、榜单、会话导出与前端会话统计优先读取有效 overall 用量，字段缺失时按 final + planning 回退，避免重复计数；来源筛选包含规划阶段，任务原始明细与 API 形状不变。详见[用量口径](../../docs/usage-accounting.md)。
  - 远端模型流必须收到 [DONE] 或已知首 choice finish_reason 才算正常结束；无信号 EOF 返回既有 remote_provider_stream_interrupted，保留全部已生成 Trace/递增 seq，不写成功 assistant 或 Memory，不自动重放；空帧不递归，正常结束无文本仍报 remote_provider_empty_response。详见[流结束契约](../../docs/provider-stream-completion.md)。
  - 跨轮重复检查使用工具名与实际输入；依赖绑定节点在解析后、工具启动前复核，同轮重复节点与工具内部重试保持原行为。反馈决策默认最多 3 轮（AGENT_MAX_ROUNDS=1 保持单轮），安全 Observation 驱动后续行动；后续 query/expression 必须提供非空文本或合法结果绑定，不从提示补缺失参数；多轮任务不生成单轮 checkpoint。Trace 记录轮次/决策来源并汇总所有规划用量；流程图虚线为记录顺序、实线为依赖/决策来源，详情不截断。
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
  - 聊天输入在 composition 生命周期、原生 isComposing 或兼容 keyCode=229 时将 Enter 留给输入法；正常 Enter 发送、Shift+Enter 换行与发送禁用规则保持一致，不改变后端请求或 SSE/Trace 契约。
  - HTTP 工具成功后的模型证据仅取 Trace 中公开的 effective_result_output_keys，复用脱敏，不读取原始响应、输入或注册表配置；最多 6 项/单项 JSON 3000/总 JSON 8000 字符，裁剪保持有效 JSON 并标记 truncated；供反馈与最终回答使用，计数 Observation 与 SSE/Trace/export 不变。
  - 模型会话快照仅含本任务创建前完成的同用户/会话问答，最多 6 轮/单消息 4000/历史 JSON 16000；RAG 证据最多 6 片段/单片段 1200/JSON 8000，规则回退与工具执行保留本次原始输入
  - 知识文件导入复用 ingest-jobs，UTF-8 TXT/Markdown 1–20 文件、256 KB/64,000 字符单文件、512 KB 总文件；文件名为 source/document_id，结果不确定时冻结并复用原载荷/幂等键；版本复核与检索均定位目标库，shared 写入权限不变
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
  business_rag_acceptance: scripts/business_rag_acceptance_runner.py；本轮修正判定，静态17/17、隔离PostgreSQL/Chroma自测1/1；待外部验收（缺真实业务资料）
  ci_e2e_robustness: frontend/backend tooling if always；ci_rerun_frontend_e2e_diagnostics；test_ci_rerun + workflow_guards + release-gate tooling PASS（VM）
  planning_wait_recovery: 本轮隔离替身5/5（含取消后迟到规划不写Trace/用量）；Chrome真实规划等待可见，回退后编辑分支恢复1/1；完整前端保留此前217/217
  provider_latency_audit: 只读既有真实 RAG 日志，两次约 60 秒异常；离线耗时专项 11/11
  source: 2026-10-09 当前后端 gate 2/2、full slice 2220/2220、模块 9/9，既有 planning-call-usage full gate 10/10、提供方静态 8/8、反馈 PostgreSQL 20/20、用量 3/3、终态 10/10、远端流 6/6；真实模型基础链路与合成 RAG 已验证，业务资料/目标部署待验
  real_rag_current: 2026-10-09 API 真实合成 RAG 检索/计算14与未记载回答均通过；Chrome 原两轮1/2完整通过、独立编辑分支恢复1/1；Trace/delta/export/messages一致，详情 docs/real-model-acceptance.md
  local_seal: 2026-10-09 本地范围封板；应用基线1b850bc已推送，CI通过来源为用户确认；封板文档hygiene4/4 PASS，来源 /tmp/insightagent-local-seal-hygiene.md 与 .json；外部就绪未验收
  current_audit: 2026-10-09 原四场景3/4完整通过、编辑分支恢复1/1；五任务已记录15642 tokens，失败/放弃规划消耗未知；不能替代业务签收、账单或目标部署
  backup_restore_fixture: scripts/local_stack_snapshot.py 安全测试通过；修正 Compose Chroma /data 挂载后，隔离 fixture 的 PostgreSQL 测试行与 Chroma 测试文档均从新项目卷恢复读回；目标环境 RPO/RTO 未验证
  tooling_current: 最终复核1/1 PASS，含RAG静态17/17、导出静态1/1与drill静态自测，来源 /tmp/insightagent-finalcheck-tooling.md 与 .json；既有协议9/9、task smoke6/6、预检7/7等保留原范围
  pilot_images_current: 后端 pilot-42ccf1f + 前端 pilot-9e78810；此前配对冒烟PASS零残留，本轮只读核对ID及应用差异，镜像未重建；来源 docs/pilot-deployment-preflight.md
  pilot_agent_protocol: scripts/smoke_pilot_images.py --with-agent-fixture 实际 HTTP 协议专项 7/7；5 完成/2 失败，13 规划/5 回答请求；历史传递/会话隔离、两种知识正文分支、来源版本、空正文与 429 用量隔离；日志 /tmp/insightagent-pilot-0209651-smoke.log，仅本地替身
  pilot_compose_current: 保留历史 218f94d 双镜像与固定 PostgreSQL/Chroma 摘要下，随机 loopback/mock fixture 健康启动，重建所有容器后登录/会话/任务/Trace/messages/Chroma 读回，独立资源清理后 PASS；来源 /tmp/insightagent-pilot-218f94d-compose-smoke.log，不替代多轮模型专项、目标部署或备份恢复
  async_rag_ingest: 持久化、幂等、取消与中断恢复落地；新增分批写入、确认进度与 5000 切块预算；沿用前轮 21/21 PostgreSQL/Chroma 隔离集成基线，包含实际 40 文档/400 切块，原始载荷终结后清理
  http_read_parallel: 固定 GET/无请求体且 parallel_read_only=true；15 个静态专项、7 个本机 HTTP/PostgreSQL 场景通过；真实端点只读性/限流/延迟待实证
  tool_dependencies: 显式 DAG 最多 32 节点/128 边，仅公开预览标量绑定 query/expression；26 个静态专项与 7 个 PostgreSQL 场景通过；HTTP/DAG checkpoint 与写入并行延期，目标图生成质量待验证
  task_tool_parallel: 默认 1（串行），1–4 配置仅并发内建与明确声明的 HTTP 读取；15 个专项与 6 个 PostgreSQL 场景通过，进程最多 8 个读取线程；取消/超时丢弃迟到结果
  task_checkpoints: 实验性内建顺序计划，成功前缀复用、独立分支与失败重试；6 个静态专项、9/9 PostgreSQL，HTTP/DAG checkpoint 延期；新 Trace 标注来源且复用 token/cost 归零
  task_reruns: 完整任务分支支持编辑输入、独立会话、幂等与来源分页；7 个既有专项进入门禁，11/11 PostgreSQL 既有回归通过；原任务/Trace/usage 不变
  backend_current: 最终复核 full slice2220/2220、module boundary9/9，来源 /tmp/insightagent-finalcheck-backend.md 与 .json；无应用变更
  release_gate: 最终分阶段本地门禁 backend2/2、frontend4/4、tooling1/1、hygiene4/4 PASS；来源 /tmp/insightagent-finalcheck-{backend,frontend,tooling,hygiene}.md 与 .json
  frontend: 最终复核隔离源码 node217/217、lint0 error/2既有warning、Turbopack/webpack双构建PASS；127个tracked文件与检查提交0e884be一致，排除生成next-env
  e2e_current: Mac开发态composer-keyboard三浏览器桌面/手机6/6；本轮Chrome真实计算/续算/分支恢复和API真实RAG，原四场景3/4完整通过；保留其余既有专项范围
  e2e_ci_incident: frontend-e2e #194/#195 因 bare nextjs-portal not.toContainText 在生产构建误失败；已改为 data-nextjs-dialog 计数 0
  hygiene: 最终复核4/4 PASS，来源 /tmp/insightagent-finalcheck-hygiene.md 与 .json；文档本地链接通过，备份计划/next-env无变更
completed_mainlines:
  - project-completion-audit：本地开发与工程收尾封板，部署/用户签收/真实业务验收按用户决策延期，已知风险与验证边界保留
  - agent-core-alignment：本地实现/契约封板；有界对话上下文、模型 RAG 证据、Observation 决策、Trace 关系和文件导入，真实模型基础链路与合成 RAG 已验证，业务质量仍待验
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
  - 后续按实际使用问题维护；当前没有确认必须新增的功能主线
  - eslint-10-adoption：仅待上游正式兼容后受控升级
next_steps:
  - 当前无必须新增主线，按实际复现的问题维护
  - 部署、用户签收与真实业务验收条件具备后单独启动；写入并行及 HTTP/DAG checkpoint 继续延期
logging_rule: 本文件的状态块保持收敛；正文中的稳定能力摘要、验证口径、维护规则和主线地图不应被整段删除。
---

# InsightAgent 实时计划

## 当前仓库状态

- **`project-completion-audit` 本地开发与工程收尾已封板（2026-10-09）**。用户明确将部署、目标用户签收与真实业务验收移出本次范围；这三项保留为条件具备后的独立验收，不阻塞当前封板。裁决见[收尾审计](../../docs/project-completion-audit.md)。
- 核心能力已完成本地实现与契约验证：Execution Trace、流式输出、有界历史/Memory/RAG、Observation 反馈、工具执行、鉴权、持久化与导出；现有 DAG/只读并发、后台导入及限定步骤恢复范围保持不变。
- 应用与验收工具基线 `1b850bc` 已推送至 main，封板核对时本机与远程引用一致；用户确认该主线 CI 为绿，未独立读取 CI run/artifact。最终复核通过下节本地门禁；未修改应用运行时。
- 已知边界保留：真实 GLM 原四场景 3/4 完整通过、编辑分支恢复 1/1；上下文续算规划回退未执行要求的工具；内置浏览器曾连接失败，原因未确诊。提示约束、合成样本与提供方用量不能证明所有回答正确、真实业务质量或账单成本。详情见[真实模型验收](../../docs/real-model-acceptance.md)。
- 当前候选后端 `pilot-42ccf1f` + 前端 `pilot-9e78810` 的本地替身联调证据保留；生产部署、HTTPS/访问边界、升级回滚和双存储恢复仍未在目标环境验收，不能据本地封板认定外部试点就绪。
- 后续进入按实际问题维护；没有确认必须新增的主线。写入工具并行与 HTTP/DAG checkpoint 继续延期，ESLint 10 仍为非阻塞维护候选。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、OpenAI Chat/Responses、Gemini/Vertex functionCall、Bedrock/Claude Converse toolUse、Anthropic Messages mixed text/tool_use content、顶层 message/delta wrapper、tool_call 单数容器、tool_calls/toolCalls 映射容器、camelCase toolCalls/toolInvocations/toolName/functionName、嵌套 tool 对象、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出与 planner 协议：覆盖常见 REST/JS 字段别名、GraphQL connection pageInfo.totalCount + edges、Elastic/OpenSearch hits、Azure/OData、Meilisearch/Algolia estimatedTotalHits / nbHits、Brave web.results、Bing webPages.totalEstimatedMatches、SearXNG/元搜索 number_of_results、Crossref/学术检索 total-results/message.items、PubMed/NCBI ESearch count/idlist、Europe PMC hitCount/resultList.result、Google Custom Search queries.request[].totalResults/items、Serper/Google Search searchInformation.totalResults/organic、引用型 citations/search_results、organic search、分页型 data/records + meta.page/pagination/paging total、安全千分位总量字符串、显式 result_fields bracket quoted 特殊字段键、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。
- release 工程：静态 release gate、PR auto routing、结构化 Markdown/JSON summary、previous summary 下载诊断、baseline/delta 友好的 release gate trend summary、release/rollback decision_summary、release readiness matrix、backend/frontend queue workflow、artifact diagnostics 与 main 分支严格策略已落地。

## 当前验证基线

2026-10-09 最终复核检查提交 `0e884be`（应用/验收工具基线仍为 `1b850bc`），本轮未改运行时；分阶段重跑以下本地门禁。CI 绿仍按用户确认记录，本地检查与远端 CI 分开。

- 后端门禁 **2/2 PASS**：full slice **2220/2220**、模块 **9/9**，来源 `/tmp/insightagent-finalcheck-backend.md` / `.json`。
- 前端门禁 **4/4 PASS**：node **217/217**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双生产构建。在当前提交的隔离源码副本执行，127 个 tracked 前端文件与检查提交 `0e884be` 一致（排除生成的 next-env）；未复制私人环境或影响本机开发构建。来源 `/tmp/insightagent-finalcheck-frontend.md` / `.json` 与 `/tmp/insightagent-finalcheck-source.json`。
- tooling **1/1 PASS**（含 RAG 静态 **17/17**），隔离 PostgreSQL/Chroma RAG **1/1**、规划等待/取消/迟到结果/重跑 **5/5**；导出静态 **1/1**、部署演练脚本静态自测 PASS（不计目标部署实证）。来源 `/tmp/insightagent-finalcheck-{tooling,rag,planning,export,drill}.log` 与 tooling `.md` / `.json`。
- 本轮 hygiene **4/4 PASS**、六份活跃/验收文档本地链接核对通过；备份计划与 next-env 无变更。前后两次 backend `8000` / frontend `3001` HTTP 200，Chroma reachable。来源 `/tmp/insightagent-finalcheck-hygiene.md` / `.json`。
- [真实 GLM 证据](../../docs/real-model-acceptance.md)沿用先前原四场景 **3/4 完整通过**、编辑分支恢复 **1/1** 与 Trace/delta/导出/消息一致；Mac dev 键盘三浏览器桌面/手机 **6/6** 沿用 `/tmp/insightagent-oct09-keyboard.log`。本轮没有新增模型调用或重跑浏览器专项；规划回退与内置浏览器连接风险保留。
- 候选后端 `pilot-42ccf1f` + 前端 `pilot-9e78810` 的历史替身联调及 Compose 恢复保留原范围，本轮未重建镜像或重跑 Compose。既有 HTTP/DAG/并发/checkpoint 与 RAG 导入专项范围继续保留。本地封板结论不变；业务验收、用户签收和目标环境部署恢复仍延期。

## 当前主线

- 当前本地收尾主线已完成，可进入日常维护或由用户明确的新主线；没有必须继续开发的已确认功能。
- 仅在实际复现问题时修复，并维护既有 API/SSE/Trace/export 契约与主题模块边界。
- 真实业务资料、用户签收和目标环境部署/恢复在条件具备后单独启动；写入并行与 HTTP/DAG checkpoint 继续延期，ESLint 10 待上游兼容后评估。

## 文档收敛边界

- 主线封板后，四份活跃文档的“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”需要收敛。
- README / backend README / frontend README / 实时计划中的长期参考章节、接口范围、运行约定、关键实现位置、SSE/Trace 与 Memory/RAG 说明不应被整段删除。
- 旧失败过程、按轮流水账、重复验证清单和阶段内细碎过程描述应删除或压缩为高信号摘要。

## 维护约定

- `data/insightagent.plan.back.md` 是只读备份计划，永远不要修改。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 测试、e2e、服务启动、端口和提交权限以 `docs/development-runbook.md` 为准。
