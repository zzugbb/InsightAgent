# InsightAgent Backend

FastAPI 后端，提供 Auth、会话/任务、SSE、Trace、PostgreSQL、Memory、RAG、导出、usage、审计与 tool runtime 能力；默认演示路径为 canonical `mock`，也支持 OpenAI-compatible `remote`。

## 当前状态

- **`project-completion-audit` 本地开发与工程收尾已封板（2026-10-09）**。用户明确将部署、目标用户签收与真实业务验收移出本次范围；这三项保留为条件具备后的独立验收，不阻塞当前封板。裁决见[收尾审计](../docs/project-completion-audit.md)。
- 核心能力已完成本地实现与契约验证：Execution Trace、流式输出、有界历史/Memory/RAG、Observation 反馈、工具执行、鉴权、持久化与导出；现有 DAG/只读并发、后台导入及限定步骤恢复范围保持不变。
- 应用与验收工具基线 `1b850bc` 已推送至 main，封板核对时本机与远程引用一致；用户确认该主线 CI 为绿，未独立读取 CI run/artifact。最终复核通过下节本地门禁；未修改应用运行时。
- 已知边界保留：真实 GLM 原四场景 3/4 完整通过、编辑分支恢复 1/1；上下文续算规划回退未执行要求的工具；内置浏览器曾连接失败，原因未确诊。提示约束、合成样本与提供方用量不能证明所有回答正确、真实业务质量或账单成本。详情见[真实模型验收](../docs/real-model-acceptance.md)。
- 当前候选后端 `pilot-42ccf1f` + 前端 `pilot-9e78810` 的本地替身联调证据保留；生产部署、HTTPS/访问边界、升级回滚和双存储恢复仍未在目标环境验收，不能据本地封板认定外部试点就绪。
- 后续进入按实际问题维护；没有确认必须新增的主线。写入工具并行与 HTTP/DAG checkpoint 继续延期，ESLint 10 仍为非阻塞维护候选。

## 当前验证基线

2026-10-09 最终复核检查提交 `0e884be`（应用/验收工具基线仍为 `1b850bc`），本轮未改运行时；分阶段重跑以下本地门禁。CI 绿仍按用户确认记录，本地检查与远端 CI 分开。

- 后端门禁 **2/2 PASS**：full slice **2220/2220**、模块 **9/9**，来源 `/tmp/insightagent-finalcheck-backend.md` / `.json`。
- 前端门禁 **4/4 PASS**：node **217/217**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双生产构建。在当前提交的隔离源码副本执行，127 个 tracked 前端文件与检查提交 `0e884be` 一致（排除生成的 next-env）；未复制私人环境或影响本机开发构建。来源 `/tmp/insightagent-finalcheck-frontend.md` / `.json` 与 `/tmp/insightagent-finalcheck-source.json`。
- tooling **1/1 PASS**（含 RAG 静态 **17/17**），隔离 PostgreSQL/Chroma RAG **1/1**、规划等待/取消/迟到结果/重跑 **5/5**；导出静态 **1/1**、部署演练脚本静态自测 PASS（不计目标部署实证）。来源 `/tmp/insightagent-finalcheck-{tooling,rag,planning,export,drill}.log` 与 tooling `.md` / `.json`。
- 本轮 hygiene **4/4 PASS**、六份活跃/验收文档本地链接核对通过；备份计划与 next-env 无变更。前后两次 backend `8000` / frontend `3001` HTTP 200，Chroma reachable。来源 `/tmp/insightagent-finalcheck-hygiene.md` / `.json`。
- [真实 GLM 证据](../docs/real-model-acceptance.md)沿用先前原四场景 **3/4 完整通过**、编辑分支恢复 **1/1** 与 Trace/delta/导出/消息一致；Mac dev 键盘三浏览器桌面/手机 **6/6** 沿用 `/tmp/insightagent-oct09-keyboard.log`。本轮没有新增模型调用或重跑浏览器专项；规划回退与内置浏览器连接风险保留。
- 候选后端 `pilot-42ccf1f` + 前端 `pilot-9e78810` 的历史替身联调及 Compose 恢复保留原范围，本轮未重建镜像或重跑 Compose。既有 HTTP/DAG/并发/checkpoint 与 RAG 导入专项范围继续保留。本地封板结论不变；业务验收、用户签收和目标环境部署恢复仍延期。

## 下一步后端计划

