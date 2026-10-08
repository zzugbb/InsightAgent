# InsightAgent Backend

FastAPI 后端，提供 Auth、会话/任务、SSE、Trace、PostgreSQL、Memory、RAG、导出、usage、审计与 tool runtime 能力；默认演示路径为 canonical `mock`，也支持 OpenAI-compatible `remote`。

## 当前状态

- 已封板主线：`provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`（含后续运维体验）、`product-ux-polish`（含下一阶段）、`production-operations-readiness`、`security-hardening`、`release-observability-polish`、`test-maintainability-hardening`、`runtime-dependency-modernization`、`next-major-upgrade-readiness`。
- `/health.operations` 保持非敏感运维摘要：readiness、readiness_level、operator_summary、warnings、warning_summary、risk_domains、readiness_checks、部署配置、SLO、备份恢复、runbook/值班、演练新鲜度、队列、执行实例、超时与 Chroma probe。
- 最近封板：`agent-core-alignment` 的本地实现与契约验证已封板：有界对话上下文、工具反馈决策、RAG 正文/来源证据、Trace 关系与知识文件导入均完成。可进入后续维护或下一条按实际需求选定的主线；真实模型效果验收仍属于外部待验项。
- 当前阶段：[Agent 核心对齐](../docs/agent-core-alignment.md)本地实现/契约已封板；后续按实际使用问题维护，真实模型质量与目标部署验收待资源具备。
- A2 [试点镜像与部署入口](../docs/pilot-deployment-preflight.md)已准备：84 个后端依赖版本锁定、非 root 默认 embedding 构建缓存通过禁网验证；新增生产 `compose.pilot.yml`、低敏预检/操作入口与健康启动顺序。隔离 mock 下重建全部容器后，登录、会话、任务/Trace 与 Chroma 知识保留；目标部署、TLS、真实模型与升级回滚仍待实测。
- A3 本地恢复基础已落地：两份 Compose 的 Chroma 卷改挂当前镜像实际持久路径 `/data`；独立 fixture 经离线快照恢复后，PostgreSQL 行与 Chroma 向量均读回。旧容器重建前须保存原 `/data`；目标环境恢复待验证。
- A4 [后台 RAG 导入](../docs/rag-background-ingest.md)的持久化/分批进度与[完整任务分支重跑](../docs/task-reruns.md)已完成本地闭环；[任务内工具并发](../docs/task-tool-parallel.md)支持内建检索/计算有界并发；[工具依赖与结果引用](../docs/tool-dependencies.md)支持显式 DAG、重复工具、拓扑波次与公开预览标量绑定；[HTTP 读取并发](../docs/http-read-parallel.md)支持明确声明只读的固定 GET、配置冻结和生命周期协调。[实验性步骤恢复](../docs/task-checkpoints.md)已实现内建顺序计划的独立分支、成功前缀复用与当前设置复核。OpenAPI 为 51 操作 / 88 组件；写入工具并行及 HTTP/DAG checkpoint 明确延期，目标运行与用户验收待完成。
- 非阻塞维护候选：ESLint 10 正式采用仍受前端锁文件中 React/import/jsx-a11y 三个插件的 peer 范围约束；保持 ESLint 9 精确 pin，预检的 1 个动作概括这组外部兼容约束。
- `backend/app` 与 `backend/scripts` Python 源码均低于 3000 行；后续新增实现继续优先落到主题模块，保留兼容 facade。

## 当前验证基线

