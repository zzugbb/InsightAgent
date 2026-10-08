# InsightAgent

可视化、可解释、工具驱动的 AI Agent 工作台，以 Execution Trace、Memory/RAG 与流式输出为核心；鉴权、持久化、导出和工程门禁支撑主链路。

## 当前状态

- 已封板主线：`provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`（含后续运维体验）、`product-ux-polish`（含下一阶段）、`production-operations-readiness`、`security-hardening`、`release-observability-polish`、`test-maintainability-hardening`、`runtime-dependency-modernization`、`next-major-upgrade-readiness`。
- 最近封板：`agent-core-alignment` 的本地实现与契约验证已封板：有界对话上下文、工具反馈决策、RAG 正文/来源证据、Trace 关系与知识文件导入均完成。可进入后续维护或下一条按实际需求选定的主线；真实模型效果验收仍属于外部待验项。
- 当前阶段：持续推进[项目收尾](docs/project-completion-audit.md)，按现有定位修复主链路并核对交付证据；Agent 核心本地实现/契约已封板，真实模型基础链路与合成 RAG 已验证，业务任务质量与目标部署验收继续收尾。
- 当前维护完成：[真实 RAG 验收修复](docs/real-model-acceptance.md)：最终回答接收成功工具/复用结果清单，明确自行推算不等于工具执行；内建检索规划声明实际可绑定字段，检索正文中的数值由后续反馈发起计算。外部 SSE/Trace/export 与规则回退保持原契约；此前规划失败用量、反馈参数和回答增量修复保留。
- A2 [试点镜像与部署入口](docs/pilot-deployment-preflight.md)已准备：84 个后端依赖版本锁定、非 root 默认 embedding 构建缓存通过禁网验证；新增生产 `compose.pilot.yml`、低敏预检/操作入口与健康启动顺序。隔离 mock 下重建全部容器后，登录、会话、任务/Trace 与 Chroma 知识保留；目标部署、TLS、候选镜像真实模型与升级回滚仍待实测。
- A3 本地恢复基础已落地：两份 Compose 的 Chroma 卷改挂当前镜像实际持久路径 `/data`，新增[离线备份与隔离恢复流程](docs/local-stack-backup-restore.md)；独立 fixture 已读回 PostgreSQL 与 Chroma 测试数据。目标环境恢复与 RPO/RTO 仍待验证。
- A4 [后台 RAG 导入](docs/rag-background-ingest.md)的持久化/分批进度与[完整任务分支重跑](docs/task-reruns.md)已完成本地闭环；[任务内工具并发](docs/task-tool-parallel.md)支持内建检索/计算有界并发；[工具依赖与结果引用](docs/tool-dependencies.md)支持显式 DAG、重复工具、拓扑波次与公开预览标量绑定；[HTTP 读取并发](docs/http-read-parallel.md)支持明确声明只读的固定 GET、配置冻结和生命周期协调。[实验性步骤恢复](docs/task-checkpoints.md)已实现内建顺序计划的独立分支、成功前缀复用与当前设置复核。OpenAPI 为 51 操作 / 89 组件；写入工具并行及 HTTP/DAG checkpoint 明确延期，目标运行与用户验收待完成。
- 非阻塞维护候选：ESLint 10 正式采用；2026-09-30 核对锁文件，`eslint-config-next` 内的 `eslint-plugin-react@7.37.5`、`eslint-plugin-import@2.32.0`、`eslint-plugin-jsx-a11y@6.10.2` peer 范围均排除 ESLint 10，React 插件官方兼容修复尚未发布。预检的 1 个外部兼容动作概括这组约束；保持 ESLint `9.39.5` 精确锁定，不强制覆盖 peer 约束。
- 外部 SSE / trace / export / e2e 契约保持兼容；`backend/app`、`backend/scripts` 与 `frontend` 源码继续维持单文件 <= 3000 行边界。

## 当前验证基线

