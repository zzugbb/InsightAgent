# Project Completion Audit

## 口径与状态

- 更新日期：2026-10-06。当前主线是 `project-completion-audit`，进度 **1/3（约 33%）**：仓库静态盘点完成、真实提供方证据核对已开始，本地离线恢复 fixture 与试点镜像隔离联调已通过；当前成功调用、目标环境验证和范围决策尚未完成。这不是项目总完成百分比。
- 审计目标：回答“InsightAgent 距离真正收尾还有什么”，不以已封板主线数量推算整体完成度。先以“可交给外部试点用户使用”为临时验收目标；正式生产运行需要额外的部署、恢复和运营证据。
- 证据等级：`已验证` 表示有本地测试或代码证据；`待实证` 表示实现或配置存在，但缺少目标环境的实际运行记录；`待定范围` 表示原始计划有要求，但是否仍纳入收尾须明确决策。
- 本主线已有隔离恢复 fixture 与试点镜像本机构建证据；当前基线为 full release gate（10/10）、后端 2083/2083、前端 184/184、6 个工具并发 PostgreSQL 场景、11 个任务分支 PostgreSQL 回归及并发开启为 2 的完整 Chromium 74 passed / 1 skipped；既有 RAG 21/21 PostgreSQL/Chroma 基线沿用前轮。当前基线来自本地验证；目标环境与当前真实供应商成功调用仍未验证。
- 用户确认：GLM 测试账号已在项目中测试过，但服务现已到期，解释了本轮无法继续真实调用；目前没有试点部署环境。本机 `backend/.env` 当前为 `mock` 且未配置 remote base URL/API key；用户级加密设置已按下文只读核验。到期原因来自用户确认，HTTP 429 是本轮实际观测。

## 本轮真实提供方证据

- 经用户同意进行可能计费的少量调用。只读核对本机数据库中的唯一“智谱”用户设置：已加密保存密钥，模型 `glm-5.1`，API 主机 `open.bigmodel.cn`；未输出用户 ID、密钥、提示词或回答正文。
- 该设置所属账号有 10 个历史完成任务具 `usage_source=provider`，Trace 标记模型 `glm-5.1`；时间范围 2026-04-20 至 2026-06-05，共 4,653 prompt tokens、7,882 completion tokens。应用对这批任务的累计成本**估算**为 USD 0.020417，不是供应商账单。
- 这 10 个任务的 Trace 包含 13 个 `tool_call` 步骤、2 个 `rag_retrieval` 步骤。使用当前代码只读构建其中一条历史任务的 JSON v1.0 与 Markdown 导出成功：任务已完成、5 个 Trace 步骤、3 个 RAG hits、2 条消息；没有请求外部 API。
- 本轮通过项目 `OpenAICompatibleLLMProvider.generate()` 向已保存的 GLM 设置发起**一次**极短非流式真实请求，返回 HTTP 429 / `remote_provider_rate_limited`，未取得回答或本轮 provider usage。没有重试；用户随后确认 GLM 服务已到期，本轮实际账单金额未知。
- PostgreSQL/Chroma 仅为只读核验临时启动，已停止；未删除数据卷。历史成功不能替代当前实时成功、完整前端 UX 或目标环境验收。

## 已有基础

| 领域 | 现有证据 | 判定 |
| --- | --- | --- |
| 主链路与契约 | `README.md` 记录 Chat、任务、SSE、Trace、Memory/RAG、鉴权、导出和治理；上一主线的后端 full slice 2020/2020、前端 node 184/184、full Chromium 64 passed / 1 skipped，release gate 10/10 PASS。 | 本地/CI 基线充分；不等于外部用户验收。 |
| 远端提供方 | `backend/app/providers/` 有 remote provider；`frontend/e2e/workbench-remote-errors.spec.ts` 用本地 mock remote server 覆盖错误、限流、流中断与取消；本轮查到 10 条历史 GLM provider-usage 成功任务及工具/RAG Trace。 | 历史 GLM 主链与一条任务导出有可复核证据；当前实时请求为 429，尚未完成当下成功验收。 |
| 运维信号 | `/health.operations` 汇总部署、备份、演练、SLO 与运行态配置；release gate 有低敏 operator summary。 | 健康摘要存在；配置声明不能替代备份、恢复或值班演练记录。 |

## 待收尾问题

