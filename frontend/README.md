# InsightAgent Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台。Node.js 使用 24.x。

## 当前状态

- 已封板主线：`provider-tool-expansion`、`ci-release-engineering`、`production-runtime-hardening`（含后续运维体验）、`product-ux-polish`（含下一阶段）、`production-operations-readiness`、`security-hardening`、`release-observability-polish`、`test-maintainability-hardening`、`runtime-dependency-modernization`、`next-major-upgrade-readiness`。
- Workbench、Task Center、任务详情、Trace/Context Inspector、Memory/RAG 调试、设置、审计、usage dashboard 与知识库治理已落地，并继续消费后端统一 preview/output/result-summary、trace/export 字段。
- 最近封板：`agent-core-alignment` 的本地实现与契约验证已封板：有界对话上下文、工具反馈决策、RAG 正文/来源证据、Trace 关系与知识文件导入均完成。可进入后续维护或下一条按实际需求选定的主线；真实模型效果验收仍属于外部待验项。
- 当前阶段：[Agent 核心对齐](../docs/agent-core-alignment.md)本地实现/契约已封板；后续按实际使用问题维护，真实模型质量与目标部署验收待资源具备。
- A2 [试点镜像与部署入口](../docs/pilot-deployment-preflight.md)已准备：84 个后端依赖版本锁定、非 root 默认 embedding 构建缓存通过禁网验证；新增生产 `compose.pilot.yml`、低敏预检/操作入口与健康启动顺序。隔离 mock 下重建全部容器后，登录、会话、任务/Trace 与 Chroma 知识保留；目标部署、TLS、真实模型与升级回滚仍待实测。
- A3 本地恢复基础：Compose 的 Chroma 数据卷已对齐镜像 `/data` 路径，隔离快照恢复后 PostgreSQL/Chroma fixture 均读回；前端登录、任务/Trace 与知识库的目标环境恢复验收仍待部署环境，详见[操作记录](../docs/local-stack-backup-restore.md)。
- A4 [后台 RAG 导入](../docs/rag-background-ingest.md)的持久化/分批进度与[完整任务分支重跑](../docs/task-reruns.md)已完成本地闭环；[任务内工具并发](../docs/task-tool-parallel.md)支持内建检索/计算有界并发；[工具依赖与结果引用](../docs/tool-dependencies.md)支持显式 DAG、重复工具、拓扑波次与公开预览标量绑定；[HTTP 读取并发](../docs/http-read-parallel.md)支持明确声明只读的固定 GET、配置冻结和生命周期协调。[实验性步骤恢复](../docs/task-checkpoints.md)已实现内建顺序计划的独立分支、成功前缀复用与当前设置复核。OpenAPI 为 51 操作 / 88 组件；写入工具并行及 HTTP/DAG checkpoint 明确延期，目标运行与用户验收待完成。
- 非阻塞维护候选：ESLint 10 正式采用；2026-09-30 核对 `eslint-config-next` 内的 `eslint-plugin-react@7.37.5`、`eslint-plugin-import@2.32.0`、`eslint-plugin-jsx-a11y@6.10.2` peer 范围均排除 ESLint 10。预检的 1 个动作概括这组约束；继续精确锁定 ESLint `9.39.5`，不使用 `--force` 或 peer override。
- `app/globals.css` 已拆为 `app/styles/` 主题模块；前端源码体积边界已纳入 node 测试，生成锁文件不作为拆分对象。

## 当前验证基线

- 2026-10-08 full release gate **10/10 PASS**，来源 `/tmp/insightagent-core-scenarios-release.md` 与 `.json`；后端 full slice **2148/2148**（上下文/知识证据新增 13 个）、module boundary **9/9**；前端 node **200/200**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双构建通过。
- 本轮核心场景 PostgreSQL/Chroma **9/9**（含实际知识写入/检索、上下文隔离/排队边界、两条条件分支与来源导出）；反馈回归 **6/6**、步骤恢复回归 **9/9**。来源 `/tmp/insightagent-core-scenarios-postgres.log`、`/tmp/insightagent-context-feedback-regression.log`、`/tmp/insightagent-context-checkpoint-regression.log`；业务模型仅本地替身。
- 已验证前端基线：知识导入 Chromium **7/7**、1440px/390px 布局复核 **2/2**，来源 `/tmp/insightagent-knowledge-import-e2e.log`、`/tmp/insightagent-knowledge-import-layout.log`；Trace 浏览器 **2/2**，来源 `/tmp/insightagent-trace-flow-e2e.log`。本轮无前端实现变更，未将历史浏览器结果当作重新验证。
- 历史 service-backed 基线：完整 Chromium **77 passed / 1 skipped**、完整重跑 PostgreSQL **11/11**、内建并发 **6/6**、HTTP **7/7**、DAG **7/7**、RAG **21/21** 与 400 切块实写，均保留原验证范围。
- 既有镜像/Compose 与备份恢复证据见试点部署和恢复文档；这些镜像不包含当前核心对齐改动，不代表目标部署验收。
- 用户无真实 key/部署环境；未发起真实模型请求。决策/回答质量、试点 HTTPS/升级回滚、恢复 RPO/RTO 与签收均未验证；本地封板不代表外部验收完成，项目总完成度不估百分比。

