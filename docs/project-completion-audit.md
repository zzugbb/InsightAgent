# Project Completion Audit

## 口径与状态

- 日期：2026-09-29。当前主线是 `project-completion-audit`，进度 **1/3（约 33%）**：仓库静态盘点完成；真实环境验证和范围决策尚未完成。这不是项目总完成百分比。
- 审计目标：回答“InsightAgent 距离真正收尾还有什么”，不以已封板主线数量推算整体完成度。先以“可交给外部试点用户使用”为临时验收目标；正式生产运行需要额外的部署、恢复和运营证据。
- 证据等级：`已验证` 表示有本地测试或代码证据；`待实证` 表示实现或配置存在，但缺少目标环境的实际运行记录；`待定范围` 表示原始计划有要求，但是否仍纳入收尾须明确决策。
- 本轮只做静态盘点，没有重新运行 release gate/e2e，也没有读取生产环境或真实供应商密钥。四份活跃文档中的测试数字均是上一主线的封板基线，不是本轮结果。
- 用户确认：GLM 测试账号已在项目中测试过，但本轮尚未获知覆盖路径、结果或成本记录；目前没有试点部署环境。本机 `backend/.env` 当前为 `mock` 且未配置 remote base URL/API key（仅检查配置存在性，未读取或输出密钥），数据库中的用户设置尚未核验。用户报告和本轮可复核证据分别记录。

## 已有基础

| 领域 | 现有证据 | 判定 |
| --- | --- | --- |
| 主链路与契约 | `README.md` 记录 Chat、任务、SSE、Trace、Memory/RAG、鉴权、导出和治理；上一主线的后端 full slice 2020/2020、前端 node 184/184、full Chromium 64 passed / 1 skipped，release gate 10/10 PASS。 | 本地/CI 基线充分；不等于外部用户验收。 |
| 远端提供方 | `backend/app/providers/` 有 remote provider；`frontend/e2e/workbench-remote-errors.spec.ts` 用本地 mock remote server 覆盖错误、限流、流中断与取消；用户报告 GLM 已测试。 | 协议与失败路径有自动化覆盖；GLM 测试范围、效果和成本尚未形成可复核验收记录。 |
| 运维信号 | `/health.operations` 汇总部署、备份、演练、SLO 与运行态配置；release gate 有低敏 operator summary。 | 健康摘要存在；配置声明不能替代备份、恢复或值班演练记录。 |

## 待收尾问题

| ID | 优先级 | 发现与证据 | 关闭条件 |
| --- | --- | --- | --- |
| A1 | 试点前必须 | 原始计划要求 mock 切 remote 后集中联调和效果校准（`data/insightagent.plan.back.md` 的“真实 API 接入时机”）；当前仓库 e2e 使用 mock 配置或本地 mock remote server。用户报告 GLM 已测试，但覆盖范围与结果尚未记录；本机 `backend/.env` 仍是 mock，未检查数据库中的用户设置。不能据此断言真实接入有故障。 | 先确认既有 GLM 测试覆盖范围；对缺口用受控测试账号和额度补验连续对话、工具/RAG、Trace、usage、导出与失败恢复，留下脱敏结果、成本和可接受质量阈值，不提交密钥。 |
| A2 | 试点前必须 | `compose.full.yml` 使用源码挂载、`uvicorn --reload`、`npm run dev`、启动时安装依赖、默认 PostgreSQL 凭据及 `chroma:latest`；`.github/workflows/` 只有 release gate 和两条 e2e 工作流。它是本地开发栈，不是可直接照搬的生产部署证明。用户确认尚无试点部署环境。 | 明确试点目标环境；用固定版本、非默认凭据、生产构建、HTTPS/访问边界完成一次部署、升级及回滚演练，并保存非敏感记录。在环境具备前保持 `未验证`。 |
| A3 | 生产前必须，试点需决定风险接受 | `backend/app/services/operations_health.py` 根据配置与演练时间戳报告备份/应急状态；本轮未在仓库找到 PostgreSQL+Chroma 的可执行备份/恢复流程或真实恢复记录。 | 对目标环境实际备份并从备份恢复 PostgreSQL 与 Chroma；验证会话、Trace、知识库和登录，记录 RPO/RTO、责任人及失败回退。 |
| A4 | 范围决策 | 原始完整版阶段 6–9 还写有单步重跑/分支重跑、任务内并行工具、异步 RAG ingest、基础运行指标及破坏性 API 变更记录。当前 `tasks.py` 路由清单没有专用单步重跑端点，`rag.py` 的 ingest 是同步调用；本轮未找到任务内 `asyncio.gather`、指标端点或 changelog。静态搜索不能单独证明不存在等价实现。 | 逐项核验真实实现和产品价值，标记为“完成 / 试点必须 / 明确延期 / 取消”；留下决策理由，不让历史计划自动变成无限待办。 |
| A5 | 试点前必须 | 现有 e2e 证明预设路径可自动跑通，但本轮没有目标用户、真实任务样本、可用性反馈或签收标准的证据。full Chromium 的 1 个 skip 是低并发队列专用场景，另有独立 queue e2e 路径，不直接视为产品缺陷。 | 选 2–3 个真实任务和目标用户，完成端到端走查；记录完成率、失败点、可理解性和签收结论。 |
| A6 | 非收尾阻塞 | `eslint-10-adoption` 仍受 `eslint-plugin-react` 官方 peer 兼容性约束，现用 ESLint 9 精确锁定，预检 `ready_with_actions` 且 0 blocker。 | 官方兼容版本发布后再走红测和完整门禁；不以该升级作为试点完成条件。 |

## 下一阶段

1. **真实环境证据（第 2/3 阶段）**：已有 GLM 测试经验，先确认其覆盖范围，再用现有或本机安全配置补齐 A1；不在仓库存密钥。A2/A3 等待明确试点环境，环境不可用时标 `未验证`，不借用旧门禁结果。
2. **范围与签收（第 3/3 阶段）**：逐项裁决 A4，并完成 A5 的用户走查；形成“试点可交付 / 带风险试点 / 暂不可交付”结论及剩余主线。
3. 只有试点目标、范围裁决和 A1/A2/A5 的结果齐备后，才估算项目收尾工作量；生产级完成还必须补 A3。ESLint 10 放在非阻塞维护队列。

## 维护规则

每条发现只接受本轮可核对的证据或明确的范围决策作为关闭依据。变更结论时同步 `README.md`、`backend/README.md`、`frontend/README.md` 与实时计划文件；永远不修改 `data/insightagent.plan.back.md`。