- 当前本地收尾主线已完成，可进入日常维护或由用户明确的新主线；没有必须继续开发的已确认功能。
- 仅在实际复现问题时修复，并维护既有 API/SSE/Trace/export 契约与主题模块边界。
- 真实业务资料、用户签收和目标环境部署/恢复在条件具备后单独启动；写入并行与 HTTP/DAG checkpoint 继续延期，ESLint 10 待上游兼容后评估。

## 稳定契约

- 规划响应校验失败或调用以空正文报错时，保存其实际用量并与先前规划相加；首轮规则回退仍可用，后续调用错误终结任务；部分字段及成本合计保持未知，上游 total 单列保留。无有效用量不估算，非法图仍返回原错误并终结任务。

- 会话消息 completion 为可选兼容扩展（seq、两个白名单结束原因）；只匹配同用户/会话的 assistant 所属任务，旧/损坏 Trace 不推断，任务分页或筛选不影响历史回答提示。消息正文与导出 v1.0 不变。
- 最终回答正文/用量保存递增 Trace.seq，包含空流后的非流式回退，增量查询可见最新结果；工具阶段停止原因传给最终回答；最终 Trace.meta 可选记录 agent_stop_reason/provider_finish_reason，聊天/任务详情只对白名单限制或截断原因提示。正常/未知原因不推断完整性；completed 表示执行结束，不能证明用户目标全部满足。
- 流结束、回退生成完成及成功提交前复核取消/超时；失败和执行器超时保存已记录规划用量及上游返回的最终用量，缺失字段不因部分文字而补估。前端仅有规划记录时保留最终回答用量未知；终态竞争不覆盖其他执行实例或外部取消结果。
- 正常任务成功状态、Trace/usage、assistant 消息与会话更新时间在同一事务提交；回答保存失败则回滚并终结为失败，终态/执行实例竞争落败不插入回答。Memory 与 done 在提交后执行；消息正文及任务终态/SSE/export 字段形状不变。详见[成功保存契约](../docs/task-completion.md)。
- 任务/会话汇总、趋势、榜单、会话导出与前端会话统计优先读取有效 overall 用量，字段缺失时按 final + planning 回退，避免重复计数；来源筛选包含规划阶段，任务原始明细与 API 形状不变。详见[用量口径](../docs/usage-accounting.md)。
- 远端模型流必须收到 [DONE] 或已知首 choice finish_reason 才算正常结束；无信号 EOF 返回既有 remote_provider_stream_interrupted，保留全部已生成 Trace/递增 seq，不写成功 assistant 或 Memory，不自动重放；空帧不递归，正常结束无文本仍报 remote_provider_empty_response。详见[流结束契约](../docs/provider-stream-completion.md)。
- HTTP 工具成功后的模型证据仅取 Trace 中公开的 effective_result_output_keys，复用脱敏，不读取原始响应、输入或注册表配置；最多 6 项/单项 JSON 3000/总 JSON 8000 字符，裁剪保持有效 JSON 并标记 truncated；供反馈与最终回答使用，计数 Observation 与 SSE/Trace/export 不变。
- 聊天输入在 composition 生命周期、原生 isComposing 或兼容 keyCode=229 时将 Enter 留给输入法；正常 Enter 发送、Shift+Enter 换行与发送禁用规则保持一致，不改变后端请求或 SSE/Trace 契约。
- 非 canonical mock 的普通任务在启动时读取本任务创建前已完成的同用户/同会话问答；最多 6 轮、单消息 4,000 字符、序列化历史 16,000 字符。历史 assistant 上下文可选附带最终回答 Trace 的白名单 completion 信号，并计入同一预算；正常结束不证明目标完成，缺失/损坏记录不推断原因。首轮规划、后续决策与最终回答使用同一快照；工具执行/规则回退保留当前原始输入。Trace 仅追加上下文数量/截断摘要；mock 演示与 checkpoint 独立分支保持原行为。
- 模型额外接收已脱敏 RAG Trace 片段/来源/文档版本，最多 6 片段、每片段 1,200 字符、序列化证据 8,000 字符，标注为不可信数据。计数型工具 Observation、既有 SSE/Trace/导出形状兼容；真实提供方合成资料的来源/版本引用已验证，业务资料与引用鲁棒性仍待验收。