## 下一步前端计划

1. `agent-core-alignment` 本地实现/契约已封板；后续按实际使用问题维护，下一条开发主线待需求核对后选定。
2. `project-completion-audit` 保留外部未验证项：有效 key、目标部署/恢复与用户验收待资源具备后继续；不阻止本地核心开发。写入并行及 HTTP/DAG checkpoint 继续延期。
3. ESLint 10 保留为上游兼容后的维护候选，当前不强制覆盖 peer 约束。

## 稳定契约

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

- 后台 RAG 导入为兼容扩展：同键重试复用原任务，按当前知识库轮询提交者的任务，完成后刷新状态与治理列表；仅排队任务可取消，失败时保留输入并提示先复核数据。

- SSE 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- 已配置 CORS 来源可读取后端生成的 `X-Request-ID`，便于把前端失败报告与后端低敏请求日志关联；SSE 业务失败仍以事件/Trace 为准。
- 后端 OpenAPI 指纹基线仅检查结构漂移；前端对 SSE、Trace、export 的实际消费仍以现有 node/e2e 回归和人工兼容性审查为准。
- `trace.step` 与后端 `TraceStep` 同构；`tool_start/tool_end` 与 action 节点通过 `step_id` 对齐。
- Workbench 使用 `trace/delta` 做静默增量刷新，流结束后补拉最终快照。
- result summary、safe output、failure hint 与 diagnostics 使用后端统一语义。
- `trace_semantic` URL 参数兼容支持 `planner/retrieval/calculator/failure`；详情页语义切换与 operator next-action 提示仅使用既有 status、failure hint/source 与 semantic failure stats 做本地展示，状态文字/色调与轮询控制优先使用 `status_normalized`，均不改变任务、trace 或 export payload。
- Workbench Inspector 语义筛选只调整本地 trace 筛选状态：保留时间线/流程图视图，清理旧 search/kind 干扰，不改变 SSE、trace/delta、任务 API 或 export payload。
- Task Center failure source 诊断 chips 与状态筛选只调整前端本地状态；状态、失败摘要和观测筛选统一优先使用 `status_normalized`，显式 `failure_hint/failure_source` 优先于 trace 文本推断，不改变任务列表 API 与 trace/export payload。
- Task Center 与任务详情页 operator next-action 提示只由现有 status、failure hint/source 与 semantic failure stats 本地派生；Audit Logs operator next-action 提示只由现有 event_type、event_detail 与 task_id 本地派生；不新增后端字段，不改变任务/审计 API、SSE、trace 或 export payload。
- Knowledge Governance operator next-action、共享范围说明与清空/删除禁用只由现有 query 状态、`chroma_reachable`、知识库 ID 和用户角色本地派生；Knowledge Governance <-> RAG 往返仅切换、聚焦并展开已有弹窗，不改变 shared RAG 权限或 API shape。
- Runtime Debug RAG 状态加载失败支持原位刷新，缓存状态在刷新失败时继续可见；失败恢复与跨库反馈隔离仅使用现有 query/mutation 状态和 reset，保留输入草稿，不改变 RAG 请求/响应、权限或审计契约。
- Release gate trend 对缺少 `operator_summary` 的旧 artifact 按既有 result、step summary 与失败标签派生低敏兼容摘要；新格式仍执行严格 operator contract，不改变前端运行时契约。
- 后端测试主题分片和规模余量门禁不改变前端 node/e2e 清单、SSE、trace 或 export 契约。
- 后端 `-k` 零匹配诊断只影响测试 CLI 的错误可读性，不改变前端 node/e2e 清单或运行时契约。
- 后端 `--list-tests` 只读取测试发现结果，不执行测试，也不改变前端 node/e2e 清单或运行时契约。
- 后端维护选择器清单只校验测试发现覆盖，不改变前端 node/e2e 清单或运行时契约。
- Release gate 失败摘要稳定性修复不改变前端构建命令、node/e2e 清单或运行时 payload。
- Task Center、Audit Logs 与知识库治理的初始错误、陈旧数据错误与原位重试只调整 TanStack Query/presentation 状态，不改变任务、审计或 RAG API shape；初始失败不再误显示空态，陈旧数据仍可查看。
- SSE close 后失败摘要兜底只在流关闭但本地尚未进入 terminal phase 时补拉任务/trace 并映射低敏 failure hint，不改变 SSE、任务、trace 或 export payload。
- queued/running/cancel/reconnect 与 task recovery 前端语义保持稳定。

