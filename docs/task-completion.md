# 任务终态与回答保存

## 成功事务

正常任务的最终回答生成后，执行服务调用 `complete_task(..., assistant_content=final_content)`；在同一个 PostgreSQL 事务中保存成功状态、最终 Trace、usage、assistant 消息及会话 updated_at，提交后才执行 best-effort Memory 写入并发送 `done`。

- 终态更新仍受任务用户、活动状态与执行实例限制；未赢得终态写入时不插入回答。并发完成同一任务只会有一个成功写入，后续返回 0。
- 回答插入或会话更新时间写入失败会回滚成功事务，执行服务随后按既有流程保存失败状态/Trace 并发送错误；没有成功 assistant 或 Memory。失败重连不重放模型调用。
- 外部连接在提交前仍读取原活动状态，不能读到已完成却尚未保存回答的中间状态；提交后状态和回答一起可见。
- session_id 来自本次成功更新的任务行；调用方不能另行指定回答所在会话。
- 独立 `create_message` 保留原接口和事务，复用连接内写入助手；`complete_task` 不传 assistant_content 时保留既有取消、失败、工具失败及历史调用行为。
- SSE/Trace/delta/export 与 API 字段形状不变。此保证适用于当前正常任务成功路径，不补造历史缺失回答。

实现位置：`backend/app/services/chat_persistence_service.py` 的 `complete_task` / `_insert_chat_message` 与 `chat_execution_service.py` 的成功分支。事务未提交的异常由数据库连接关闭回滚；最终生成文字可保留在失败 Trace，但不作为成功会话消息进入后续上下文。

## 结束前复核与失败用量

- 模型流迭代结束、空流回退生成返回后，以及最终 Trace 保存后/成功事务提交前，复核任务取消与总执行时限。最后文本之后或保存期间跨时限，不写成功回答、Memory 或 `done`；保持既有 timeout/error 事件。
- 使用同步 Provider 的等待仍受提供方 socket timeout 约束；这次补齐的是等待返回后的终态判定，不保证阻塞读期间立即中断。
- 模型/工具/数据库写入失败、执行器自己终结的超时均保存已记录规划/决策用量；已完成最终调用沿用正常记录，未完成调用仅保存提供方实际返回的用量。字段缺失保持未知，不根据部分文字补估。详见[用量汇总](usage-accounting.md)。
- 迟到反馈决策返回的用量可以计入执行器超时记录，但不追加决策 Trace 或新工具；调用抛错且未返回用量的消耗保持未知。
- 活动状态、用户与执行实例写入保护继续有效；外部取消/其他实例已经终结后，不覆盖其终态或用量。这些竞争下尚未保存的消耗仍可能未知。
- 前端支持仅规划/整体用量的任务，不把未知的最终回答用量显示为 0。

新增实现位于 `backend/app/services/task_terminal_usage.py`，只构建已知消耗记录；执行服务复用既有终态写入与统计接口。

## 验证与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_completion_atomic
backend/.venv/bin/python backend/scripts/test_task_completion_postgres.py
```

2026-10-08：静态 5/5；独立 PostgreSQL 6/6，包含数据库触发器注入助手插入/会话更新时间失败、并发完成、取消/执行实例/用户竞争、提交前外部读取、成功回放/导出与下一轮会话上下文。集成已进入 backend-e2e，使用本地模型替身，无真实模型请求。

来源 `/tmp/insightagent-task-completion-{static,postgres}.log`；模型流 6/6、用量 3/3、步骤恢复 9/9 回归来源 `/tmp/insightagent-task-completion-{stream,usage,checkpoint}-regression.log`；完整门禁 `/tmp/insightagent-task-completion-release.md` / `.json`（10/10 PASS、后端 2180/2180、前端 206/206）。本轮未重跑浏览器。

2026-10-08 终态维护：静态 `-k task_terminal_usage` **5/5**，前端用量计算 **8/8**；独立 PostgreSQL `test_task_terminal_postgres.py` **10/10**，覆盖流尾、空流回退、最终 Trace 保存跨时限，迟到决策、取消竞争、工具/决策/流失败、真实本机 HTTP usage 后 EOF、汇总/导出与成功写入失败。已进入 backend-e2e。来源 `/tmp/insightagent-task-terminal-{static,frontend,postgres}.log`；反馈、模型流、原子成功回归各 **6/6**，来源 `/tmp/insightagent-task-terminal-{feedback,stream,completion}-regression.log`。完整门禁 `/tmp/insightagent-task-terminal-release.md` / `.json`；无真实模型/目标部署或浏览器复验。
