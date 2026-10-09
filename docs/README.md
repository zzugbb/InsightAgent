# 文档

首次使用从[项目 README](../README.md)开始。下面按使用、开发和运行组织，当前状态只维护在[验证基线](validation-baseline.md)。

## 开始使用

| 文档 | 内容 |
| --- | --- |
| [项目概览与快速开始](../README.md) | 项目定位、核心能力、本机运行与第一项任务 |
| [配置](configuration.md) | 用户模型 Key、配置继承、API 地址、网络与密钥轮换 |
| [验收指南](acceptance.md) | 本机检查、业务 RAG、任务签收与证据导出 |

## 开发参考

| 文档 | 内容 |
| --- | --- |
| [架构](architecture.md) | 系统分层、任务执行、三类存储、embedding 与设计取舍 |
| [后端](../backend/README.md) / [前端](../frontend/README.md) | 运行命令、HTTP 接口、实现入口与交互 |
| [运行时契约](runtime-contracts.md) | SSE / Trace / 导出及跨前后端约束 |
| [Agent 上下文与反馈](agent-core-alignment.md) | 历史快照、证据预算与有界模型决策 |
| [依赖与绑定](tool-dependencies.md) / [任务并发](task-tool-parallel.md) / [HTTP 只读并发](http-read-parallel.md) | 工具图、结果引用与执行资格 |
| [终态事务](task-completion.md) / [分支重跑](task-reruns.md) / [实验性步骤恢复](task-checkpoints.md) | 保存一致性、幂等与恢复范围 |
| [流结束](provider-stream-completion.md) / [回答完整性](answer-completion.md) / [用量](usage-accounting.md) | 模型结束信号、展示与统计口径 |
| [RAG 后台导入](rag-background-ingest.md) | 接口预算、分批写入、权限与中断恢复 |
| [API 变更记录](api-changelog.md) | OpenAPI 指纹与兼容性审查 |

## 维护与运行

| 文档 | 内容 |
| --- | --- |
| [开发运行手册](development-runbook.md) | 测试、服务、Docker、浏览器、权限与提交 |
| [部署指南](pilot-deployment-preflight.md) | 生产镜像、配置预检、HTTPS、升级回滚与演练 |
| [备份恢复](local-stack-backup-restore.md) | 离线快照、新项目恢复与旧 Chroma 数据保护 |
| [验证基线](validation-baseline.md) / [真实模型记录](real-model-acceptance.md) | 已执行检查、证据范围、已知风险与外部待验收 |
| [贡献](../CONTRIBUTING.md) / [安全](../SECURITY.md) / [许可证](../LICENSE) | 变更流程、安全披露与授权 |

维护三个 README 和受影响专题；测试数字、实现状态与外部验收统一在验证基线，真实供应商证据单独保留。开发计划、重复收尾审计和旧镜像流水账已退出文档树，原文可从 Git 历史查询；不要重新创建。`data/insightagent.plan.back.md` 原始完整计划永远只读，历史目标不等于当前实现承诺。AGENTS、测试 fixture、API 基线与依赖锁文件属于有效工程资料，继续保留。