- 知识库提供 UTF-8 TXT/Markdown 文件预览与后台导入（每次 1–20 文件，单文件 256 KB / 64,000 字符，总大小 512 KB）；文件名作为来源和文档 ID，同名文件归为同一文档并保留内容版本。提交中和结果不确定时冻结输入，重试复用原载荷/幂等键；明确放弃结果后可返回编辑。复核自动定位版本，检索测试携带目标库；复用既有 API 与共享库管理员权限。

- 跨轮重复检查使用工具名与实际输入；依赖绑定节点在解析后、工具启动前复核，同轮重复节点与工具内部重试保持原行为。反馈决策默认最多 3 轮（AGENT_MAX_ROUNDS=1 保持单轮），安全 Observation 驱动后续行动；后续 query/expression 必须提供非空文本或合法结果绑定，不从提示补缺失参数；多轮任务不生成单轮 checkpoint。Trace 记录轮次/决策来源并汇总所有规划用量；流程图虚线为记录顺序、实线为依赖/决策来源，详情不截断。

- 任务 failed 状态轮询不能提前终止仍在接收的 SSE；保留提供方具体错误事件，避免被通用“流已关闭”覆盖。取消/超时仍按既有流程终止本地连接。

- HTTP 并发需 execution.parallel_read_only=true 且固定 GET/无请求体；资格绑定工厂 runner，配置与上下文冻结，未声明工具保持串行。GET 只读性由配置者确认，见[HTTP 读取契约](../docs/http-read-parallel.md)。
- 显式工具图最多 32 节点/128 边，绑定仅限已投影预览标量到 query/expression；图错误拒绝整图，失败/取消/超时阻止依赖调用。Trace.meta 的 plan_node_id/depends_on 为可选扩展，详见[依赖契约](../docs/tool-dependencies.md)。
- 任务内并发默认关闭（`TASK_TOOL_MAX_CONCURRENT=1`）；仅就绪的内建检索/计算及明确配置只读的 HTTP GET 可并发，进程最多 8 个读取线程，Trace/终态写入由协调线程串行处理；并发事件允许交错，Trace.meta 增加兼容可选分组信息，详见[并发契约](../docs/task-tool-parallel.md)。
- 完整分支重跑从本人已终结任务复制/编辑 prompt，不复制历史结果；实验性 checkpoint 保留输入/计划并复用内建顺序计划的成功前缀。两者均创建独立会话、幂等保存 queued 任务并由既有 stream 执行，原任务和 SSE/Trace/export shape 不变；复用步骤标注来源并清零本任务 token/cost，详见[步骤恢复](../docs/task-checkpoints.md)。

- 后台导入新增可空 progress 确认计数，失败/中断保留已确认批次；默认每批 128 切块并遵守 Chroma 上限，每任务最多 5000 切块（超限 422，调用方分拆或降低 overlap）；进度不延长整任务超时，同步 ingest 与 SSE/Trace/export 保持原契约。

- 后台 RAG 导入为兼容扩展：同键同参数返回原任务，查询/取消只对提交者开放，共享写入限管理员；仅排队任务可取消，中断失败先复核数据再重新提交，原同步 ingest 保持可用。

