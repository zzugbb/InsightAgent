# AGENTS

本仓库的开发规则（强制）：

1. 永远不要修改备份的完整开发计划文件：`data/insightagent.plan.back.md`。
2. 每次开发完成后，必须同步更新以下文档：
   - `README.md`
   - `backend/README.md`
   - `frontend/README.md`
   - `.cursor/plans/` 下的实时计划文件
3. 每个主线确认封板后，必须额外整理上述四份活跃文档：
   - 只保留当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要
   - 删除或收缩按轮流水账、旧失败过程、重复验证清单和阶段内细碎过程描述
   - 明确主线封板结论、最终验证来源，以及是否可进入下一主线
4. 运行测试、e2e、启动项目和提交前，先参考 `docs/development-runbook.md`：
   - 后端使用 `backend/.venv/bin/python`
   - 本机端口 / Docker 访问、e2e、本地服务启动通常需要提权
   - `git add` / `git commit` 写 `.git/index` 通常需要提权
   - `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 被 ignore 但已 tracked，提交时需要继续纳入
5. 控制单文件规模，避免无限追加：
   - 新增测试、文档或实现时，优先放入已有主题文件；如果主题文件已经明显膨胀，先拆分到新主题文件/新模块
   - 不把历史大文件当作默认追加点；曾经的 `backend/scripts/test_tool_runtime_slice.py` 和 `app/services/tool_runtime.py` 已拆分为主题包与 facade 模块，后续继续沿用该拆分方式
   - 单轮变更如果会显著增加单文件长度，应同步评估拆分方案，再继续实现
