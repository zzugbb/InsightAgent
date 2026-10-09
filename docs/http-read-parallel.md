# HTTP 读取工具并发

配置的 `http_json` 工具可显式声明只读并加入任务内有界并发。需要同时设置服务端 `TASK_TOOL_MAX_CONCURRENT=2`（或 3/4）和该工具的 `execution.parallel_read_only=true`。两者默认都不启用 HTTP 并发；现有未声明工具继续串行。

## 配置示例

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

## 资格与边界

- `parallel_read_only` 必须为 JSON 布尔值；true 仅允许固定的字面量 GET（也可省略 method，由无请求体推导 GET），不得定义非 null `json_body`。
- true 配合 POST/PUT/PATCH/DELETE、HEAD、动态 method 模板或请求体，会进入既有配置诊断/预检失败路径，阻止网络调用。false/未设置沿用既有方法和模板校验。
- 资格由 HTTP 工厂绑定到实际创建的 runner 身份。名称、kind、展示 summary、调用函数自定义属性或替换后的自定义 runner 都不能赋予资格。
- 创建 runner 时深拷贝完整请求 spec 和 runtime 模板上下文；后续修改原始字典、headers、URL、凭据或上下文不会改变已分类的请求。窗口内 registry 沿用已有固定快照。
- 内建读取和符合条件的 HTTP 读取可在同一个窗口并发；未声明 HTTP、自定义 runner、规划和未解析依赖提示仍为串行屏障。[显式依赖计划](tool-dependencies.md)先校验/解析结果绑定，只调度同波已就绪工具。
- 单任务每个窗口仍最多并发 1–4 个工具，进程共享最多 8 个读取线程；该上限包含取消后尚未返回的 HTTP 读取。每个请求继续使用自己的 timeout 和既有重试规则。

## 任务流、权限与结果

HTTP header/query/body 模板仍使用本次实际用户上下文，来源配置和用户设置沿用既有规则；并发不增加权限。工作线程只生成事件与结果，Trace、审计、任务终态和消息由协调线程写入。可重试 HTTP 失败只重试失败项，成功兄弟不重放。

协调线程在取消/超时后停止消费窗口，不等待已发出的请求；底层 HTTP 请求不能强制中断，会占用读取线程直到返回或请求超时。迟到事件、结果与依赖节点不得继续写入或启动。该行为不能撤销远端副作用。

沿用 `tool_start/tool_end/state/error`、Trace.meta 并发分组、拓扑节点字段和 JSON v1.0/Markdown 结构。execution_summary 仅新增可选布尔 `parallel_read_only`；它表示配置声明，实际是否并发仍看 action 的 `execution_mode`。URL、认证头与返回内容继续经既有投影/脱敏，原始密钥不进入 Trace/导出。OpenAPI 当前为 51 操作 / 89 组件。

## 验证

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k http_parallel
# 需要 Docker/随机本机端口；独立 PostgreSQL + 本机临时 HTTP 服务，不访问真实供应商
backend/.venv/bin/python backend/scripts/test_http_parallel_postgres.py
```

15 个静态专项覆盖资格、非法配置、快照、自定义 runner、内存释放、并发/串行、结果脱敏、重试和依赖绑定；7 个 PostgreSQL 场景以真实本机 HTTP 请求验证重叠、用户模板、Trace/delta/export、503 重试、结果绑定、取消、超时和预检拒绝，已接入 backend-e2e workflow。临时服务和容器自动清理。真实端点的只读性、限流、延迟与目标运行仍待实证；HTTP/DAG checkpoint 恢复和写入工具并行明确延期；[内建顺序计划步骤恢复](task-checkpoints.md)已实现。