## 能力索引

- Workbench：会话、消息、任务中心、Trace/Context Inspector 与 running task recovery。
- 任务回放：任务详情页、Trace 时间线/流程图、Failure 入口、operator next-action 提示、任务和会话 JSON/Markdown 导出。
- 任务详情页支持通过 `trace_semantic` URL 参数直达语义 Trace，并在切换时更新可分享 URL、清理旧筛选；Task Center 与 Audit Logs failure drilldown 可直达 Failure 回放，列表、详情与审计统一 normalized 状态、显式失败诊断、operator next-action 和轮询控制。
- 设置与治理：模型设置、provider/source diagnostics、task queue diagnostics、审计日志、usage dashboard、知识库治理。
- Memory/RAG 调试：会话级 `memory_{session_id}` 调试入口、知识库 `kb_{user_hash}_{knowledge_base_id}` 状态/写入/检索入口。
- 前端不新增 provider 专用显示分支，继续消费后端统一 preview/output/result-summary 与 trace/export 字段。

## 当前已有内容

- 三栏工作台：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试，失败后自动回登录
- Workbench：聊天主视图、任务中心抽屉、任务详情页 `/tasks/[taskId]`
- Inspector：Trace 时间线 / 流程图双视图、Context 概览、同步诊断、当前任务
- 流式链路：SSE 状态、token 追加、trace 实时更新、`trace/delta` 自动静默轮询与结束补拉
- running task 恢复：刷新页面或切回会话时自动接管 `queued/pending/running` 任务流
- 导出：任务与会话 JSON / Markdown 导出
- 模型设置：`mock / remote` 模式切换、校验、保存、错误码友好提示、provider/source diagnostics 与 task queue diagnostics 限额/全局与当前用户计数/可用槽位/压力状态/等待策略说明
- RAG / Memory 调试：运行调试子页展示召回摘要、质量分布、筛选、来源摘要与 distance 解释
- 知识库治理：列表、版本明细展开、文档组摘要、文档组删除、来源采样、shared 权限显隐、清空/删除
- 审计日志：筛选、分页、详情、导出
- usage dashboard：趋势、会话榜、任务榜与来源分布

## 当前运行态重点