- SSE 事件、REST `TraceStep`、result summary、safe output 与 JSON/Markdown export shape 保持稳定。
- 全局 HTTP 响应追加 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Permissions-Policy` 与 `Cross-Origin-Opener-Policy`；该安全头层不改变业务响应体、SSE event、trace/delta 或 export body shape。
- HTTP 响应增加服务端生成的 `X-Request-ID`，允许已配置 CORS 来源读取；低敏 JSON 行日志只记录 request ID、方法、路由模板、状态码与完整响应耗时，404 使用 `<unmatched>`。不记录原始 URL/query、请求 header/body 或异常正文；SSE 业务失败仍需看流事件与 Trace。
- 运行时 OpenAPI 操作/组件指纹与 `api_surface_baseline.json` 一致性已纳入 full slice；新增或修改接口需审查兼容性并更新记录。指纹不能自动证明 SSE/Trace/export 的运行时语义兼容。
- Access token 解析要求 JWT header 为 `alg=HS256`、`typ=JWT`；签名、过期和 subject 校验语义保持不变。
- Refresh token 请求会先 trim 并拒绝空白值；服务层将空白 refresh token 视为无效 token 返回，不暴露内部异常。
- 生产环境禁止使用默认 `INSIGHT_AGENT_JWT_SECRET` 或其首尾空白包装值签发或验签 access token；开发默认值仍只允许在非生产环境使用。
- 生产环境默认 `INSIGHT_AGENT_JWT_SECRET` 及其首尾空白包装值也不能作为 refresh token 哈希或 secret 加密派生材料；`/health.operations` 按同一口径报告 `default_jwt_secret`。
- `/health.operations`、release gate、previous summary、artifact guard、trend/export diagnostics 的 operator-facing 摘要仅聚合低敏状态、主行动、最高严重级别、失败/告警计数、关注阶段/风险域/scope 与原因枚举；不回显连接串、API key、密钥、联系人、runbook URL、artifact 路径、命令输出、日志正文、环境变量或外部服务响应。
- Operator summary contract 只校验 summary JSON/Markdown 中的低敏状态、主行动、严重级别和标量列表字段，不启动服务、不读取外部日志。
- Release gate trend 对缺少 `operator_summary` 的旧 artifact 按既有 result、step summary 与失败标签派生低敏兼容摘要；新格式仍执行严格 operator contract。
- `scripts/tool_runtime_slice` 主题文件保持 <= 2500 行；拆分主题通过 `_partN` 承载测试，原主题模块继续作为稳定组合入口。
- Full slice 与有效 `-k` 筛选继续使用原生 unittest 语义；显式 `-k` 零匹配时输出筛选表达式并保持退出码 5。
- `--list-tests` 可单独或结合 `-k` 列出实际匹配的测试 ID 与总数而不执行测试；零匹配继续返回退出码 5。
- `--list-selections` 动态校验 queue、task、security、production operations、production reliability 与 reconnect 六个维护选择器；任一零匹配即失败，且不能与 `-k` 组合。
- Release gate 首个失败步骤保留原退出码并输出 `FAIL` decision/operator summary；空 focus phase 不触发 Bash `set -u` 二次失败。
- 生产环境禁止 `INSIGHT_AGENT_CORS_ORIGINS` 包含 wildcard `*`；非生产 CORS 调试行为保持不变。
- 鉴权依赖对 token parser 异常统一返回低敏 `401 invalid token`，保留 `WWW-Authenticate: Bearer`，不向客户端回显内部配置或解析细节。
- Auth token 签发与刷新会在创建/轮换 refresh token 和写入 auth session 前先校验 access token 签发配置；生产默认 JWT secret 错误不留下会话存储副作用。
- `tool_start/tool_end` 与 trace action 节点通过 `step_id` 对齐。
- remote provider 错误在 SSE `error` 中保持结构化 `code / fatal / retryable / detail / status_code`，并在 SSE 与 failure audit 中追加低敏 `diagnostic.category/reason/recoverability/http_status_family/has_detail`。
- 任务详情页可通过兼容 URL 参数 `trace_semantic` 回放语义 Trace；前端语义切换、operator next-action 提示与 normalized 状态/轮询控制均不改变后端任务、trace 或 export payload。
- Workbench Inspector 语义筛选清理旧 search/kind 干扰属于前端本地状态变更，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure drilldown、normalized 状态/失败摘要与显式 `failure_hint` 优先级均为前端本地语义，不改变任务列表 API、后端 trace 或 export shape。
- Task Center 与任务详情页 operator next-action 提示只由现有 status、failure hint/source 与 semantic failure stats 本地派生；Audit Logs operator next-action 提示只由现有 event_type、event_detail 与 task_id 本地派生；不新增后端字段，不改变任务/审计 API、SSE、trace 或 export payload。
- Knowledge Governance operator next-action、共享范围说明与破坏性操作禁用只由现有 query 状态、`chroma_reachable`、知识库 ID 和用户角色本地派生；Knowledge Governance <-> RAG 往返仅切换、聚焦并展开已有前端弹窗，不新增后端字段，不改变 shared RAG 权限或 API shape。
- Runtime Debug RAG 状态加载失败支持原位刷新，缓存状态在刷新失败时继续可见；失败恢复与跨库反馈隔离仅使用现有 query/mutation 状态和 reset，保留输入草稿，不改变 RAG 请求/响应、权限或审计契约。
- Task Center、Audit Logs 与知识库治理列表的错误恢复/陈旧数据保留不改变任务、审计或 RAG API shape。
- 前端 SSE close 后失败摘要兜底只补拉既有任务/trace 并映射低敏 failure hint，不改变后端 SSE、任务、trace 或 export payload。
- Memory/RAG collection 命名、Chroma 503 降级、shared knowledge base 权限语义保持稳定。
- 默认 settings 语义保持不变：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。

## HTTP 接口范围

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- `GET /api/auth/users`（admin only）
- `GET /api/auth/me`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`

