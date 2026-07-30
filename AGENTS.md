# AGENTS

本仓库的开发规则（强制）：

1. 永远不要修改备份的完整开发计划文件：`data/insightagent.plan.back.md`。
2. 每次开发完成后，必须同步更新以下文档：
   - `README.md`
   - `backend/README.md`
   - `frontend/README.md`
   - `.cursor/plans/` 下的实时计划文件
3. 运行测试、e2e、启动项目和提交前，先参考 `docs/development-runbook.md`：
   - 后端使用 `backend/.venv/bin/python`
   - 本机端口 / Docker 访问、e2e、本地服务启动通常需要提权
   - `git add` / `git commit` 写 `.git/index` 通常需要提权
   - `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 被 ignore 但已 tracked，提交时需要继续纳入
