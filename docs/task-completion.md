# 任务成功与回答保存

## 成功事务

正常任务的最终回答生成后，执行服务调用 `complete_task(..., assistant_content=final_content)`；在同一个 PostgreSQL 事务中保存成功状态、最终 Trace、usage、assistant 消息及会话 updated_at，提交后才执行 best-effort Memory 写入并发送 `done`。

- 终态更新仍受任务用户、活动状态与执行实例限制；未赢得终态写入时不插入回答。并发完成同一任务只会有一个成功写入，后续返回 0。
- 回答插入或会话更新时间写入失败会回滚成功事务，执行服务随后按既有流程保存失败状态/Trace 并发送错误；没有成功 assistant 或 Memory。失败重连不重放模型调用。
- 外部连接在提交前仍读取原活动状态，不能读到已完成却尚未保存回答的中间状态；提交后状态和回答一起可见。
- session_id 来自本次成功更新的任务行；调用方不能另行指定回答所在会话。
- 独立 `create_message` 保留原接口和事务，复用连接内写入助手；`complete_task` 不传 assistant_content 时保留既有取消、失败、工具失败及历史调用行为。
- SSE/Trace/delta/export 与 API 字段形状不变。此保证适用于当前正常任务成功路径，不补造历史缺失回答。

实现位置：`backend/app/services/chat_persistence_service.py` 的 `complete_task` / `_insert_chat_message` 与 `chat_execution_service.py` 的成功分支。事务未提交的异常由数据库连接关闭回滚；最终生成文字可保留在失败 Trace，但不作为成功会话消息进入后续上下文。

## 验证与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_completion_atomic
backend/.venv/bin/python backend/scripts/test_task_completion_postgres.py
```

2026-10-08：静态 5/5；独立 PostgreSQL 6/6，包含数据库触发器注入助手插入/会话更新时间失败、并发完成、取消/执行实例/用户竞争、提交前外部读取、成功回放/导出与下一轮会话上下文。集成已进入 backend-e2e，使用本地模型替身，无真实模型请求。

来源 `/tmp/insightagent-task-completion-{static,postgres}.log`；模型流 6/6、用量 3/3、步骤恢复 9/9 回归来源 `/tmp/insightagent-task-completion-{stream,usage,checkpoint}-regression.log`；完整门禁 `/tmp/insightagent-task-completion-release.md` / `.json`（10/10 PASS、后端 2180/2180、前端 206/206）。本轮未重跑浏览器。