`GET /api/settings` 的响应包含只读 `task_queue_diagnostics`，用于观察全局、当前用户和可选当前会话的 active/waiting/available 计数、限额状态、压力状态与等待策略。该字段不参与用户设置保存，不暴露内部 task ids，也不改变 SSE / trace / export payload。

- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/export/json`
- `GET /api/sessions/{session_id}/export/markdown`
- `GET /api/sessions/{session_id}/memory/status`
- `GET /api/sessions/{session_id}/usage/summary`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=&query=`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/tasks/{task_id}/reruns`（HTTP 201，独立会话、幂等 queued 分支；可选 checkpoint_step_id 创建限定步骤恢复）
- `GET /api/tasks/{task_id}/checkpoints`（本人实验性步骤恢复候选，不返回结果正文）
- `GET /api/tasks/{task_id}/reruns?limit=&offset=`（本人来源与直接分支分页）
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`
- `GET /api/tasks/usage/summary`
- `GET /api/tasks/usage/dashboard`
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/ingest-jobs`（HTTP 202，幂等受理）
- `GET /api/rag/ingest-jobs`（当前用户任务列表）
- `GET /api/rag/ingest-jobs/{job_id}`
- `POST /api/rag/ingest-jobs/{job_id}/cancel`（仅排队任务）
- `POST /api/rag/query`
- `GET /api/rag/knowledge-bases`
- `POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}/documents`

补充约定：

- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`。
- `GET /api/tasks*` 相关响应包含 `status_normalized`、`status_label`、`status_rank`。
- usage 接口支持来源维度统计：`provider / estimated / mixed / legacy`。
- `shared-*` 知识库走共享命名空间；admin 可写，普通用户只读。

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`task_reruns`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- `app/providers/`：provider 抽象、mock provider、OpenAI-compatible remote provider
- `app/services/chat_execution_service.py`：任务流编排与 SSE 主链
- `app/services/task_rerun_{service,schema}.py` 与 `app/api/routes/task_reruns.py`：完整任务分支的原子创建、幂等、独立会话与来源关系；详见[任务分支契约](../docs/task-reruns.md)
- `app/services/task_tool_{execution,parallel}.py`：任务工具协调、内建读取并发窗口、共享线程上限及顺序 Trace 合并
- `app/services/task_queue_service.py`：单进程任务执行槽位、capacity-aware oldest eligible FIFO 等待调度、安全等待快照、等待项移除与测试重置入口
- `app/services/tool_runtime.py`：tool runtime 兼容 facade，汇总旧导出路径
- `app/services/tool_runtime_planning.py`：planner、provider planner 与 payload normalization
- `app/services/task_checkpoint_service.py`：内建顺序计划资格、成功前缀快照与新 Trace/usage 复用；分支创建与既有任务执行接管
- `app/services/tool_plan_dependencies.py`：显式工具依赖图校验、稳定拓扑波次与公开预览标量绑定；`task_tool_execution.py` 协调执行与持久化，`task_tool_parallel.py` 限定内建工具并发
- `app/services/tool_runtime_display.py`：tool 显示名、语义分类、输出归一化与 `run_tool` 旧导出实现
- `app/services/tool_runtime_execution.py`：runtime context、attempt 与前半段执行语义
- `app/services/tool_runtime_execution_flow.py`：trace event、RAG follow-up、iteration 与 service effects
- `app/services/tool_runtime_http_json.py`：HTTP JSON request/template/mapping 核心
- `app/services/tool_runtime_http_json_execution.py`：HTTP JSON runner、execution spec、summary 与 diagnostics
- `app/services/tool_http_parallel_policy.py`：HTTP GET 显式只读资格、固定方法/请求体校验与弱引用 runner 身份登记
- `app/services/tool_runtime_http_json_response.py`：响应读取、解码、错误格式化和敏感信息脱敏
- `app/services/tool_runtime_registry.py`：registry/file/provider-source facade
- `app/services/tool_runtime_registry_settings.py`：settings override、provider artifacts 与 diagnostics 实现
- `app/services/tool_runtime_registry_runtime.py`：registry service action、preflight 与 runtime artifacts 实现
- `app/services/tool_runtime_registry_public.py`：兼容 wrapper 安装器
- `app/services/chat_persistence_service.py`：会话/任务持久化与治理列处理
- `app/services/chat_persistence_trace_export.py`：Trace 展示、响应摘要与任务 export
- `app/services/chat_persistence_usage.py`：usage summary/dashboard 与 session export response summary
- `scripts/tool_runtime_slice/`：后端 slice 测试主题包；`backend/scripts/test_tool_runtime_slice.py` 是兼容入口
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/conversation_context.py` / `agent_knowledge_context.py`：有界会话快照与模型 RAG 正文/版本证据
- `app/services/agent_tool_context.py`：公开 HTTP 工具结果的模型证据、脱敏与 JSON 预算；不改变 Trace/Observation 展示
- `app/services/chroma_rag_service.py`：RAG ingest/query/status、knowledge base list/clear/delete 与 shared/private 语义
- `app/services/rag_ingest_{jobs,schema,worker,runner}.py` 与 `app/api/routes/rag_ingest.py`：持久化后台导入、分批确认进度、领取/恢复与子进程监管；共享 lazy chunking 在 `app/services/rag_chunking.py`，详见[后台导入契约](../docs/rag-background-ingest.md)
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 usage，供任务列表、导出与 dashboard 复用

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：

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

对齐说明：

- `event: trace` 的 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。
- `tool_start/tool_end` 使用与 action 节点一致的 `step_id`，与 trace 节点一一对齐。
- `trace/delta?after_seq=` 可在任务流式进行中拉取阶段性 `observation` 刷新内容。
- remote provider 异常会被归一成结构化错误码，并在 SSE `error` 中透传稳定的 `code / fatal / retryable / detail / status_code`。
- SSE `error.diagnostic` 是新增低敏摘要字段，包含稳定 `reason` 枚举；旧客户端可忽略。

## 当前实现边界

- `trace/delta` 支持 `limit` 参数控制单次增量返回量；当前默认 `200`，最大 `500`。
- `GET /api/tasks/usage/summary` 与 `GET /api/tasks/usage/dashboard` 都已支持 usage 来源统计；当前来源语义是 `provider / estimated / mixed / legacy`。
- 任务相关对外读取优先走 task row 上的规范化治理摘要与 parsed trace 主干，不鼓励在 route 层继续扩写 sibling fallback。
- 默认 settings 语义是：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`；remote `base_url/api_key` 继承链已打通到 get/save/validate。
- shared RAG 语义当前保持 `shared-*` 命名空间约定：admin 可写共享库，普通用户对共享库只读。
- registry extra tool / override 的真实执行器入口以 `execution.kind=http_json` 为主；请求模板、响应字段映射与既有 runtime semantic/preview/export 主链保持同一契约。
- 显式给 tool 配了 `execution` 时，当前语义是“宁可报配置错，也不回退 stub”；provider/source 治理不会把 real tool 假阳性地跑成本地模板行为。
- provider/source/global settings 侧会把静态可判定的 `execution` 坏配置归一成 registry diagnostics。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- RAG collection 命名：`kb_{user_hash}_{knowledge_base_id}`
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务后的摘要写入为 best-effort