- 本轮收尾：修复 GitHub `frontend-e2e` #194/#195 中 `composer-keyboard.spec.ts` 在生产构建下的误失败。根因是 Playwright 在 `CI=1` 时由 `npm run build && npm run start` 启动，无开发态 `nextjs-portal`，`not.toContainText("Runtime Error")` 在元素缺失时失败；断言改为与同仓库其它 e2e 一致的 `nextjs-portal [data-nextjs-dialog]` 计数为 0，dev 仍可捕获运行时错误对话框，生产无 overlay 时通过。云端 VM 生产模式 Chromium **2/2**（`CI=1 npx playwright test e2e/composer-keyboard.spec.ts --project=chromium`）；`errors` 控制台断言在生产构建下首次执行并通过。门禁一致的前端 node **217/217**（`scripts/ci_run_release_gate.sh` 所列 21 个 `*.node.test.ts`，含 `app/next-major-readiness.node.test.ts` 8 项）；`docs/development-runbook.md` 已补齐该文件，避免与 release gate 列表漂移。文档原先记录的输入法/键盘三浏览器 **6/6** 为用户本机 `npm run dev` 结果，修复后 dev 三浏览器复验**待用户 Mac**；候选镜像未重建，应用实现未变。
- 上轮收尾：[规划等待排查](docs/real-model-acceptance.md)已核对两次约 60 秒异常，补齐离线请求/流耗时统计；不增加超时或重试，根因与恢复体验仍待实证。专项 **11/11**，新增 3 个耗时边界测试，来源 `/tmp/insightagent-provider-latency-static.log`。后端门禁 **2/2 PASS**（full slice **2220/2220**、模块 **9/9**），来源 `/tmp/insightagent-provider-latency-release.md` / `.json`。
- 前轮执行证据后端门禁 **2/2 PASS**，来源 `/tmp/insightagent-execution-evidence-release.md` / `.json`：full slice **2217/2217**、module boundary **9/9**；执行证据专项 **7/7**、独立 PostgreSQL/Chroma 核心场景 **11/11**，来源 `/tmp/insightagent-execution-evidence-{static,postgres}.log`。前端未变，保留上一完整门禁 **10/10 PASS** 的前端 node **217/217**、lint **0 error / 2 个既有 warning**与双构建基线（`/tmp/insightagent-planning-call-usage-release.md` / `.json`）；本轮未重跑全量前端。
- 规划调用用量专项基线：提供方静态 **8/8**、独立 PostgreSQL 反馈/规划 **20/20**、用量汇总 **3/3**、终态 **10/10**、远端流 **6/6**；来源 `/tmp/insightagent-planning-call-usage-{static,postgres,accounting-regression,terminal-regression,stream-regression}.log`。覆盖真实本机 HTTP 空正文/429、完整/部分/缺失用量、首轮回退与后续失败、Trace/delta/export 和请求隔离；模型仅协议替身。该专项为前轮验证，保留其范围；当前后端修复门禁见本节首项。
- 保留空流回退回答 **14/14**、终态 **10/10**、成功保存 **6/6**，来源 `/tmp/insightagent-fallback-trace-*.log`；历史消息/会话静态 **9/11**、前端提示计算 **9/9** 与 Chromium 桌面英文/手机中文 **2/2** 保留 `/tmp/insightagent-message-completion-*.log` 基线。会话/Chroma 核心 **9/9** 保留；本轮未重跑这些交互或模型专项。
- 保留用量计算后端 **8/8** / 前端 **6/6**（`/tmp/insightagent-usage-accounting-{static,frontend}.log`）及公开工具证据 **3/3**、HTTP 并发 **7/7**（`/tmp/insightagent-tool-evidence-{postgres,http-regression}.log`）；本轮未重跑这些专项。
- 已验证前端基线：输入法/键盘三浏览器桌面/手机 **6/6**（用户本机 `npm run dev`，见 `/tmp/insightagent-composer-keyboard-e2e.log`）、生产构建 Chromium **2/2**（本轮云端 VM `CI=1` 专项）、知识导入 Chromium **7/7**、布局复核 **2/2**、Trace **2/2**；来源 `/tmp/insightagent-knowledge-import-e2e.log`、`/tmp/insightagent-knowledge-import-layout.log`、`/tmp/insightagent-trace-flow-e2e.log`。前轮镜像联调仅核对浏览器 API 地址，未重跑这些交互专项；输入法事件 fixture 不代替操作系统人工验收。
- 历史 service-backed 基线：完整 Chromium **77 passed / 1 skipped**、完整重跑 PostgreSQL **11/11**、步骤恢复 **9/9**、内建并发 **6/6**、DAG **7/7**、RAG **21/21** 与 400 切块实写，均保留原验证范围。
- 当前[本地候选镜像](docs/pilot-deployment-preflight.md)：后端 `pilot-0209651` 覆盖执行证据/检索规划修复，ARM64 构建和 78 个 Python 文件源码摘要一致；前端应用代码未变，复用 `pilot-218f94d`。新配对禁网 embedding、生产模式任务/RAG 与 Agent HTTP 协议联调 PASS，清理核验通过；来源 `/tmp/insightagent-pilot-0209651-{backend-retry,source-proof,smoke}.log`。Compose 重建持久化保留原 `218f94d` 配对基线，本轮未重跑；真实模型实测仍为本机开发服务，目标部署待验。
- 镜像 Agent 协议专项 **7/7**：通过实际 HTTP Provider 核对历史传递/会话隔离、两种 RAG 正文驱动的反馈分支、来源/版本、空正文回退/失败及 429 请求间用量隔离；5 个任务完成、2 个失败，13 次规划/5 次回答请求，Trace/delta/导出/用量一致。来源 `/tmp/insightagent-pilot-0209651-smoke.log`，仅本地协议替身；无服务自测 **9/9**、清理失败不输出 PASS 的回归已纳入 tooling，成功摘要在资源清理后输出；前轮 tooling **1/1**、hygiene **3/3** PASS，来源 `/tmp/insightagent-pilot-agent-{tooling,hygiene}.md` / `.json`。
- 2026-10-08 [真实模型配置验收](docs/real-model-acceptance.md)部分通过：智谱 `glm-5.3` 极短流式请求成功，真实任务 **3/3**（计算、历史续算及登录工作台发送）完成；Trace/delta/导出/消息与提供方用量一致。三任务共 **6,405 tokens**，加连通验证共 **6,530 tokens**；本机开发服务实测，未计作候选镜像或目标部署验证。真实 RAG 合成资料检索/反馈计算 2/2 通过；未知日期回答正确但首轮超时回退（严格报告 2/3），注入规划超时的真实回答明确未执行计算；业务资料质量、失败恢复体验与账单成本仍待验收；目标 HTTPS/升级回滚、恢复 RPO/RTO 与用户签收未验证，项目总完成度不估百分比。

