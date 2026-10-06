# 任务分支重跑

任务详情页的「分支重跑」允许从本人已结束的任务复制或编辑输入，在**独立会话**中重新执行完整任务。原任务的状态、Trace、usage、消息与导出不变；来源和分支通过单独接口查询。新任务使用执行时的当前模型、工具和知识库设置，不复制历史消息、Memory、Trace 或结果，也不保证复现历史版本的数据或回答。

## 接口与执行

| 接口 | 契约 |
| --- | --- |
| `POST /api/tasks/{task_id}/reruns` | 保存独立会话、queued 任务、首条用户消息和来源关系，返回 201；请求体可为 `{}`，或包含 UUID `idempotency_key` 与可选 `user_input`。不在本接口调用 LLM/工具。 |
| `GET /api/tasks/{task_id}/reruns?limit=20&offset=0` | 返回本人任务的来源与直接分支；limit 1–100、offset >= 0，最新分支优先；包含 total、has_more。 |

POST 返回既有 `TaskCreateResponse` 字段及可空 `parent_task_id`。只允许 `completed/failed/cancelled/timed_out` 及既有状态别名的任务创建分支；排队、pending、running 或未知状态返回 `409 rerun_parent_not_terminal`。不存在或属于其他人的来源任务统一 404；管理员也不会取得其他用户的重跑权限。

- 省略 `user_input` 时使用原始 prompt；提供时先 trim，非空且最多 64,000 字符。历史 prompt 本身超限或空白时返回 `422 rerun_input_invalid`，可提供符合约束的编辑输入。
- 同用户、同幂等键、同来源及同请求参数返回同一个分支及其**当前状态**，不重复创建会话、消息或审计。同键不同参数返回 `409 rerun_idempotency_conflict`；未提供键时每次请求生成新键。
- 客户端无法确认响应是否送达时，重试须复用原键和参数。前端失败重试冻结本次输入并复用键；要修改输入另建分支，应先查看列表确认已受理的分支。
- GET 包含 `task_id`、`is_rerun`、`parent_task_id`、`items`、`total`、`limit`、`offset`、`has_more`；每个直接分支仅含 task_id、session_id、status、created_at。无请求键、hash、原始输入或内部用户身份。
- 这是完整任务重跑，不是从某个 Trace 步骤恢复、复用工具输出或重放外部副作用。工具/LLM 会按当前设置重新调用，可能产生费用或新的外部写入。

新任务通过既有 `GET /api/tasks/{child_task_id}/stream` 执行，沿用并发队列、取消、超时与恢复语义。「创建并运行」保存后选择新会话并返回 Workbench，由既有任务恢复流程接管 SSE；仅用 POST 创建后关闭客户端，不保证任务自动执行。再次打开该分支会话可继续接管 queued/running 任务。

## 持久化与删除

`task_reruns` 使用用户范围的唯一幂等键。创建时持有用户事务 advisory lock 及来源行读锁，同一事务插入 session、task、message 与 relation；任何插入失败都会回滚整组记录。新增表及索引通过数据库初始化幂等创建，原任务表/响应/导出无需迁移。

- 删除来源任务或其会话会将关系中的 parent_task_id 置空；独立分支继续存在，GET 返回 `is_rerun=true` 且无来源 ID，界面说明来源已删除。
- 删除分支会话/任务会级联清除其关系；幂等记录与分支同寿命，不承诺删除分支后仍能恢复原响应。
- 审计 `task_rerun_created` 仅记录新任务/会话/来源 ID、input_edited 和 prompt_length，不记录正文、密钥或历史结果。
- 原任务列表、详情、SSE、Trace 和 JSON v1.0/Markdown export shape 保持稳定；需要来源信息的调用方应使用新增 GET 接口。

## 验证

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_rerun
# 需要 Docker/本机随机端口；使用并清理独立临时 PostgreSQL，执行使用 mock
backend/.venv/bin/python backend/scripts/test_task_rerun_postgres.py
# 已启动 mock backend/frontend、PostgreSQL 与 Chroma 时运行
cd frontend
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 \
  npm run test:e2e -- e2e/task-reruns.spec.ts
```

7 个静态专项、11 个真实 PostgreSQL 场景与 4 个浏览器场景覆盖编辑/执行/来源往返、未知送达重试、活动任务禁用及手机分页。数据库场景已接入 backend-e2e workflow。当前验证采用本机 mock 提供方，真实提供方质量、收费与目标环境验收仍待实证；单步恢复和任务内并行仍未实现。