| ID | 优先级 | 发现与证据 | 关闭条件 |
| --- | --- | --- | --- |
| A1 | 试点前必须，当前外部阻塞 | 历史 10 条 GLM provider-usage 成功任务证明模型、工具与 RAG 路径曾工作；一条历史任务的当前 JSON/Markdown 导出构建通过。本轮最小实时请求返回 HTTP 429，用户确认 GLM 服务已到期；当前成功流式调用、前端交互质量与失败恢复尚未验收。 | 续用 GLM 或换有效的兼容账号后，只补缺失的当前成功流式链路、前端交互与质量/成本记录；到期期间保持 `未验证`，不反复请求。密钥不提交仓库。 |
| A2 | 试点前必须 | `compose.full.yml` 仍是本地开发栈。[试点镜像配方、配置预检与演练记录](pilot-deployment-preflight.md)已准备；后端试点镜像的 84 个依赖版本已锁定并在本机 ARM64 重建核验。隔离联调以生产模式验证 PostgreSQL 注册/会话写读、Chroma 探测、CORS 来源边界、前端 HTML/CSS 和浏览器实际请求的 API 地址；错误地址负向检查失败，临时资源已清理。预检核验 HTTPS/CORS、凭据及六个镜像摘要；尚无目标环境、TLS 或升级回滚实证。 | 明确试点目标环境；用固定版本、非默认凭据、生产构建、HTTPS/访问边界完成一次部署、升级及回滚演练，并保存非敏感记录。在环境具备前保持 `未验证`。 |
| A3 | 生产前必须，试点需决定风险接受 | 已新增[本地离线备份/隔离恢复流程](local-stack-backup-restore.md)，用独立 fixture 验证 PostgreSQL 行与 Chroma 向量恢复；同时发现并修正旧 Compose 的 Chroma 卷挂载路径错误。目标环境尚无真实恢复记录。 | 对目标环境实际备份并从备份恢复 PostgreSQL 与 Chroma；验证会话、Trace、知识库和登录，记录 RPO/RTO、责任人及失败回退。 |
| A4 | 范围决策与实现 | [后台 RAG 导入](rag-background-ingest.md)已具备持久化、幂等、取消、权限、多 worker 与恢复；分批写入、确认进度、每批角色复核及 5000 切块预算已验证，40 文档 / 400 切块隔离实写通过。[完整任务分支重跑](task-reruns.md)已支持输入编辑、独立会话、幂等与来源分页；[任务内工具并发](task-tool-parallel.md)已支持内建独立检索/计算、串行回退、顺序 Trace 合并及取消/超时协调；单步恢复、通用依赖调度与外部工具并行仍待实现。请求与 LLM 尝试低敏观测已落地；OpenAPI 50 操作 / 86 组件进入门禁。 | 对剩余能力标记“试点必须 / 明确延期 / 取消”；真实资料与目标环境仍需验证规模、等待体验和观测/调用方流程，fixture 耗时不等于吞吐承诺。 |
| A5 | 试点前必须 | 现有 e2e 证明预设路径可自动跑通，但本轮没有目标用户、真实任务样本、可用性反馈或签收标准的证据。full Chromium 的 1 个 skip 是低并发队列专用场景，另有独立 queue e2e 路径，不直接视为产品缺陷。 | 选 2–3 个真实任务和目标用户，完成端到端走查；记录完成率、失败点、可理解性和签收结论。 |
| A6 | 非收尾阻塞 | 2026-09-30 核对锁文件，`eslint-config-next` 内 React/import/jsx-a11y 三个插件的 peer 范围均排除 ESLint 10；React 插件官方兼容修复尚未发布。现用 ESLint 9 精确锁定，本轮 lint 0 error / 2 warning；预检的 1 个外部兼容动作概括这组约束。 | 官方兼容版本发布并确认三个插件均支持 ESLint 10 后，再走依赖红测和完整门禁；不以该升级作为试点完成条件。 |

## 原始范围裁决建议

以下是面向**小规模外部试点**的建议，尚未得到产品范围确认，不能当作已取消原始计划：