### 通俗分工（后端视角）

- `PostgreSQL`：业务主存储，保存用户、会话、消息、任务、trace、usage、设置、审计。
- `Chroma Memory`：会话级语义记忆，服务当前对话上下文。
- `Chroma RAG`：知识库级文档检索，服务跨会话复用的资料。

## 本地运行

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如需重新创建虚拟环境：

```bash
cd backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

如需将历史 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
backend/.venv/bin/python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

常用校验：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue
cd backend && PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py
bash scripts/ci_run_release_gate.sh --phase auto
```

`scripts/ci_run_release_gate.sh` 的 Markdown/JSON summary 会保留 summary kind、summary schema version、service-required 标识、resolved phases、逐步结果、步骤聚合计数、失败步骤标签、release/rollback `decision_summary` 与 `operator_summary`；service-backed e2e 仍按 runbook 单独执行。
`scripts/ci_download_previous_release_gate_summary.sh` 会在 GitHub release-gate workflow 中尝试下载同分支上一条 successful `release-gate-summary` artifact；缺少 `gh`、分支、run id、历史 run 或 artifact 时只输出低敏诊断和 `operator_summary` 并保留 baseline 路径。
`scripts/ci_release_gate_trend_summary.sh` 可从当前和可选上一份 release gate JSON summary 生成趋势摘要，Markdown 直接展示当前/上一份 operator 状态、主行动和关注阶段，并在 JSON 中透传 release/rollback `decision_summary` 与 `operator_summary`；GitHub release-gate workflow 会产出并上传 `release-gate-trend-summary` artifact。
`scripts/ci_assert_operator_summary_contract.sh` 可对 release/trend/artifact/export 等 summary JSON 和可选 Markdown 运行低敏 operator 摘要契约检查；该检查已纳入 tooling 自测、release-gate workflow 与 release readiness matrix。
GitHub release-gate workflow 将 release Markdown 固定写入 `/tmp/release-gate-summary.md`，再追加到当前 step summary；后置契约校验与 artifact 上传复用该文件，不依赖跨 step 的 `$GITHUB_STEP_SUMMARY`。
`scripts/ci_assert_artifact_stage_health.sh` 会为 e2e artifact stage guard 输出低敏 `operator_summary`，用于区分可继续、需复核 warning、需补齐 artifact 的值班行动。
`scripts/ci_export_diagnostics_overview.sh` 会把 backend/frontend diagnostics 与 artifact guard 结果汇总为 overview，并输出低敏 `operator_summary` 便于值班快速判断缺失输入、warning 或 guard failure。