## 当前开发计划

1. `agent-core-alignment` 本地实现/契约已封板；终态、失败规划用量、回答提示/增量与反馈参数维护已完成，后续按实际使用问题核对必要修复。
2. `project-completion-audit` 持续收尾：原候选镜像本地复验已完成，本次修复已进入新后端候选并通过配对联调；后续按可复现的主链路问题维护；有效模型配置已验证，后续补业务资料/任务质量与供应商稳定性，补目标部署/恢复与用户验收实证。当前没有确认必须新增的功能主线，写入并行及 HTTP/DAG checkpoint 继续延期。
3. ESLint 10 保留为上游兼容后的维护候选，当前不强制覆盖 peer 约束。

## 稳定契约

- 规划响应校验失败或调用以空正文报错时，保存其实际用量并与先前规划相加；首轮规则回退仍可用，后续调用错误终结任务；部分字段及成本合计保持未知，上游 total 单列保留。无有效用量不估算，非法图仍返回原错误并终结任务。

- 会话消息 completion 为可选兼容扩展（seq、两个白名单结束原因）；只匹配同用户/会话的 assistant 所属任务，旧/损坏 Trace 不推断，任务分页或筛选不影响历史回答提示。消息正文与导出 v1.0 不变。
- 最终回答正文/用量保存递增 Trace.seq，包含空流后的非流式回退，增量查询可见最新结果；工具阶段停止原因传给最终回答；最终 Trace.meta 可选记录 agent_stop_reason/provider_finish_reason，聊天/任务详情只对白名单限制或截断原因提示。正常/未知原因不推断完整性；completed 表示执行结束，不能证明用户目标全部满足。
- 流结束、回退生成完成及成功提交前复核取消/超时；失败和执行器超时保存已记录规划用量及上游返回的最终用量，缺失字段不因部分文字而补估。前端仅有规划记录时保留最终回答用量未知；终态竞争不覆盖其他执行实例或外部取消结果。
- 正常任务成功状态、Trace/usage、assistant 消息与会话更新时间在同一事务提交；回答保存失败则回滚并终结为失败，终态/执行实例竞争落败不插入回答。Memory 与 done 在提交后执行；消息正文及任务终态/SSE/export 字段形状不变。详见[成功保存契约](docs/task-completion.md)。
- 任务/会话汇总、趋势、榜单、会话导出与前端会话统计优先读取有效 overall 用量，字段缺失时按 final + planning 回退，避免重复计数；来源筛选包含规划阶段，任务原始明细与 API 形状不变。详见[用量口径](docs/usage-accounting.md)。
- 远端模型流必须收到 [DONE] 或已知首 choice finish_reason 才算正常结束；无信号 EOF 返回既有 remote_provider_stream_interrupted，保留全部已生成 Trace/递增 seq，不写成功 assistant 或 Memory，不自动重放；空帧不递归，正常结束无文本仍报 remote_provider_empty_response。详见[流结束契约](docs/provider-stream-completion.md)。
- HTTP 工具成功后的模型证据仅取 Trace 中公开的 effective_result_output_keys，复用脱敏，不读取原始响应、输入或注册表配置；最多 6 项/单项 JSON 3000/总 JSON 8000 字符，裁剪保持有效 JSON 并标记 truncated；供反馈与最终回答使用，计数 Observation 与 SSE/Trace/export 不变。
- 聊天输入在 composition 生命周期、原生 isComposing 或兼容 keyCode=229 时将 Enter 留给输入法；正常 Enter 发送、Shift+Enter 换行与发送禁用规则保持一致，不改变后端请求或 SSE/Trace 契约。
- 非 canonical mock 的普通任务在启动时读取本任务创建前已完成的同用户/同会话问答；最多 6 轮、单消息 4,000 字符、序列化历史 16,000 字符。历史 assistant 上下文可选附带最终回答 Trace 的白名单 completion 信号，并计入同一预算；正常结束不证明目标完成，缺失/损坏记录不推断原因。首轮规划、后续决策与最终回答使用同一快照；工具执行/规则回退保留当前原始输入。Trace 仅追加上下文数量/截断摘要；mock 演示与 checkpoint 独立分支保持原行为。
- 模型额外接收已脱敏 RAG Trace 片段/来源/文档版本，最多 6 片段、每片段 1,200 字符、序列化证据 8,000 字符，标注为不可信数据。计数型工具 Observation、既有 SSE/Trace/导出形状兼容；真实提供方合成资料的来源/版本引用已验证，业务资料与引用鲁棒性仍待验收。

