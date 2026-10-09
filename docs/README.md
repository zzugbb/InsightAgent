# 文档导航

按用途阅读：首次使用从项目 README 开始，开发时查模块与契约，运行时查配置与手册，验收时查证据与模板。

## 使用与开发

| 文档 | 用途 |
| --- | --- |
| [项目 README](../README.md) | 定位、能力、工作流、技术栈与快速开始 |
| [后端 README](../backend/README.md) / [前端 README](../frontend/README.md) | 模块运行、接口范围、实现入口与交互边界 |
| [架构](architecture.md) | 执行链、三类存储、embedding 位置与设计取舍 |
| [配置](configuration.md) | 配置继承、用户 Key、前端地址、网络、备份与轮换 |
| [运行时契约](runtime-contracts.md) | SSE / Trace / 导出、终态、证据与专题入口 |
| [贡献指南](../CONTRIBUTING.md) / [安全政策](../SECURITY.md) | 变更流程、披露方式与实际安全边界 |
| [开发运行手册](development-runbook.md) | 测试、服务、Docker、e2e、权限与提交命令 |
| [API 变更记录](api-changelog.md) | OpenAPI 指纹更新与兼容性裁决 |

## 技术专题

| 主题 | 文档 |
| --- | --- |
| 上下文与工具反馈 | [Agent 核心](agent-core-alignment.md) |
| 图与执行 | [工具依赖](tool-dependencies.md)、[任务内并发](task-tool-parallel.md)、[HTTP 只读并发](http-read-parallel.md) |
| 任务与恢复 | [成功事务](task-completion.md)、[完整分支重跑](task-reruns.md)、[实验性步骤恢复](task-checkpoints.md) |
| 回答与用量 | [流结束](provider-stream-completion.md)、[回答完整性](answer-completion.md)、[用量口径](usage-accounting.md) |
| 文档与检索 | [RAG 后台导入](rag-background-ingest.md) |

## 运行与验收

| 文档 | 当前范围 |
| --- | --- |
| [验证基线](validation-baseline.md) | 最新本地检查与沿用基线；替身/真实模型/CI 分开 |
| [收尾审计](project-completion-audit.md) | 本地封板、原始范围裁决和外部待验收项 |
| [真实模型验收](real-model-acceptance.md) | GLM 小样本、已知回退、用量与证据范围 |
| [五项专项检查](post-seal-usability-audit.md) | mock、仓库、登录、布局、ID 及后续配置/文档维护 |
| [本机验收清单](local-acceptance-checklist.md) | 统一入口、依赖、可选真实调用与阶段口径 |
| [业务 RAG 验收](business-rag-acceptance.md) | 独立知识库与低敏自动报告；真实资料待提供 |
| [目标任务签收模板](target-task-acceptance.md) | 2–3 个任务、用户反馈与证据导出；尚无签收 |
| [部署预检](pilot-deployment-preflight.md) | 镜像配方、仓库外配置、单机试点入口 |
| [历史镜像证据](pilot-image-evidence.md) | 各候选源码、摘要、联调与验证范围；不是当前部署承诺 |
| [备份恢复](local-stack-backup-restore.md) | 开发栈离线快照与全新项目恢复，旧 Chroma 数据保护 |
| [目标环境演练](pilot-environment-drill.md) | HTTPS、升级回滚、RPO/RTO 模板；目标环境未验收 |

## 文档保留与维护规则

- 三个 README 各自负责项目、后端和前端；稳定契约保留摘要并链接专题，避免复制所有验收流水账。
- 专题文档保留接口、边界、实现入口和可运行命令；最新验证集中在验证基线，历史验收仅在有不可替代来源/范围时保留。
- 两份 2026-05 tool-runtime-productionization 旧 spec / handoff 已删除，重复 wrapper 迁移日志和旧计数从活跃文档退出；有效模块化决策保留在架构中，历史原文仍可从 Git 查询。
- AGENTS 指令、许可证、测试 fixture、API 基线与锁文件保留；它们不是过期过程文档。临时日志和截图不纳入仓库。
- 本机原始完整版计划 `data/insightagent.plan.back.md` 永远只读，原目标不等于当前已实现承诺；当前进度由 tracked 实时计划 `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 和收尾审计维护。
- 每次开发同步三个 README 与实时计划；只收敛进度块，不删除仍有效的长期技术参考。部署/真实业务/用户验收延期不写成已通过。

本轮文档组织参考 [Dify README](https://github.com/langgenius/dify/blob/main/README.md)、[Open WebUI README](https://github.com/open-webui/open-webui/blob/main/README.md) 与 [LangGraph README](https://github.com/langchain-ai/langgraph/blob/main/README.md) 的项目介绍、快速使用、技术文档和贡献入口分工；项目能力、实现和许可证以本仓库为准。
