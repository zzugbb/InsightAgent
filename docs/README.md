# 文档导航

首次使用见[项目README](../README.md)，模块命令与实现入口见[后端](../backend/README.md)和[前端](../frontend/README.md)。docs只保留以下10份主题文档；稳定规则与验收证据分节查阅，不再维护开发计划和单功能收尾记录。

| 文档 | 用途 |
| --- | --- |
| 本导航 | 阅读顺序与维护约定 |
| [架构](architecture.md) | 系统分层、存储、embedding、Agent上下文与反馈 |
| [配置](configuration.md) | 模型Key、继承、前端地址、网络与轮换 |
| [工具执行](tool-execution.md) | DAG、标量绑定、内建/HTTP只读并发与配置示例 |
| [任务契约](runtime-contracts.md) | SSE/Trace、终态、回答、用量、分支与步骤恢复 |
| [RAG导入](rag-background-ingest.md) | 文件预算、持久队列、批次/权限与部分失败 |
| [开发手册](development-runbook.md) | 检查、服务、Docker/e2e、诊断、权限与提交 |
| [部署与恢复](pilot-deployment-preflight.md) | 镜像、预检、HTTPS、升级回滚、离线备份/恢复 |
| [验收](acceptance.md) | 业务复核、签收、验证基线及真实模型证据 |
| [API变更](api-changelog.md) | OpenAPI指纹与兼容性审查 |

项目授权见[LICENSE](../LICENSE)，贡献与安全问题见[CONTRIBUTING](../CONTRIBUTING.md)、[SECURITY](../SECURITY.md)。README面向使用者，AGENTS面向自动化维护；测试fixture、API基线与锁文件保留。更新受影响主题，当前结果集中在验收的验证基线；旧开发过程从Git历史查询，`data/insightagent.plan.back.md`原始完整计划永远只读。