- 知识库提供 UTF-8 TXT/Markdown 文件预览与后台导入（每次 1–20 文件，单文件 256 KB / 64,000 字符，总大小 512 KB）；文件名作为来源和文档 ID，同名文件归为同一文档并保留内容版本。提交中和结果不确定时冻结输入，重试复用原载荷/幂等键；明确放弃结果后可返回编辑。复核自动定位版本，检索测试携带目标库；复用既有 API 与共享库管理员权限。

- 跨轮重复检查使用工具名与实际输入；依赖绑定节点在解析后、工具启动前复核，同轮重复节点与工具内部重试保持原行为。反馈决策默认最多 3 轮（AGENT_MAX_ROUNDS=1 保持单轮），安全 Observation 驱动后续行动；后续 query/expression 必须提供非空文本或合法结果绑定，不从提示补缺失参数；多轮任务不生成单轮 checkpoint。Trace 记录轮次/决策来源并汇总所有规划用量；流程图虚线为记录顺序、实线为依赖/决策来源，详情不截断。

- 任务 failed 状态轮询不能提前终止仍在接收的 SSE；保留提供方具体错误事件，避免被通用“流已关闭”覆盖。取消/超时仍按既有流程终止本地连接。

- HTTP 并发需 execution.parallel_read_only=true 且固定 GET/无请求体；资格绑定工厂 runner，配置与上下文冻结，未声明工具保持串行。GET 只读性由配置者确认，见[HTTP 读取契约](docs/http-read-parallel.md)。
- 显式工具图最多 32 节点/128 边，绑定仅限已投影预览标量到 query/expression；图错误拒绝整图，失败/取消/超时阻止依赖调用。Trace.meta 的 plan_node_id/depends_on 为可选扩展，详见[依赖契约](docs/tool-dependencies.md)。
- 任务内并发默认关闭（`TASK_TOOL_MAX_CONCURRENT=1`）；仅就绪的内建检索/计算及明确配置只读的 HTTP GET 可并发，进程最多 8 个读取线程，Trace/终态写入由协调线程串行处理；并发事件允许交错，Trace.meta 增加兼容可选分组信息，详见[并发契约](docs/task-tool-parallel.md)。
- 完整分支重跑从本人已终结任务复制/编辑 prompt，不复制历史结果；实验性 checkpoint 保留输入/计划并复用内建顺序计划的成功前缀。两者均创建独立会话、幂等保存 queued 任务并由既有 stream 执行，原任务和 SSE/Trace/export shape 不变；复用步骤标注来源并清零本任务 token/cost，详见[步骤恢复](docs/task-checkpoints.md)。

