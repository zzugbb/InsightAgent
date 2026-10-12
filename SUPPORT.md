# 使用与求助

InsightAgent 的完整应用与公开静态展示用途不同：展示站回放预设公开记录；实际提问、模型调用和资料导入需要运行完整应用。

## 先查文档

| 需要帮助的事项 | 阅读入口 |
| --- | --- |
| 安装和运行完整应用 | [快速开始](README.md#快速开始)、[开发运行手册](docs/development-runbook.md) |
| 模型、Key、网络与配置 | [配置指南](docs/configuration.md) |
| 工具执行、知识导入与任务恢复 | [工具执行](docs/tool-execution.md)、[RAG 导入](docs/rag-background-ingest.md)、[运行时契约](docs/runtime-contracts.md) |
| 静态展示、案例回放与 Pages 发布 | [展示说明](docs/showcase.md)、[展示 README](showcase/README.md) |
| 当前完成范围与已知边界 | [项目状态](README.md#项目状态)、[验收基线](docs/acceptance.md#验证基线) |

## 提交问题

先[搜索已有 Issue](https://github.com/zzugbb/InsightAgent/issues)，避免重复报告。没有对应记录时，从[Issue 入口](https://github.com/zzugbb/InsightAgent/issues/new/choose)选择：

- **缺陷报告**：提供源码提交或页面地址、环境、最小复现步骤及预期/实际结果；文档错误也可使用此模板。
- **改进建议**：说明具体场景、现有方式的限制、最小改动范围和验证方式。
- **使用问题**：说明目标、已阅读的文档和已尝试的步骤。

模板字段按问题填写，不适用的内容可删除；仍保留空白 Issue 入口，供其他协作事项及不含敏感细节的联系请求使用。PR 按[贡献指南](CONTRIBUTING.md)和仓库模板说明改动与实际验证。

公开报告仅使用合成示例与脱敏证据。不要上传真实 env、Key、密码、token、私人会话、业务原文、数据库备份或完整配置；日志和截图也需先检查。

## 安全与社区问题

安全漏洞遵循[安全政策](SECURITY.md)，社区行为问题遵循[行为准则](CODE_OF_CONDUCT.md)。不要将敏感报告放入公开 Issue；私密报告渠道是否可用，以仓库当前设置为准。没有可用私密渠道时，先向[维护者](https://github.com/zzugbb)发起不含敏感细节的联系请求，确认方式后再提供证据。

## 支持范围

当前按可复现问题和明确需求维护，没有固定响应时限或商业支持承诺。新建议先评估，不代表新增功能承诺；静态展示上线不代表完整应用已完成生产部署或业务签收。当前状态与验证边界统一见[验收基线](docs/acceptance.md)。
