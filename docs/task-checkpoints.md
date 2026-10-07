# 步骤恢复（实验功能）

任务详情页的「从步骤继续」在**独立会话**中保留来源任务输入与已确认的工具计划，复用所选步骤之前的成功工具结果，重新执行所选工具及剩余工具，然后生成新回答。原任务的 Trace、消息、usage 和终态不变；这不是前端 Replay，也不会撤销外部操作。

## 支持范围

- 仅支持本次功能上线后保存了快照的内建 `task_plan`、`task_retrieve`、`calc_eval` 顺序计划，最多 32 个工具。整份计划必须符合此范围；即使 HTTP 声明只读，也不支持 checkpoint。显式 DAG、结果绑定、自定义/覆盖 runner 和写入工具暂不支持恢复。
- 按保存的计划序号选择工具步骤；起点之前的所有工具必须成功并保存了观察结果。起点可以是成功或失败步骤。失败步骤之后没有合格前缀的步骤不可选；尚未执行的步骤不作为恢复起点。
- 内建顺序计划可按既有并发设置执行独立读取；checkpoint 前缀仍按计划顺序定义。历史检索结果是本人原任务的快照，**不会重新检索**，也不保证数据仍是最新版本。需要刷新检索时请选择检索步骤；需要改变输入、重新规划或执行 HTTP/DAG 时使用完整分支重跑。
- 新分支执行时使用当前模型和工具设置，先校验整份计划的内建 runner 身份及启用状态；不兼容时以 `checkpoint_unavailable` 失败，不调用工具。复用结果不重新计入模型 usage 或工具 token/cost；新工具调用与新回答仍可能产生费用。

## 接口

| 接口 | 契约 |
| --- | --- |
| `GET /api/tasks/{task_id}/checkpoints` | 本人任务的候选起点，返回 task_id、experimental=true、items；每项含 step_id、index、tool_name、reused_steps。旧任务/不支持的计划返回空 items；不存在或其他人的任务返回 404。 |
| `POST /api/tasks/{task_id}/reruns` | 请求新增可选 UUID `checkpoint_step_id`。指定后必须省略 user_input；原输入不可编辑，返回既有分支响应。 |

创建只允许本人已结束任务，沿用分支重跑的事务、唯一幂等键和来源查询；同键同起点返回同一分支，不同起点/不同完整重跑参数返回 `409 rerun_idempotency_conflict`。无可用快照返回 `409 checkpoint_unavailable`，同时编辑输入返回 `422 checkpoint_input_immutable`。客户端未知送达时重试复用原键及起点，并冻结选择；POST 不调用模型或工具，由既有 stream 接管 queued 任务。

## 保存与执行

没有新增数据库表：计划、工具序号和脱敏后的工具观察结果进入既有 Trace.meta。计划输入只接受内建字段白名单，若脱敏改变输入则不保存可恢复计划；单个分支快照最多 2 MB。创建事务把独立快照保存为新任务的 queued seed，来源被删除后分支仍可执行，来源关系变为空。

执行不重新调用规划模型。新任务先写新的规划 Trace，然后用新 UUID/新递增 seq 写入复用结果；`checkpoint_reused=true` 和 `checkpoint_source_step_id` 标注来源，复用步骤的 tokens/cost/latency/retryCount 归零。seq 沿用 delta 契约：唯一递增，不保证连续，最终回答更新可以跳号。普通执行步骤附加 checkpoint_index/checkpoint_observations，规划步骤附加 checkpoint_plan；这些是兼容的可选 meta 扩展，SSE 事件与 JSON v1.0/Markdown export shape 不变。

恢复任务仍受任务队列、execution owner、取消、超时和 reconnect 约束。工具结果提交前和进入新回答阶段前强制复核终态，阻止取消/超时之后的结果落盘或回答启动。外部调用无法强行中断，未受支持的远端工具也不进入恢复范围。

## 验证

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_checkpoint
# 独立 PostgreSQL/mock，需提权访问 Docker/随机本机端口，自动清理
backend/.venv/bin/python backend/scripts/test_task_checkpoint_postgres.py
# 已启动隔离 mock 栈
cd frontend
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 npm run test:e2e -- e2e/task-checkpoints.spec.ts
```

6 个静态专项检查 runner 身份、字段/图/HTTP 排除、前缀资格、独立快照与预算；9 个 PostgreSQL 场景检查实际复用且不重新规划、原任务不变、delta/export、新分支继续恢复、并发幂等、来源删除、权限、设置不兼容、失败重试、取消及超时。浏览器覆盖桌面创建/执行/来源往返和手机未知送达重试。均使用本地 mock；真实模型质量与试点环境仍未验收。