- 后台导入新增可空 progress 确认计数，失败/中断保留已确认批次；默认每批 128 切块并遵守 Chroma 上限，每任务最多 5000 切块（超限 422，调用方分拆或降低 overlap）；进度不延长整任务超时，同步 ingest 与 SSE/Trace/export 保持原契约。

- 后台 RAG 导入为兼容扩展：同键同参数返回原任务，查询/取消只对提交者开放，共享写入限管理员；仅排队任务可取消，中断失败先复核数据再重新提交，原同步 ingest 保持可用。

- SSE 事件、`TraceStep`、result summary、safe output、JSON/Markdown export shape 保持稳定；`error.diagnostic` 与 failure audit diagnostic 只包含低敏分类、reason 枚举、recoverability、HTTP 状态族与 detail 存在性。
- 后端全局 HTTP 响应追加安全 header；只增加响应头，不改变 JSON payload、SSE event、trace/delta 或 export body shape。
- HTTP 请求由服务端生成 `X-Request-ID`；低敏 JSON 行日志仅含 request ID、方法、路由模板、状态码与完整响应耗时，404 用 `<unmatched>`。原始路径、query、header、body 与异常正文不进入该日志；SSE 建连后的业务失败仍需结合 SSE/Trace 判断。
- 远端 OpenAI 兼容提供方每次实际 HTTP 尝试记录低敏 `llm_http_attempt` 事件；[运行手册](docs/development-runbook.md)给出离线汇总命令与计数口径。兼容回退产生两次尝试，目标环境采集和告警仍待实证。
- `backend/api_surface_baseline.json` 对运行时 OpenAPI 操作和组件取指纹；任何漂移需按[API 变更记录](docs/api-changelog.md)核对兼容性。该检查不替代字段语义、SSE/Trace/export 行为审查。
- Access token 解析要求 JWT header 为 `alg=HS256`、`typ=JWT`；签名、过期和 subject 校验语义保持不变。
- Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常。
- 生产环境禁止使用默认 `INSIGHT_AGENT_JWT_SECRET` 或其首尾空白包装值签发或验签 access token；开发默认值仍只允许在非生产环境使用。
- 生产环境默认 `INSIGHT_AGENT_JWT_SECRET` 及其首尾空白包装值也不能作为 refresh token 哈希或 secret 加密派生材料；`/health.operations` 按同一口径报告 `default_jwt_secret`。
- `/health.operations`、release gate、previous summary、artifact guard、trend/export diagnostics 的 operator-facing 摘要仅聚合低敏状态、主行动、最高严重级别、失败/告警计数、关注阶段/风险域/scope 与原因枚举；不回显连接串、API key、密钥、联系人、runbook URL、artifact 路径、命令输出、日志正文、环境变量或外部服务响应。
- Operator summary contract 只校验 summary JSON/Markdown 中的低敏状态、主行动、严重级别和标量列表字段，不启动服务、不读取外部日志。
- Release gate trend 对缺少 `operator_summary` 的旧 artifact 按既有 result、step summary 与失败标签派生低敏兼容摘要；新格式仍执行严格 operator contract。
- `backend/scripts/tool_runtime_slice` 主题文件保持 <= 2500 行；拆分主题通过 `_partN` 承载测试，原主题模块继续作为稳定组合入口。
- Tool runtime full slice 与有效 `-k` 筛选继续使用原生 unittest 语义；显式 `-k` 零匹配时输出筛选表达式并保持退出码 5，避免无上下文的选择性回归失败。
- `--list-tests` 可单独或结合 `-k` 列出实际匹配的测试 ID 与总数，不执行测试；零匹配继续返回退出码 5。
- `--list-selections` 列出 queue、task、security、production operations、production reliability 与 reconnect 六个维护选择器的实时覆盖数；任一选择器零匹配即失败，且不能与 `-k` 组合。
- Release gate 即使在首个失败步骤发生时也保留该步骤退出码，并输出 `FAIL` decision/operator summary；空 focus phase 不触发 Bash `set -u` 二次失败。
- 生产环境禁止 `INSIGHT_AGENT_CORS_ORIGINS` 包含 wildcard `*`；非生产 CORS 调试行为保持不变。
- 鉴权依赖对 token parser 异常统一返回低敏 `401 invalid token`，保留 `WWW-Authenticate: Bearer`，不向客户端回显内部配置或解析细节。
- Auth token 签发与刷新会在创建/轮换 refresh token 和写入 auth session 前先校验 access token 签发配置；生产默认 JWT secret 错误不留下会话存储副作用。
- 任务详情页 `trace_semantic` URL 参数保持兼容扩展；语义切换与 operator next-action 提示仅使用既有 status、failure hint/source 与 semantic failure stats 做本地展示，状态文字/色调与轮询控制优先使用 `status_normalized`，均不改变任务、trace 或 export payload。
- Workbench Inspector 语义筛选只调整前端本地 trace 筛选状态：保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure source 诊断 chips 与状态筛选只调整前端本地筛选/展示状态；状态、失败摘要和观测筛选统一优先使用 `status_normalized`，显式 `failure_hint/failure_source` 优先于 trace 文本推断，不改变任务列表 API 与 trace/export payload。
- Task Center 与任务详情页 operator next-action 提示只由现有 status、failure hint/source 与 semantic failure stats 本地派生；Audit Logs operator next-action 提示只由现有 event_type、event_detail 与 task_id 本地派生；不新增后端字段，不改变任务/审计 API、SSE、trace 或 export payload。
- Knowledge Governance operator next-action、共享范围说明与破坏性操作禁用只由现有 query 状态、`chroma_reachable`、知识库 ID 和用户角色本地派生；Knowledge Governance <-> RAG 往返仅切换、聚焦并展开已有前端弹窗，不新增后端字段，不改变 shared RAG 权限或 API shape。
- Runtime Debug RAG 状态加载失败支持原位刷新，缓存状态在刷新失败时继续可见；失败恢复与跨库反馈隔离仅使用现有 query/mutation 状态和 reset，保留输入草稿，不改变 RAG 请求/响应、权限或审计契约。
- Task Center、Audit Logs 与知识库治理的加载错误、陈旧数据保留与原位重试只调整前端 query/presentation 状态，不改变任务、审计或 RAG API shape。
- SSE close 后失败摘要兜底只在流结束但前端尚未进入 terminal phase 时补拉任务/trace 并映射低敏 failure hint，不改变 SSE、任务、trace 或 export payload。
- 默认 settings 仍按 provider/model/api_key 自动选择 `remote` 或 canonical `mock`。
- queued/running/cancel/reconnect 与 task recovery 语义保持稳定。
- `data/insightagent.plan.back.md` 是只读备份计划，永远不参与同步或修改。

