# 贡献指南

欢迎提交可复现问题、文档修正和围绕项目定位的改进。新功能先说明真实使用场景、外部契约影响及验证方式；当前维护以既有能力的问题修复为主。

## 开发准备

按照[根 README](README.md#快速开始)准备 Python 3.14、Node.js 24+ 与本地依赖。运行前阅读 [AGENTS.md](AGENTS.md) 和[开发运行手册](docs/development-runbook.md)。已有 PostgreSQL / Chroma 数据需保留；不要为了测试重建开发数据库，集成测试使用独立 fixture。

只修改展示站时，按[展示 README](showcase/README.md)准备 Node 24 和独立依赖，不需要启动后端或数据服务。公开案例采集会创建本机数据并可能消耗真实模型用量，普通构建和 CI 不运行采集脚本。

## 提交变更

1. 说明具体触发条件和预期行为；缺陷优先补能复现原问题的测试。
2. 沿用主题模块与兼容 facade，控制单文件规模，不机械增加包装层。
3. 运行受影响专项与对应门禁；浏览器/数据库/真实模型结果分别记载，不能把替身通过写成业务验收。
4. 同步根、受影响模块（backend/frontend/showcase）的 README 与专题；当前状态和验证集中在 [验收基线](docs/acceptance.md#验证基线)，不要重复追加开发流水账。
5. 检查 diff、冲突标记、秘密与生成产物。提交使用简体中文 Conventional Commits，例如 `fix: 修复取消后的任务状态同步`。

`data/insightagent.plan.back.md` 是原始完整计划，永远只读。开发实时计划已删除，历史过程从 Git 查询；不要重建计划文件或把历史目标写成已实现能力。

## 验证入口

```bash
bash scripts/ci_run_release_gate.sh --phase auto
backend/.venv/bin/python backend/scripts/check_api_surface.py
```

门禁会按范围运行 backend/frontend/tooling/hygiene；完整数据库和浏览器测试按[运行手册](docs/development-runbook.md)执行。发布门禁不等于部署验收。接口变化按[API 变更记录](docs/api-changelog.md)核对 OpenAPI、SSE、Trace 与导出兼容性。

展示站的类型、lint、格式、Node tests、静态构建与浏览器命令按[展示 README](showcase/README.md)执行。纯文档修改只检查链接、命令和 hygiene。main 上展示目录或发布工作流变更会自动发布至 Pages，PR 只检查。

## 问题报告与审查

普通问题记录源码提交、环境类别、脱敏的复现步骤、预期/实际结果及相关检查。不要上传真实 env、API Key、登录 token、密码、数据库备份或私人会话；安全问题先按 [SECURITY.md](SECURITY.md) 私密披露。

PR 描述以问题和最终行为开头，附实际完成的验证及边界；未执行的检查明确标注。贡献遵循项目现有 [MIT License](LICENSE)。
