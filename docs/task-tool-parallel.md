# 任务内工具并发

任务执行器可在同一个任务中并发运行已就绪的内建知识检索、计算和[显式声明只读的 HTTP GET](http-read-parallel.md)。规划、Trace 合并、持久化、审计、终态写入与最终回答仍由任务协调线程完成。跨任务队列的槽位与权限规则继续生效。

## 开关与范围

服务端环境变量 `TASK_TOOL_MAX_CONCURRENT` 范围为 1–4，默认 **1（串行）**。在启动 backend 前设为 `2` 即可启用当前内建检索/计算组合；`.env.example` 保留默认值。该选项不是用户模型设置字段，修改后需重启对应执行实例。Compose 的 backend 已通过 env_file 读取本机配置。

- runner 身份须与内建 `task_retrieve` / `calc_eval` 一致，或为 HTTP 工厂创建且 `parallel_read_only=true` 的固定 GET、无请求体工具；名称、语义 kind、显示标签或自定义属性不能赋予资格。
- 旧版平铺计划中相邻、可确认独立的工具按窗口执行；规划工具、未声明只读的 HTTP、未知/自定义 runner 及未解析的 dependsOn/dependencies/after 等提示形成串行屏障。含 depends_on/input_bindings 的[显式依赖计划](tool-dependencies.md)先校验整图与解析结果绑定，再对同波就绪工具应用并发窗口。
- 并发窗口固定 registry 快照，避免分类后 loader 切换实现；各次尝试仍使用既有输入归一化、有效用户上下文、shared/private 知识库规则和结果脱敏策略。
- 进程共享最多 **8 个读取线程**，包含取消后仍在返回中的读取。单任务窗口不会突破配置上限；该线程池与 `TASK_QUEUE_MAX_CONCURRENT` 的任务槽位是两个不同边界。
- 当前规则规划器通常只有一个检索项和一个计算项，因此启用值 2 即可覆盖该组合。Provider 可声明有界 DAG 与预览标量绑定；外部读取需要另外明确配置只读资格，写入工具仍串行。

## SSE、Trace 与最终回答

工具尝试复用既有 `tool_start` / `tool_end` / `state` / `error` 事件。不同工具的事件可能交错，同一 step 的尝试顺序不变；前端应按 step_id 合并状态，不假设同一时间只存在一个运行工具。

工作线程只生成事件与结果，不写 tasks、Trace、审计或消息。协调线程在窗口结束后按原计划顺序合并结果，重排 action/RAG follow-up 的 seq，再依次执行既有持久化动作与汇总最终回答输入。工具完成顺序不会改变最终观察顺序，Trace/delta 游标保持递增。

并发 action 的 `Trace.meta` 新增兼容的可选字段：

| 字段 | 含义 |
| --- | --- |
| `execution_mode` | 当前为 `parallel`；串行步骤不增加该字段 |
| `parallel_group_id` | 本次并发窗口的随机标识，与来源任务/会话无关 |
| `parallel_group_size` | 本窗口工具数量 |

既有 Trace.meta 允许扩展字段；JSON v1.0 和 Markdown 导出沿用原有结构及脱敏策略。没有新增接口或修改 OpenAPI 操作/组件指纹，当前为 51 操作 / 89 组件。

## 取消、超时与失败

协调线程等待结果时每 50ms 检查生命周期（数据库状态沿用既有 250ms 探测节流），刷新执行 heartbeat，空闲等待期间继续发送 SSE heartbeat。取消或超时后停止消费结果、取消未启动 future 并释放任务槽位，不等待正在进行的读取返回。

已进入底层读取的调用不能被 Python 线程强制中断；它们占用共享线程直至返回。返回后不得发布事件、持久化 Trace 或触发最终回答。窗口尚未合并时取消，其成功读取也可能不进入持久化 Trace；已发送的 tool_end 不能视为任务完成。该模式仅允许上述内建读取/纯计算和明确配置的 HTTP 读取，不承诺外部副作用回滚。

- 可重试失败只重试该工具，已成功的兄弟工具不重复运行。
- fatal 工具失败中止窗口，保留已接收结果及失败 Trace，写失败终态并阻止最终回答；取消其他未启动读取，丢弃迟到结果。
- 未知工作线程异常交回协调线程，沿用任务流失败处理；不会静默视为成功。
- 默认关闭时仍走既有串行执行/重试/服务动作语义，可通过将配置改回 1 回退。

## 验证

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task_parallel
# 需要 Docker/随机本机端口，独立 PostgreSQL，自动清理；LLM 和读取故障 fixture 为 mock
backend/.venv/bin/python backend/scripts/test_task_parallel_postgres.py
```

15 个内建并发静态专项及 6 个 PostgreSQL 场景覆盖重叠、屏障、快照、重试隔离、稳定顺序、生命周期、heartbeat、线程上限与导出。HTTP 另有 15 个静态专项和 7 个本机 HTTP/PostgreSQL 场景，见[读取并发](http-read-parallel.md)。数据库场景已接入 backend-e2e workflow。真实端点只读性与目标环境延迟待实证，写入工具并行明确延期。
