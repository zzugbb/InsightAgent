# Development Runbook

本文件记录当前 Codex 沙箱下 InsightAgent 的高频运行、e2e 与提交路径。目标是后续开发直接走正确命令和权限，不再用失败来探测环境。

## 快速规则

- 后端 Python 统一用 `backend/.venv/bin/python`，不要临时找系统 Python 或重装依赖。
- 前端 Node 依赖已在 `frontend/node_modules`，常规检查在 `frontend/` 下用 `npm` 脚本。
- 单元/slice/lint 通常不需要提权。
- 访问本机 Docker、监听本机端口、访问本机 e2e 服务、写 `.git/index` 通常需要提权。
- `data/insightagent.plan.back.md` 永远不要修改。
- `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 虽在 `.gitignore` 范围内，但当前是 tracked 文件，文档同步和提交必须包含它。
- 每个主线确认封板后，整理 `README.md`、`backend/README.md`、`frontend/README.md` 与实时计划文件：仅收敛“进度/封板状态相关块”，保留当前状态、当前验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要；删除或收缩按轮流水账、旧失败过程和重复验证清单。
- 文档收敛不是把整份 README 改成短状态页；接口范围、运行方式、关键实现位置、SSE/Trace 契约、Memory/RAG 说明、文档维护约定等长期参考章节应保留，除非对应功能真的被删除或迁移。
- 控制单文件规模：新增测试/实现优先落到主题文件；主题文件明显膨胀时先拆出新主题文件或新模块，再继续追加。历史上的 `backend/scripts/test_tool_runtime_slice.py` 和 `app/services/tool_runtime.py` 已按该规则拆成 slice 主题包与 facade 模块。

## 不需要提权的常用命令

从仓库根目录运行：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task
python3 -m py_compile backend/app/config.py backend/app/services/chat_execution_service.py backend/app/services/task_queue_service.py
bash scripts/ci_run_release_gate.sh --phase auto
bash scripts/ci_release_readiness_matrix.sh --format markdown
git diff --check
git diff --cached --check
git diff -- data/insightagent.plan.back.md
```

`scripts/ci_run_release_gate.sh` 是不启动本机服务的发布前门禁聚合入口：`auto` 在 PR 中按 changed files 选择 backend/frontend 阶段，并始终跑 tooling 与 hygiene；非 PR 或 diff 不可解析时保守跑全量。`backend` 跑 full slice 与 module boundary，`frontend` 跑 node tests、lint、build，`tooling` 跑 CI/e2e tooling 自测，`hygiene` 跑 compileall、diff whitespace 与备份计划 diff；可用 `--dry-run` 查看命令清单，可用 `--summary-file` / `--json-summary-file` 输出 CI 摘要。

`scripts/ci_release_readiness_matrix.sh` 只生成发布候选检查矩阵，支持 `--format markdown|json` 与 `--output <path>`。矩阵明确区分不需要服务的静态 release gate、需要已启动服务的 backend/frontend e2e，以及 e2e 后置 artifact-stage guard；它不启动服务，也不替代下方 service-backed e2e 命令。
GitHub backend/frontend e2e workflow 已按矩阵覆盖低并发 queue 阶段；backend 失败诊断可重复传 `--secondary-health-url`，用于同时采集 timeout 与 queue 实例。
artifact-stage guard 的 main push 严格度为 `fail-on-missing`，PR 严格度为 `fail-on-empty`；手动 `workflow_dispatch` 可用 `artifact_stage_strict_level` 覆盖。

前端检查：

```bash
cd frontend
npm run lint
node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts
```

## 需要提权的本机服务

普通沙箱下，backend 访问 `127.0.0.1:5432` PostgreSQL / Chroma 或 frontend 监听 `127.0.0.1:3001` 会经常遇到 `Operation not permitted` / `EPERM`。后续需要启动项目或跑 e2e 时，直接按流程申请提权启动：

后端，工作目录 `backend/`：

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端，工作目录 `frontend/`：

```bash
npm run dev -- --hostname 127.0.0.1 --port 3001
```

健康检查也需要提权访问本机端口：

```bash
curl -sS http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3001
```

如果提权审批因为审核通道连接中断被拒，不要绕路用等价命令规避；重新发起同一必要命令的明确审批。

## e2e 路径

Docker 依赖通常已启动，可先普通查看：

```bash
docker compose ps
```

backend/frontend 服务启动后，e2e 需要访问本机端口，直接申请提权运行：

```bash
bash scripts/ci_run_backend_e2e.sh --phase main --base-url http://127.0.0.1:8000 --log-dir /tmp
bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001
```

低并发队列专项 e2e 需要单独启动一个 backend，避免影响默认 full Chromium 并发基线：

```bash
TASK_QUEUE_MAX_CONCURRENT=1 TASK_QUEUE_POLL_INTERVAL_SEC=0.1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
bash scripts/ci_run_backend_e2e.sh --phase queue --base-url http://127.0.0.1:8011 --log-dir /tmp
```

低并发前端队列专项需要同时启动 backend 与 frontend，并让 frontend 指向 `8011`。backend 与 frontend 是两个长驻会话；测试脚本从仓库根目录单独运行：

```bash
TASK_QUEUE_MAX_CONCURRENT=1 TASK_QUEUE_POLL_INTERVAL_SEC=0.1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8011 npm run dev -- --hostname 127.0.0.1 --port 3001
bash scripts/ci_run_frontend_e2e.sh --phase queue --api-base-url http://127.0.0.1:8011 --frontend-base-url http://127.0.0.1:3001
```

单条 Chromium 复验在 `frontend/` 下运行，也需要提权：

```bash
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 npm run test:e2e -- e2e/workbench-remote-errors.spec.ts:527
```

跑完后停止本轮启动的 backend/frontend 会话，并确认端口无残留：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3001 -sTCP:LISTEN
```

## 提交路径

当前环境普通 `git add` / `git commit` 经常失败：

```text
fatal: Unable to create '.git/index.lock': Operation not permitted
```

后续提交可以在确认 diff 后直接申请提权 stage/commit。因为 `.cursor/` 被 ignore，实时计划文件需要强制 add：

```bash
git add README.md backend/README.md frontend/README.md <changed-files>
git add -f .cursor/plans/insightagent_开发计划_306e7915.plan.md
git diff --cached --check
git diff --cached -- data/insightagent.plan.back.md
git commit -m "<message>"
```

提交后最终核对：

```bash
git status --short
git log -1 --oneline
git diff -- data/insightagent.plan.back.md
git status --short --ignored .cursor/plans/insightagent_开发计划_306e7915.plan.md
```