| 原始完整版能力 | 当前核对 | 建议 |
| --- | --- | --- |
| 单步重新执行/分支重跑 | `/api/tasks/{task_id}/reruns` 新增完整任务分支创建与来源查询；本人已终结任务可编辑输入，在独立会话中通过既有 stream 执行，使用当前设置。单步 checkpoint 恢复尚未实现，前端 Replay 仍为历史查看。 | 完整分支已完成本地闭环，目标运行待实证；单步恢复是否纳入试点仍需范围决策。 |
| 任务内并行工具 | `task_tool_execution.py` / `task_tool_parallel.py` 已支持相邻内建独立检索/计算，默认 TASK_TOOL_MAX_CONCURRENT=1，开启为 2 可重叠执行；Trace/最终观察按计划顺序合并，进程最多 8 个读取线程，取消/超时丢弃迟到结果。规划、自定义/HTTP 工具与依赖提示项为串行屏障。 | 限定并发已完成本地闭环，目标延迟仍待实证；通用 DAG、跨工具结果绑定和外部工具并行需单独范围决策与实现。 |
| 异步 RAG ingest | `/api/rag/ingest-jobs` 创建/列表/详情/排队取消、PostgreSQL 队列与监管 worker 实现本地闭环；新增分批写入、持久化确认进度与 5000 切块预算，原同步接口继续可用；真实 Chroma 400 切块写入、版本元数据与部分失败已验证。 | 实现已落地；真实资料吞吐、等待体验和目标环境验收仍待实证。超过新展开上限的调用方须分拆请求或降低 overlap。 |
| 请求观测与 LLM 调用指标 | `request_observability.py` 记录服务端 request ID、路由模板、状态码与完整响应耗时；远端提供方另记每次实际 HTTP 尝试的模式、结果、状态族、耗时及 usage 是否可用，可用 `summarize_provider_attempts.py` 离线统计。兼容性回退会计两次尝试；不等于逻辑任务数、账单调用数或 token 用量。`/health.operations` 仍提供运行态摘要；尚无目标环境指标采集与告警。SSE 建连后失败可能仍是 HTTP 200，需结合 SSE/Trace。 | 试点可采集低敏日志并核对重试/回退口径；目标环境确认采集、留存和告警后再认定指标完成。 |
| OpenAPI 与破坏性变更记录 | FastAPI 提供运行时 `/openapi.json`；`backend/api_surface_baseline.json` 记录 API 0.1.0 操作与组件指纹，后端 full slice 检查漂移，`docs/api-changelog.md` 记录初始基线及更新流程。指纹差异不自动判定破坏性。 | 每次对外契约变更人工判断兼容性并更新记录；若有外部 API 使用者，破坏性变更需迁移路径与通知计划。目标环境和调用方流程待验证。 |

## 下一阶段

2026-09-30 A3 本地开发进展：当前 Chroma 镜像将数据写到 `/data`，旧 Compose 挂载 `/chroma/chroma` 导致第一轮演练快照为空；两个 Compose 文件已改挂 `/data`。第二轮隔离演练在停止服务后生成双卷快照，恢复到全新项目并读回 PostgreSQL 测试行与 Chroma 测试文档。旧容器如仍在，重建前须先保存其 `/data`；本地 fixture 不计入目标环境恢复演练，A3 保持开放。

2026-10-06 A4 当前验证：工具并发 15 个静态专项、6 个 PostgreSQL 场景及既有任务分支 11/11 PostgreSQL 回归通过；full release gate 10/10、后端 2083/2083、module boundary 9/9、前端 184/184 与双构建通过。临时 PostgreSQL/Chroma mock 栈开启 TASK_TOOL_MAX_CONCURRENT=2，完整 Chromium 74 passed / 1 skipped，临时资源已清理。既有 RAG 21/21 PostgreSQL/Chroma、40 文档 / 400 切块实写沿用前轮基线，不是本轮目标吞吐验收。OpenAPI 保持 50 操作 / 86 组件；并发复用 SSE 事件、允许跨 step 交错，Trace.meta 的分组字段为兼容扩展。任务分支使用当前设置，导入失败仍不自动重放；单步恢复、通用依赖调度、外部工具并行、产品范围、目标运行和用户签收未完成，A4 保持开放。

2026-10-06 A2 本地验证：只读配置预检覆盖六个镜像摘要；后端试点镜像在固定基础镜像上以 84 个版本约束重建，构建期 `pip check` 与最终 `pip freeze` 比对通过；镜像内应用导入及 Chroma 1.5.7 通过。[隔离联调](pilot-deployment-preflight.md)复验生产模式后端的 PostgreSQL 注册/会话写读、Chroma 探测、前端 HTML/CSS 和浏览器实际 API 地址，临时资源已清理。目标环境部署、TLS/访问边界和升级回滚仍未实测，A2 保持开放。

1. **真实环境证据（第 2/3 阶段）**：已有 GLM 历史成功证据；服务到期期间暂停真实请求，续用或换有效兼容账号后做一次受控的当前成功流式/前端验收，不在仓库存密钥。A2/A3 等待明确试点环境，环境不可用时标 `未验证`，不借用旧门禁结果。
2. **范围与签收（第 3/3 阶段）**：逐项裁决 A4，并完成 A5 的用户走查；形成“试点可交付 / 带风险试点 / 暂不可交付”结论及剩余主线。
3. 只有试点目标、范围裁决和 A1/A2/A5 的结果齐备后，才估算项目收尾工作量；生产级完成还必须补 A3。ESLint 10 放在非阻塞维护队列。

## 维护规则

每条发现只接受本轮可核对的证据或明确的范围决策作为关闭依据。变更结论时同步 `README.md`、`backend/README.md`、`frontend/README.md` 与实时计划文件；永远不修改 `data/insightagent.plan.back.md`。