如需 Memory / RAG 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

常用运行参数：

- `TRACE_PERSIST_MIN_INTERVAL_SEC`：trace 增量持久化最小间隔
- `STREAM_RECONNECT_POLL_FAST_SEC`：running reconnect 快轮询间隔
- `STREAM_RECONNECT_POLL_MAX_SEC`：running reconnect 慢轮询上限
- `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`：reconnect heartbeat 间隔
- `TASK_TIMEOUT_SEC`：任务超时秒数
- `TASK_QUEUE_MAX_CONCURRENT`：单 backend 进程内同时执行的流式任务数，默认 `32`
- `TASK_QUEUE_POLL_INTERVAL_SEC`：queued 任务等待执行槽位时的 SSE 状态刷新间隔，默认 `0.25`
- `TASK_EXECUTION_OWNER_ID`：当前 backend 执行实例 ID，多实例部署时应为每个实例设置唯一稳定值
- `TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC`：running 任务刷新 DB heartbeat 的最小间隔，默认 `2.0`
- `TASK_EXECUTION_STALE_AFTER_SEC`：启动恢复时接管其他实例 stale running 任务的阈值，默认 `0` 关闭
- `INSIGHT_AGENT_BACKUP_ENABLED`：生产备份是否已启用，默认 `false`
- `INSIGHT_AGENT_BACKUP_PROVIDER`：备份提供方标识；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_BACKUP_RESTORE_RUNBOOK_URL`：恢复 runbook 链接；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_BACKUP_LAST_RESTORE_DRILL_AT`：最近一次恢复演练时间（ISO-8601），用于判断恢复演练新鲜度
- `INSIGHT_AGENT_OPERATIONS_RUNBOOK_URL`：生产运维 runbook 链接；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_INCIDENT_CONTACT`：生产值班/应急联系人；`/health` 仅暴露是否已配置
- `INSIGHT_AGENT_INCIDENT_LAST_DRILL_AT`：最近一次应急响应演练时间（ISO-8601）；`/health` 仅暴露演练记录与新鲜度摘要
- `INSIGHT_AGENT_STATUS_PAGE_URL`：状态页链接；`/health` 仅暴露是否已配置

测试、e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- registry 治理语义已封板，不优先继续扩大旧 fallback 兼容面，也不继续维护已归档的 runtime spec 历史文档。
- 文档收敛只处理当前状态、验证基线、下一步计划/候选主线、稳定契约和高信号摘要；长期参考章节不应被整段删除。
`GET /health` 额外返回只读 `operations` 摘要，包含 `readiness`、`readiness_level`、`operator_summary` 值班摘要、非敏感 `warnings`、`warning_summary` 告警等级计数、`risk_domains` 按 deployment/SLO/backup_restore/runbook/runtime 聚合的风险计数、`readiness_checks` 固定清单、部署配置分类与布尔校验、SLO 阈值口径、备份恢复演练状态、runbook/值班响应配置状态、应急响应演练新鲜度、任务队列并发、执行实例 stale recovery、任务超时与 Chroma probe 状态；不会返回数据库连接串、API key、密钥、联系人或 runbook URL 原文，也不改变既有健康字段。
