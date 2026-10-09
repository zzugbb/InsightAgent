# 贡献指南

欢迎提交可复现问题、文档修正和围绕项目定位的改进。新功能先说明真实使用场景、外部契约影响及验证方式；当前维护以既有能力的问题修复为主。

## 开发准备

按照[根 README](README.md#快速开始)准备 Python 3.14、Node.js 24+ 与本地依赖。运行前阅读 [AGENTS.md](AGENTS.md) 和[开发运行手册](docs/development-runbook.md)。已有 PostgreSQL / Chroma 数据需保留；不要为了测试重建开发数据库，集成测试使用独立 fixture。

## 提交变更

1. 说明具体触发条件和预期行为；缺陷优先补能复现原问题的测试。
2. 沿用主题模块与兼容 facade，控制单文件规模，不机械增加包装层。
3. 运行受影响专项与对应门禁；浏览器/数据库/真实模型结果分别记载，不能把替身通过写成业务验收。
4. 同步 `README.md`、`backend/README.md`、`frontend/README.md` 和实时计划；专题文档保留稳定规则，证据集中在验收记录。
5. 检查 diff、冲突标记、秘密与生成产物。提交使用简体中文 Conventional Commits，例如 `fix: 修复取消后的任务状态同步`。

`data/insightagent.plan.back.md` 是原始完整计划，永远只读。实时计划 `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 已 tracked 但被 ignore，提交时必要用 `git add -f`。

## 验证入口

```bash
bash scripts/ci_run_release_gate.sh --phase auto
backend/.venv/bin/python backend/scripts/check_api_surface.py
```

门禁会按范围运行 backend/frontend/tooling/hygiene；完整数据库和浏览器测试按[运行手册](docs/development-runbook.md)执行。发布门禁不等于部署验收。接口变化按[API 变更记录](docs/api-changelog.md)核对 OpenAPI、SSE、Trace 与导出兼容性。

## 问题报告与审查

普通问题记录源码提交、环境类别、脱敏的复现步骤、预期/实际结果及相关检查。不要上传真实 env、API Key、登录 token、密码、数据库备份或私人会话；安全问题先按 [SECURITY.md](SECURITY.md) 私密披露。

PR 描述以问题和最终行为开头，附实际完成的验证及边界；未执行的检查明确标注。贡献遵循项目现有 [MIT License](LICENSE)。
