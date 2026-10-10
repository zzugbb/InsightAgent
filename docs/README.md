# 文档导航

按任务选择阅读入口：

- **先看展示**：[在线展示](https://zzugbb.github.io/InsightAgent/) → [案例回放](https://zzugbb.github.io/InsightAgent/demo/) → [展示与发布](showcase.md)。
- **运行完整应用**：[项目 README](../README.md#快速开始) → [模型与凭据配置](configuration.md)。
- **理解与开发**：[架构](architecture.md) → [后端](../backend/README.md) / [前端](../frontend/README.md) → [贡献指南](../CONTRIBUTING.md)。
- **运行与排障**：[开发手册](development-runbook.md) → [部署与恢复](pilot-deployment-preflight.md)。
- **核对完成范围**：[验证基线](acceptance.md#验证基线) → [真实模型记录](acceptance.md#真实模型记录) → [业务验收](acceptance.md#业务-rag)。

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
| [公开展示与发布](showcase.md) | 已上线静态站、交互与素材边界、自动发布与维护 |
| [验收](acceptance.md) | 业务复核、签收、验证基线及真实模型证据 |
| [API变更](api-changelog.md) | OpenAPI指纹与兼容性审查 |

README 提供使用与模块入口，专题维护稳定行为，验收文档记录验证范围和证据。变更时更新受影响主题；开发过程从 Git 历史查询。维护规则见 [AGENTS](../AGENTS.md)，授权与安全问题见 [LICENSE](../LICENSE)、[SECURITY](../SECURITY.md)。