## 核心边界

- `PostgreSQL` 保存用户、会话、消息、任务、trace、usage、设置与审计，是完整历史和回放账本。
- `Chroma Memory` 使用会话级 collection `memory_{session_id}`，服务当前对话的语义记忆。
- `Chroma RAG` 使用知识库 collection `kb_{user_hash}_{knowledge_base_id}`，服务跨会话复用资料。
- Chroma 默认连接 `127.0.0.1:8001`；不可达时 Memory/RAG 接口返回 503，任务后的 memory 摘要写入保持 best-effort。
- 仓库主目录为 `backend/`、`frontend/`、`data/`；完整启动和门禁细节以 runbook 为准。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard、生产可靠性治理与主链路 e2e / CI tooling 已落地。
- 观测体验：失败诊断、任务回放、Trace 语义过滤、Task Center/任务详情/Audit Logs operator next-action、Audit Logs 服务端 keyword 与跨视图 Failure 回放已落地。
- RAG 产品体验：知识库版本明细、source/document 文档组、文档组删除、召回摘要、质量分布、筛选与 distance 解释已落地。
- Provider/tool 兼容：常见搜索总量/命中归一化、多 provider planner 工具调用形态、JSON 字符串参数与 failed reconnect 错误码复原已落地。

## SSE 与 TraceStep 契约（当前实现）

