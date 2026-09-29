# Project Completion Audit

## 口径与状态

- 日期：2026-09-29。当前主线是 `project-completion-audit`，进度 **1/3（约 33%）**：仓库静态盘点完成、真实提供方证据核对已开始；当前成功调用、目标环境验证和范围决策尚未完成。这不是项目总完成百分比。
- 审计目标：回答“InsightAgent 距离真正收尾还有什么”，不以已封板主线数量推算整体完成度。先以“可交给外部试点用户使用”为临时验收目标；正式生产运行需要额外的部署、恢复和运营证据。
- 证据等级：`已验证` 表示有本地测试或代码证据；`待实证` 表示实现或配置存在，但缺少目标环境的实际运行记录；`待定范围` 表示原始计划有要求，但是否仍纳入收尾须明确决策。
- 本轮没有重新运行 release gate/e2e，也没有读取生产环境或输出真实供应商密钥。四份活跃文档中的测试数字均是上一主线的封板基线，不是本轮结果。
- 用户确认：GLM 测试账号已在项目中测试过，目前没有试点部署环境。本机 `backend/.env` 当前为 `mock` 且未配置 remote base URL/API key；用户级加密设置已按下文只读核验。用户报告与本轮可复核证据分别记录。

## 本轮真实提供方证据

- 经用户同意进行可能计费的少量调用。只读核对本机数据库中的唯一“智谱”用户设置：已加密保存密钥，模型 `glm-5.1`，API 主机 `open.bigmodel.cn`；未输出用户 ID、密钥、提示词或回答正文。
- 该设置所属账号有 10 个历史完成任务具 `usage_source=provider`，Trace 标记模型 `glm-5.1`；时间范围 2026-04-20 至 2026-06-05，共 4,653 prompt tokens、7,882 completion tokens。应用对这批任务的累计成本**估算**为 USD 0.020417，不是供应商账单。
- 这 10 个任务的 Trace 包含 13 个 `tool_call` 步骤、2 个 `rag_retrieval` 步骤。使用当前代码只读构建其中一条历史任务的 JSON v1.0 与 Markdown 导出成功：任务已完成、5 个 Trace 步骤、3 个 RAG hits、2 条消息；没有请求外部 API。
- 本轮通过项目 `OpenAICompatibleLLMProvider.generate()` 向已保存的 GLM 设置发起**一次**极短非流式真实请求，返回 HTTP 429 / `remote_provider_rate_limited`，未取得回答或本轮 provider usage。没有重试，也无法从状态码单独判定是额度、并发还是其他限流原因；本轮实际账单金额未知。
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
| A1 | 试点前必须 | 历史 10 条 GLM provider-usage 成功任务证明模型、工具与 RAG 路径曾工作；一条历史任务的当前 JSON/Markdown 导出构建通过。本轮最小实时请求返回 HTTP 429；连续对话、前端交互质量、当前成功用量与失败恢复仍未验收。 | 先核对测试账号额度/限流状态；恢复后只补缺失的当前成功流式链路、前端交互与质量/成本记录，不重复执行已被历史证据充分证明的静态契约检查。密钥不提交仓库。 |
| A2 | 试点前必须 | `compose.full.yml` 使用源码挂载、`uvicorn --reload`、`npm run dev`、启动时安装依赖、默认 PostgreSQL 凭据及 `chroma:latest`；`.github/workflows/` 只有 release gate 和两条 e2e 工作流。它是本地开发栈，不是可直接照搬的生产部署证明。用户确认尚无试点部署环境。 | 明确试点目标环境；用固定版本、非默认凭据、生产构建、HTTPS/访问边界完成一次部署、升级及回滚演练，并保存非敏感记录。在环境具备前保持 `未验证`。 |
| A3 | 生产前必须，试点需决定风险接受 | `backend/app/services/operations_health.py` 根据配置与演练时间戳报告备份/应急状态；本轮未在仓库找到 PostgreSQL+Chroma 的可执行备份/恢复流程或真实恢复记录。 | 对目标环境实际备份并从备份恢复 PostgreSQL 与 Chroma；验证会话、Trace、知识库和登录，记录 RPO/RTO、责任人及失败回退。 |
| A4 | 范围决策 | 原始完整版阶段 6–9 还写有单步重跑/分支重跑、任务内并行工具、异步 RAG ingest、基础运行指标及破坏性 API 变更记录。当前 `tasks.py` 路由清单没有专用单步重跑端点，`rag.py` 的 ingest 是同步调用；本轮未找到任务内 `asyncio.gather`、指标端点或 changelog。静态搜索不能单独证明不存在等价实现。 | 逐项核验真实实现和产品价值，标记为“完成 / 试点必须 / 明确延期 / 取消”；留下决策理由，不让历史计划自动变成无限待办。 |
| A5 | 试点前必须 | 现有 e2e 证明预设路径可自动跑通，但本轮没有目标用户、真实任务样本、可用性反馈或签收标准的证据。full Chromium 的 1 个 skip 是低并发队列专用场景，另有独立 queue e2e 路径，不直接视为产品缺陷。 | 选 2–3 个真实任务和目标用户，完成端到端走查；记录完成率、失败点、可理解性和签收结论。 |
| A6 | 非收尾阻塞 | `eslint-10-adoption` 仍受 `eslint-plugin-react` 官方 peer 兼容性约束，现用 ESLint 9 精确锁定，预检 `ready_with_actions` 且 0 blocker。 | 官方兼容版本发布后再走红测和完整门禁；不以该升级作为试点完成条件。 |

## 下一阶段

1. **真实环境证据（第 2/3 阶段）**：已有 GLM 历史成功证据；先核对 429 的账号额度/限流状态，恢复后做一次受控的当前成功流式/前端验收，不在仓库存密钥。A2/A3 等待明确试点环境，环境不可用时标 `未验证`，不借用旧门禁结果。
2. **范围与签收（第 3/3 阶段）**：逐项裁决 A4，并完成 A5 的用户走查；形成“试点可交付 / 带风险试点 / 暂不可交付”结论及剩余主线。
3. 只有试点目标、范围裁决和 A1/A2/A5 的结果齐备后，才估算项目收尾工作量；生产级完成还必须补 A3。ESLint 10 放在非阻塞维护队列。

## 维护规则

每条发现只接受本轮可核对的证据或明确的范围决策作为关闭依据。变更结论时同步 `README.md`、`backend/README.md`、`frontend/README.md` 与实时计划文件；永远不修改 `data/insightagent.plan.back.md`。