- 2026-10-08 输入交互维护：前端 release gate **4/4 PASS**（node **200/200**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双构建），来源 `/tmp/insightagent-composer-release.md` / `.json`；输入法/键盘浏览器专项 **6/6**（Chromium/Firefox/WebKit，各 1440px/390px），来源 `/tmp/insightagent-composer-keyboard-e2e.log`。组字事件由 fixture 模拟，未代替操作系统真实输入法人工验收。
- 2026-10-08 full release gate **10/10 PASS**，来源 `/tmp/insightagent-core-scenarios-release.md` 与 `.json`；后端 full slice **2148/2148**（上下文/知识证据新增 13 个）、module boundary **9/9**；前端 node **200/200**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双构建通过。
- 保留的后端核心场景基线：PostgreSQL/Chroma **9/9**（含实际知识写入/检索、上下文隔离/排队边界、两条条件分支与来源导出）；反馈回归 **6/6**、步骤恢复回归 **9/9**。来源 `/tmp/insightagent-core-scenarios-postgres.log`、`/tmp/insightagent-context-feedback-regression.log`、`/tmp/insightagent-context-checkpoint-regression.log`；业务模型仅本地替身。
- 已验证前端基线：知识导入 Chromium **7/7**、1440px/390px 布局复核 **2/2**，来源 `/tmp/insightagent-knowledge-import-e2e.log`、`/tmp/insightagent-knowledge-import-layout.log`；Trace 浏览器 **2/2**，来源 `/tmp/insightagent-trace-flow-e2e.log`。本轮仅修改输入交互；这些知识导入/Trace 浏览器结果未重跑。
- 历史 service-backed 基线：完整 Chromium **77 passed / 1 skipped**、完整重跑 PostgreSQL **11/11**、内建并发 **6/6**、HTTP **7/7**、DAG **7/7**、RAG **21/21** 与 400 切块实写，均保留原验证范围。
- 既有镜像/Compose 与备份恢复证据见试点部署和恢复文档；这些镜像不包含当前核心对齐改动，不代表目标部署验收。
- 用户无真实 key/部署环境；未发起真实模型请求。决策/回答质量、试点 HTTPS/升级回滚、恢复 RPO/RTO 与签收均未验证；本地封板不代表外部验收完成，项目总完成度不估百分比。

## 下一步后端计划

1. `agent-core-alignment` 本地实现/契约已封板；后续按实际使用问题维护，下一条开发主线待需求核对后选定。
2. `project-completion-audit` 保留外部未验证项：有效 key、目标部署/恢复与用户验收待资源具备后继续；不阻止本地核心开发。写入并行及 HTTP/DAG checkpoint 继续延期。
3. ESLint 10 保留为上游兼容后的维护候选，当前不强制覆盖 peer 约束。

## 稳定契约

- 聊天输入在 composition 生命周期、原生 isComposing 或兼容 keyCode=229 时将 Enter 留给输入法；正常 Enter 发送、Shift+Enter 换行与发送禁用规则保持一致，不改变后端请求或 SSE/Trace 契约。
- 非 canonical mock 的普通任务在启动时读取本任务创建前已完成的同用户/同会话问答；最多 6 轮、单消息 4,000 字符、序列化历史 16,000 字符。首轮规划、后续决策与最终回答使用同一快照；工具执行/规则回退保留当前原始输入。Trace 仅追加上下文数量/截断摘要；mock 演示与 checkpoint 独立分支保持原行为。
- 模型额外接收已脱敏 RAG Trace 片段/来源/文档版本，最多 6 片段、每片段 1,200 字符、序列化证据 8,000 字符，标注为不可信数据。计数型工具 Observation、既有 SSE/Trace/导出形状兼容；模型引用质量待真实提供方验证。

- 知识库提供 UTF-8 TXT/Markdown 文件预览与后台导入（每次 1–20 文件，单文件 256 KB / 64,000 字符，总大小 512 KB）；文件名作为来源和文档 ID，同名文件归为同一文档并保留内容版本。提交中和结果不确定时冻结输入，重试复用原载荷/幂等键；明确放弃结果后可返回编辑。复核自动定位版本，检索测试携带目标库；复用既有 API 与共享库管理员权限。

- 反馈决策默认最多 3 轮（AGENT_MAX_ROUNDS=1 保持单轮），安全 Observation 驱动后续行动；多轮任务不生成单轮 checkpoint。Trace 记录轮次/决策来源并汇总所有规划用量；流程图虚线为记录顺序、实线为依赖/决策来源，详情不截断。

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