- 实时流、持久化 trace 与导出回放当前共用同一套 `TraceStep` 消费主干，前端优先避免派生本地专用语义。
- `tool_end.result_summary`、preview/output key、retrieval follow-up 与 registry diagnostics 已进入工作台主展示链，当前重点是继续跟随后端保持 helper/runtime 语义一致。
- 任务失败线索已进入共享快照语义；Task Center、任务详情、Usage Dashboard 与 Audit Logs 复用同一失败摘要、来源分类、可读错误码、operator next-action 和 Failure 轨迹入口。
- 远端错误/取消 e2e 的并发等待已对齐真实 UI 状态：任务详情 failure 计数等待稳定，trace retry ETA 限定可见 Context 面板，remote cancel 先验证冷却阻塞再等待恢复。
- Usage Dashboard、Audit Logs、Task Center 与任务详情页已统一失败回放入口、Failure 计数与处置提示。
- running task recovery、remote cancel、model settings diagnostics 与知识库治理 shared 权限是当前最容易回归的前端运行态重点。
- 当前前端回归重点仍围绕 workbench 主链、remote errors、settings、usage dashboard 与 common tooling。

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、会话导出入口与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：模型设置、审计、用量统计、知识库治理与当前用户信息入口
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/usage-dashboard-modal.tsx`：用量仪表盘
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx` / `audit-logs-modal-utils.ts`：审计日志筛选、服务端 keyword URL、分页、失败详情可读化、展开与导出
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库治理与导入/检索入口
- `app/components/workbench/knowledge-import-modal.tsx` / `knowledge-import-utils.ts`：UTF-8 文件校验、预览与既有后台导入任务衔接
- `app/components/workbench/runtime-debug-modal.tsx` / `runtime-debug-memory-section.tsx`：RAG 调试编排与按会话重建的 Memory 调试区
- `app/tasks/[taskId]/page.tsx`：任务详情页与任务导出入口
- `app/tasks/[taskId]/task-checkpoint-panel.tsx`：实验性起点选择、成功前缀说明、失败同键重试与独立会话接管
- `app/tasks/[taskId]/task-rerun-panel.tsx`：独立任务分支、输入编辑、同键重试、来源分页与 Workbench 会话接管
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/stores/chat-stream-store-utils.ts`：tool_end / tool meta 合并、preview/output/result-summary 归一化
- `app/components/workbench/utils.ts`：trace display、tool result preview、follow-up 展示与搜索辅助
- `app/components/workbench/model-settings-modal-utils.ts`：settings 预览、provider/source/tool registry diagnostics 与 task queue diagnostics 说明
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期
- `lib/types/trace.ts`：前端 TraceStep 类型

## SSE 消费与契约对齐

当前前端按以下事件消费：

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

- `trace` 事件中的 `step` 与后端 REST `TraceStep` 同构。
- `tool_start/tool_end` 会先驱动 action 节点状态，再由 `trace` 事件补齐持久化快照。
- Workbench 会定时静默拉取 `trace/delta`，失败时退避重试，并在流结束后自动补拉一次。
- 同步健康度会在 Inspector Context 区域展示，便于定位网络抖动或增量拉取异常。

## Memory（会话级）

- collection 规则：`memory_{session_id}`
- 状态读取：`GET /api/sessions/{session_id}/memory/status`
- 写入调试：`POST /api/sessions/{session_id}/memory/add`
- 检索调试：`POST /api/sessions/{session_id}/memory/query`

## RAG（知识库）

- 普通入口：设置 → 知识库 → 导入知识；支持 UTF-8 `.txt` / `.md` / `.markdown`。同名文件复用文档 ID，内容变化保留新旧版本；不同目录的同名文件应先重命名。导入完成后复核版本，知识库行的“检索测试”自动带入该库。
- 状态：`GET /api/rag/status?knowledge_base_id=...`
- 写入：`POST /api/rag/ingest`
- 后台写入：`POST /api/rag/ingest-jobs`；状态列表/详情与排队取消使用对应 `ingest-jobs` 路由。运行调试窗口关闭后停止轮询，重新打开从服务端恢复状态与批次确认进度；失败时显示保留进度及复核入口，详见[后台导入说明](../docs/rag-background-ingest.md)。
- 检索：`POST /api/rag/query`
- 默认知识库 ID：`default`
- 实际 collection：`kb_{user_hash}_{knowledge_base_id}`

## PostgreSQL / Memory / RAG 怎么看（前端通俗版）

- `PostgreSQL`：完整历史，支撑会话、消息、任务、trace、usage、导出。
- `Memory`：当前会话便签，适合放“本次对话临时约束和结论”。
- `RAG`：外部知识库，适合放手册、FAQ、产品文档。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

说明：

- `npm run dev` / `npm run start` 固定监听 `127.0.0.1:3001`
- 默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端；未设置时使用 `http://127.0.0.1:8000`

前端 e2e 常用命令：

```bash
npm run test:e2e
npm run test:e2e:smoke:matrix
```

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

详细 e2e、服务启动、端口和提交权限以 [`docs/development-runbook.md`](../docs/development-runbook.md) 为准。

## 当前约束

- 当前前端优先保持与后端 SSE / trace / export 契约稳定对齐，不主动发散出新的本地语义分支。
- registry-governance 已封板，settings/preflight/runtime trace/display/export 一致性保持稳定，不优先继续扩张旧 payload fallback。
- 文档收敛只处理当前状态、验证基线、下一步计划/候选主线、稳定契约和高信号摘要；长期参考章节不应被整段删除。
