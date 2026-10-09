# 工具执行、依赖与并发

内建检索使用真实 Chroma，计算使用 AST 白名单；HTTP JSON 工具按显式配置执行。本文定义图、结果绑定和只读并发，模型规划与上下文见[架构](architecture.md#agent-上下文与反馈)，任务终态与恢复见[运行时契约](runtime-contracts.md)。

## 依赖与结果绑定

Provider 规划器可声明有向无环图（DAG）：同一种工具可出现多次，后续步骤可依赖前一步，并把已公开结果预览中的标量作为查询或计算输入。规则规划器和旧版平铺计划保持原有行为；当前不提供前端图编辑器、HTTP/DAG checkpoint 恢复或写入工具并行。

### 规划协议

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
- 最多 32 个工具节点、128 条依赖边；未知、重复、自身引用、缺失 ID、循环依赖和不允许的工具会在任何工具执行前拒绝整图，返回 `tool_dependency_plan_invalid`，不会降级成部分执行或规则计划。模型已返回的实际规划用量仍计入失败任务；首次和反馈规划均适用，缺失字段不估算，见[用量口径](runtime-contracts.md#用量口径)。
- `depends_on` 必须为无重复 ID 的数组；`input_bindings` 为对象，当前目标仅支持 `query` / `expression`，归一化后的工具输入必须包含对应字段。合法绑定可省略对应字面量，运行时使用上游结果；后续模型规划中未绑定的必填字段必须为非空文本，不能从提示补齐。
- path 为 1–8 层数组：对象键为 1–80 字符字符串，数组索引为 0–1000 的整数；布尔索引、属性访问和代码表达式不参与解析。

### 结果边界

引用只读取上游成功 action 的 **`meta.tool.output_preview`**，沿用 registry 的投影与脱敏。原始工具输出、异常正文和未公开字段不可引用。最终叶子必须为字符串、整数、有限浮点数或布尔值；空文本、null、对象、数组、非有限数和不可用路径返回 `tool_dependency_input_unavailable`，保留已完成 Trace 并阻止后续调用与最终回答。

每个标量转换后的文本最多 8192 字符；可选 template 最多 8192 字符，必须含 1–8 次字面量 `{value}`，只作文本替换；最终输入最多 16384 字符。模板不执行 format、属性求值或代码。绑定后的计算表达式仍经既有 AST 白名单校验，查询仍按有效用户和 literal `knowledge_base_id` 进行权限检查。不能绑定用户身份、知识库 ID、URL、header、密钥或工具名称。

### 调度与生命周期

按稳定拓扑波次调度：一波结果完成并由协调线程处理后，才解锁下一波；不会按某个工具先完成就立即启动其子节点。就绪波内实际内建检索/计算 runner 和[明确配置只读的 HTTP GET](tool-execution.md#http-只读并发) 可按 [任务内并发](tool-execution.md#任务内并发) 有界执行，默认 `TASK_TOOL_MAX_CONCURRENT=1` 仍串行。规划、自定义和未声明只读的 HTTP 工具仍形成串行屏障；依赖声明本身不赋予并发资格。

工作线程只产出事件与结果；Trace、审计、终态和消息继续由协调线程写入。上游失败耗尽重试或 fatal 后停止后续节点；取消/超时沿用任务生命周期检查，阻止依赖节点启动和迟到结果写入。正在进行的底层读取仍不能强制中断，进程线程上限保持 8。

### Trace 与兼容性

显式节点 action 的 `Trace.meta` 增加可选 `plan_node_id`、`depends_on`，后者包含结果绑定推导出的依赖。`plan_node_id` 是本计划中的引用 ID，与持久化 `TraceStep.id` 不同；工具 input 为本次实际解析后的输入。前向引用会改变工具执行顺序，Trace.seq 按实际拓扑执行及既有 RAG follow-up 顺序递增；同波并发合并按计划相对顺序。

SSE 事件名称、Trace/delta 外层结构、JSON v1.0/Markdown 导出与权限规则保持兼容。没有新增 HTTP 接口；OpenAPI 当前为 51 操作 / 89 组件。前端继续按 step_id 消费既有事件和 Trace，无需生成本地节点 ID。


## 任务内并发

任务执行器可在同一个任务中并发运行已就绪的内建知识检索、计算和[显式声明只读的 HTTP GET](tool-execution.md#http-只读并发)。规划、Trace 合并、持久化、审计、终态写入与最终回答仍由任务协调线程完成。跨任务队列的槽位与权限规则继续生效。

### 开关与范围

服务端环境变量 `TASK_TOOL_MAX_CONCURRENT` 范围为 1–4，默认 **1（串行）**。在启动 backend 前设为 `2` 即可启用当前内建检索/计算组合；`.env.example` 保留默认值。该选项不是用户模型设置字段，修改后需重启对应执行实例。Compose 的 backend 已通过 env_file 读取本机配置。

- runner 身份须与内建 `task_retrieve` / `calc_eval` 一致，或为 HTTP 工厂创建且 `parallel_read_only=true` 的固定 GET、无请求体工具；名称、语义 kind、显示标签或自定义属性不能赋予资格。
- 旧版平铺计划中相邻、可确认独立的工具按窗口执行；规划工具、未声明只读的 HTTP、未知/自定义 runner 及未解析的 dependsOn/dependencies/after 等提示形成串行屏障。含 depends_on/input_bindings 的[显式依赖计划](tool-execution.md#依赖与结果绑定)先校验整图与解析结果绑定，再对同波就绪工具应用并发窗口。
- 并发窗口固定 registry 快照，避免分类后 loader 切换实现；各次尝试仍使用既有输入归一化、有效用户上下文、shared/private 知识库规则和结果脱敏策略。
- 进程共享最多 **8 个读取线程**，包含取消后仍在返回中的读取。单任务窗口不会突破配置上限；该线程池与 `TASK_QUEUE_MAX_CONCURRENT` 的任务槽位是两个不同边界。
- 当前规则规划器通常只有一个检索项和一个计算项，因此启用值 2 即可覆盖该组合。Provider 可声明有界 DAG 与预览标量绑定；外部读取需要另外明确配置只读资格，写入工具仍串行。

### SSE、Trace 与最终回答

工具尝试复用既有 `tool_start` / `tool_end` / `state` / `error` 事件。不同工具的事件可能交错，同一 step 的尝试顺序不变；前端应按 step_id 合并状态，不假设同一时间只存在一个运行工具。

工作线程只生成事件与结果，不写 tasks、Trace、审计或消息。协调线程在窗口结束后按原计划顺序合并结果，重排 action/RAG follow-up 的 seq，再依次执行既有持久化动作与汇总最终回答输入。工具完成顺序不会改变最终观察顺序，Trace/delta 游标保持递增。

并发 action 的 `Trace.meta` 新增兼容的可选字段：

| 字段 | 含义 |
| --- | --- |
| `execution_mode` | 当前为 `parallel`；串行步骤不增加该字段 |
| `parallel_group_id` | 本次并发窗口的随机标识，与来源任务/会话无关 |
| `parallel_group_size` | 本窗口工具数量 |

既有 Trace.meta 允许扩展字段；JSON v1.0 和 Markdown 导出沿用原有结构及脱敏策略。没有新增接口或修改 OpenAPI 操作/组件指纹，当前为 51 操作 / 89 组件。

### 取消、超时与失败

协调线程等待结果时每 50ms 检查生命周期（数据库状态沿用既有 250ms 探测节流），刷新执行 heartbeat，空闲等待期间继续发送 SSE heartbeat。取消或超时后停止消费结果、取消未启动 future 并释放任务槽位，不等待正在进行的读取返回。

已进入底层读取的调用不能被 Python 线程强制中断；它们占用共享线程直至返回。返回后不得发布事件、持久化 Trace 或触发最终回答。窗口尚未合并时取消，其成功读取也可能不进入持久化 Trace；已发送的 tool_end 不能视为任务完成。该模式仅允许上述内建读取/纯计算和明确配置的 HTTP 读取，不承诺外部副作用回滚。

- 可重试失败只重试该工具，已成功的兄弟工具不重复运行。
- fatal 工具失败中止窗口，保留已接收结果及失败 Trace，写失败终态并阻止最终回答；取消其他未启动读取，丢弃迟到结果。
- 未知工作线程异常交回协调线程，沿用任务流失败处理；不会静默视为成功。
- 默认关闭时仍走既有串行执行/重试/服务动作语义，可通过将配置改回 1 回退。


## HTTP 只读并发

配置的 `http_json` 工具可显式声明只读并加入任务内有界并发。需要同时设置服务端 `TASK_TOOL_MAX_CONCURRENT=2`（或 3/4）和该工具的 `execution.parallel_read_only=true`。两者默认都不启用 HTTP 并发；现有未声明工具继续串行。

### 配置示例

以下内容放入已有 `INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON`，或采用已有 overrides/source/profile 配置入口；没有新增用户设置字段或 HTTP 接口。

```json
{
  "catalog_search": {
    "template": "task_retrieve",
    "label": "Catalog Search",
    "execution": {
      "kind": "http_json",
      "url": "https://example.com/search",
      "method": "GET",
      "parallel_read_only": true,
      "query_params": {"q": "$query"},
      "timeout_ms": 3000,
      "result_fields": {"documents_total": "total", "chunks": "items"}
    },
    "result_preview_keys": ["documents_total", "chunks"],
    "result_output_keys": ["documents_total", "chunks"]
  }
}
```

URL 是配置占位示例；使用真实、已确认无写入副作用的读取端点。声明代表配置者确认该端点和所传参数只进行读取；GET 方法本身不能证明服务端无副作用。写入/变更型 GET 不应声明只读。

### 资格与边界

- `parallel_read_only` 必须为 JSON 布尔值；true 仅允许固定的字面量 GET（也可省略 method，由无请求体推导 GET），不得定义非 null `json_body`。
- true 配合 POST/PUT/PATCH/DELETE、HEAD、动态 method 模板或请求体，会进入既有配置诊断/预检失败路径，阻止网络调用。false/未设置沿用既有方法和模板校验。
- 资格由 HTTP 工厂绑定到实际创建的 runner 身份。名称、kind、展示 summary、调用函数自定义属性或替换后的自定义 runner 都不能赋予资格。
- 创建 runner 时深拷贝完整请求 spec 和 runtime 模板上下文；后续修改原始字典、headers、URL、凭据或上下文不会改变已分类的请求。窗口内 registry 沿用已有固定快照。
- 内建读取和符合条件的 HTTP 读取可在同一个窗口并发；未声明 HTTP、自定义 runner、规划和未解析依赖提示仍为串行屏障。[显式依赖计划](tool-execution.md#依赖与结果绑定)先校验/解析结果绑定，只调度同波已就绪工具。
- 单任务每个窗口仍最多并发 1–4 个工具，进程共享最多 8 个读取线程；该上限包含取消后尚未返回的 HTTP 读取。每个请求继续使用自己的 timeout 和既有重试规则。

### 任务流、权限与结果

HTTP header/query/body 模板仍使用本次实际用户上下文，来源配置和用户设置沿用既有规则；并发不增加权限。工作线程只生成事件与结果，Trace、审计、任务终态和消息由协调线程写入。可重试 HTTP 失败只重试失败项，成功兄弟不重放。

协调线程在取消/超时后停止消费窗口，不等待已发出的请求；底层 HTTP 请求不能强制中断，会占用读取线程直到返回或请求超时。迟到事件、结果与依赖节点不得继续写入或启动。该行为不能撤销远端副作用。

沿用 `tool_start/tool_end/state/error`、Trace.meta 并发分组、拓扑节点字段和 JSON v1.0/Markdown 结构。execution_summary 仅新增可选布尔 `parallel_read_only`；它表示配置声明，实际是否并发仍看 action 的 `execution_mode`。URL、认证头与返回内容继续经既有投影/脱敏，原始密钥不进入 Trace/导出。OpenAPI 当前为 51 操作 / 89 组件。


## 实现与验证

`tool_plan_dependencies.py` 负责图与绑定；`task_tool_execution.py` / `task_tool_parallel.py` 负责调度和合并；`tool_http_parallel_policy.py` 与 HTTP 工厂负责读取资格。文件均在 `backend/app/services/`，兼容入口仍是 tool_runtime facade。

| 静态 selector | 隔离集成文件（backend/scripts/） | 历史专项范围 |
| --- | --- | --- |
| `tool_dependency` | `test_tool_dependencies_postgres.py` | 静态26、PostgreSQL7；图、输入边界、绑定、审计与生命周期 |
| `task_parallel` | `test_task_parallel_postgres.py` | 静态15、PostgreSQL6；重叠、屏障、稳定合并、线程上限 |
| `http_parallel` | `test_http_parallel_postgres.py` | 静态15、本机HTTP/PostgreSQL7；快照、503重试、模板、脱敏、取消 |

静态使用 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k <selector>`；集成按[开发手册](development-runbook.md#隔离专项入口)，已纳入 backend-e2e，独立数据与模型替身自动清理，不计作本轮重跑。真实端点只读性、供应商规划质量、限流和延迟另验；写入并行、HTTP/DAG checkpoint 仍延期。
