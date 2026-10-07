# 工具依赖与结果引用

Provider 规划器可声明有向无环图（DAG）：同一种工具可出现多次，后续步骤可依赖前一步，并把已公开结果预览中的标量作为查询或计算输入。规则规划器和旧版平铺计划保持原有行为；当前不提供前端图编辑器、单步 checkpoint 恢复或写入工具并行。

## 规划协议

任一工具项含 `depends_on` 或 `input_bindings` 时，整份计划进入显式依赖模式。每项必须有唯一 `id`；名称仍须来自当前 registry 的已启用规划候选。自动生成的规划步骤由服务端添加，不写入下面的 `tools`。

```json
{
  "tools": [
    {"id": "sum", "name": "calc_eval", "input": {"expression": "2+3"}, "depends_on": []},
    {
      "id": "scaled", "name": "calc_eval", "input": {}, "depends_on": ["sum"],
      "input_bindings": {"expression": {"node": "sum", "path": ["result"], "template": "{value} * 2"}}
    },
    {
      "id": "search", "name": "task_retrieve",
      "input": {"query": "placeholder", "knowledge_base_id": "default"},
      "input_bindings": {"query": {"node": "scaled", "path": ["result"], "template": "value {value}"}}
    }
  ]
}
```

该例依次执行 `2+3`、`5.0 * 2`、查询 `value 10.0`。绑定源会自动加入依赖，因此 `search` 可省略 `depends_on`。前向引用允许；无依赖项先运行，每批就绪项按原计划中的相对顺序处理。旧计划继续按名称去重，显式图按节点 ID 保留重复工具。

- ID 为 1–64 个 ASCII 字符，以字母开头，其余允许字母、数字、下划线、连字符。
- 最多 32 个工具节点、128 条依赖边；未知、重复、自身引用、缺失 ID、循环依赖和不允许的工具会在任何工具执行前拒绝整图，返回 `tool_dependency_plan_invalid`，不会降级成部分执行或规则计划。
- `depends_on` 必须为无重复 ID 的数组；`input_bindings` 为对象，当前目标仅支持 `query` / `expression`，归一化后的工具输入必须包含对应字段。
- path 为 1–8 层数组：对象键为 1–80 字符字符串，数组索引为 0–1000 的整数；布尔索引、属性访问和代码表达式不参与解析。

## 结果边界

引用只读取上游成功 action 的 **`meta.tool.output_preview`**，沿用 registry 的投影与脱敏。原始工具输出、异常正文和未公开字段不可引用。最终叶子必须为字符串、整数、有限浮点数或布尔值；空文本、null、对象、数组、非有限数和不可用路径返回 `tool_dependency_input_unavailable`，保留已完成 Trace 并阻止后续调用与最终回答。

每个标量转换后的文本最多 8192 字符；可选 template 最多 8192 字符，必须含 1–8 次字面量 `{value}`，只作文本替换；最终输入最多 16384 字符。模板不执行 format、属性求值或代码。绑定后的计算表达式仍经既有 AST 白名单校验，查询仍按有效用户和 literal `knowledge_base_id` 进行权限检查。不能绑定用户身份、知识库 ID、URL、header、密钥或工具名称。

## 调度与生命周期

按稳定拓扑波次调度：一波结果完成并由协调线程处理后，才解锁下一波；不会按某个工具先完成就立即启动其子节点。就绪波内实际内建检索/计算 runner 和[明确配置只读的 HTTP GET](http-read-parallel.md) 可按 [任务内并发](task-tool-parallel.md) 有界执行，默认 `TASK_TOOL_MAX_CONCURRENT=1` 仍串行。规划、自定义和未声明只读的 HTTP 工具仍形成串行屏障；依赖声明本身不赋予并发资格。

工作线程只产出事件与结果；Trace、审计、终态和消息继续由协调线程写入。上游失败耗尽重试或 fatal 后停止后续节点；取消/超时沿用任务生命周期检查，阻止依赖节点启动和迟到结果写入。正在进行的底层读取仍不能强制中断，进程线程上限保持 8。

## Trace 与兼容性

显式节点 action 的 `Trace.meta` 增加可选 `plan_node_id`、`depends_on`，后者包含结果绑定推导出的依赖。`plan_node_id` 是本计划中的引用 ID，与持久化 `TraceStep.id` 不同；工具 input 为本次实际解析后的输入。前向引用会改变工具执行顺序，Trace.seq 按实际拓扑执行及既有 RAG follow-up 顺序递增；同波并发合并按计划相对顺序。

SSE 事件名称、Trace/delta 外层结构、JSON v1.0/Markdown 导出与权限规则保持兼容。没有新增 HTTP 接口；OpenAPI 仍为 50 操作 / 86 组件。前端继续按 step_id 消费既有事件和 Trace，无需生成本地节点 ID。

## 验证与实现位置

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_dependency
# 需要 Docker/随机本机端口；独立 PostgreSQL + 本地规划 fixture，无远端 LLM 调用，自动清理
backend/.venv/bin/python backend/scripts/test_tool_dependencies_postgres.py
```

25 个静态专项覆盖图校验、前向引用、重复工具、输入/投影边界、拓扑顺序、并发分支、失败重试与 AST 校验；7 个 PostgreSQL 场景覆盖实际规划/任务流、Trace/delta/export、错误审计、串行回退、取消与超时。后者已接入 backend-e2e workflow。真实提供方的图生成质量、目标环境性能、单步恢复和写入工具并行仍待验证或实现。

- `backend/app/services/tool_plan_dependencies.py`：图校验、拓扑波次、结果绑定。
- `backend/app/services/tool_runtime_planning.py`：Provider 协议说明、候选工具归一化与图错误透传。
- `backend/app/services/task_tool_execution.py`：就绪工具执行、观察收集及持久化协调。