`GET /api/tasks/{task_id}/stream` 的 `event: trace` 中 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。

当前 SSE 事件类型：

- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `cancelled`
- `timeout`
- `done`
- `error`

对齐规则：

- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中可先为空或阶段性刷新，REST 中返回完整内容。
- 前端实时流、历史 trace 与导出回放都按同一 `TraceStep` 结构消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 知识库级 collection：`kb_{user_hash}_{knowledge_base_id}`（用户隔离）
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

### 通俗理解：为什么有 RAG 还需要 Memory

- `PostgreSQL`：完整账本，保存会话、消息、任务、trace、usage。
- `Chroma Memory`：当前会话便签本，保存可语义召回的会话记忆片段。
- `Chroma RAG`：长期知识库，保存导入文档的分块内容。

三者分工不同：

- `RAG` 解决“系统知道哪些外部资料”。
- `Memory` 解决“当前会话刚刚确认了什么偏好和约束”。
- `PostgreSQL` 解决“完整历史如何留档和回放”。

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
├── docs/
└── data/
```

## 运行与门禁

```bash
docker compose up -d chroma
./start_insightagent.command
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_release_readiness_matrix.sh --format markdown
```

`scripts/ci_run_release_gate.sh` 的 Markdown/JSON summary 会保留 summary kind、summary schema version、service-required 标识、resolved phases、逐步结果、步骤聚合计数、失败步骤标签、release/rollback `decision_summary` 与 `operator_summary`；service-backed e2e 仍按 runbook 单独执行。
`scripts/ci_download_previous_release_gate_summary.sh` 会在 GitHub release-gate workflow 中尝试下载同分支上一条 successful `release-gate-summary` artifact；缺少 `gh`、分支、run id、历史 run 或 artifact 时只输出低敏诊断和 `operator_summary` 并保留 baseline 路径。
`scripts/ci_release_gate_trend_summary.sh` 可从当前和可选上一份 release gate JSON summary 生成趋势摘要，Markdown 直接展示当前/上一份 operator 状态、主行动和关注阶段，并在 JSON 中透传 release/rollback `decision_summary` 与 `operator_summary`；GitHub release-gate workflow 会产出并上传 `release-gate-trend-summary` artifact。
`scripts/ci_assert_operator_summary_contract.sh` 可对 release/trend/artifact/export 等 summary JSON 和可选 Markdown 运行低敏 operator 摘要契约检查；该检查已纳入 tooling 自测、release-gate workflow 与 release readiness matrix。
GitHub release-gate workflow 将 release Markdown 固定写入 `/tmp/release-gate-summary.md`，再追加到当前 step summary；后置契约校验与 artifact 上传复用该文件，不依赖跨 step 的 `$GITHUB_STEP_SUMMARY`。
`scripts/ci_assert_artifact_stage_health.sh` 会为 e2e artifact stage guard 输出低敏 `operator_summary`，用于区分可继续、需复核 warning、需补齐 artifact 的值班行动。
`scripts/ci_export_diagnostics_overview.sh` 会把 backend/frontend diagnostics 与 artifact guard 结果汇总为 overview，并输出低敏 `operator_summary` 便于值班快速判断缺失输入、warning 或 guard failure。

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

默认 Chroma 连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

详细测试、e2e、启动和提交流程以 [`docs/development-runbook.md`](docs/development-runbook.md) 为准。

## 下一步

- [项目收尾](docs/project-completion-audit.md)持续进行：本轮修复 `frontend-e2e` 输入法用例在生产构建下的覆盖层断言，等待 PR 上 GitHub `frontend-e2e` 复验；补 A2/A3 目标部署/恢复与 A5 真实用户签收证据；修复后 dev 三浏览器输入法复验待用户 Mac。
- [Agent 核心对齐](docs/agent-core-alignment.md)本地实现与契约已封板；真实模型效果与目标部署/恢复验收仍待外部资源。

## 文档维护约定

- 活跃进度块只收敛“当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要”。
- README 中的长期参考章节、接口范围、运行约定、实现入口、SSE/Trace 与 Memory/RAG 说明不应在封板收敛时被整段删除。
- 长串历史流水账、阶段内小切片、旧失败过程和重复验证清单不继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
