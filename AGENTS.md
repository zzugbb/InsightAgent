# 维护规则

InsightAgent已完成本地实现与工程收尾。后续围绕可复现问题或维护者明确的新需求变更；公开静态展示已上线，完整应用部署、业务资料和用户签收仍待外部验收，写入并行与HTTP/DAG checkpoint延期，不因持续推进自动扩展范围。

- `data/insightagent.plan.back.md`是原始完整计划，永远只读。已删除的实时计划和开发流水账不重新创建，历史从Git查询。
- 运行/测试/提交前读[开发手册](docs/development-runbook.md)。Python统一用`backend/.venv/bin/python`，前端用Node24+与npm；Docker、本机端口、浏览器e2e和写Git索引按当前环境权限流程执行。
- 先查已有服务与健康，不重复启动。PostgreSQL/Chroma数据保留；旧Chroma实际`/data`可能不在旧挂载卷内，未经备份不重建/删除容器或卷，见[恢复规则](docs/pilot-deployment-preflight.md#开发栈备份恢复)。
- 不输出或提交真实env、Key、密码、token、私人会话、数据库备份或构建/测试产物。使用[安全政策](SECURITY.md)与[配置指南](docs/configuration.md)。
- 沿用主题模块和兼容facade，不无限追加主编排或历史大文件。后端slice主题≤2500行，临近上限先拆分，再增加测试。
- 保留长期接口与运行契约，按影响同步根、受影响模块的README及主题文档；验证、已知风险和外部状态统一在[验收基线](docs/acceptance.md#验证基线)。纯文档变更核对链接/命令与hygiene，不重复跑无关全量测试。
- 区分源码完成、本地替身、真实模型、浏览器、镜像、CI和外部签收；completed不等于目标全部满足，未知用量不补零，旧CI/镜像不代表新源码已验证。
- 提交采用简体中文Conventional Commits，提交前检查暂存差异和原始计划；推送或部署按维护者授权处理，不虚报远端或目标环境结果。

项目介绍见[README](README.md)，文档入口见[docs](docs/README.md)。环境安装由各执行环境提供，不把本机macOS或旧云端绝对路径当成通用前提。
