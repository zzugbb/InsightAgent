# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（根目录 `.nvmrc`、`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端镜像一致）。

## 当前状态

- W1-W4 主链路已完成并收口：Auth Gate、Workbench、Trace 双视图、Memory / RAG 调试、usage 展示、任务与会话导出、任务详情页、running task 恢复等已具备可演示闭环。
- 当前前端主线已从“配合 runtime spec 内部收口”转向“真实工具语义在工作台中的稳定呈现”，重点跟随后端推进：
  - extra/real tool 的 display label、preview/output/result-summary 语义
  - retrieval follow-up 与 tool-registry diagnostics 展示
  - model settings 中 provider/source diagnostics 与 selected source 说明
  - 真实工具输入、计划项与最终 trace/export 回放的一致性
- 最近已对齐到代码的高信号能力：
  - `tool_end.result_summary`、preview/output key 与安全 observation 已进入流式 store 与回放主链，不再回退泛化 `Tool done: ...` 或原始 JSON；当后端只保留 step meta 而未保留原始 `output` 时，也会优先回放 `result_summary` / `output_preview`，并把 preview 继续作为结构化 success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 透传；Memory / RAG 调试返回的 query metadata、query payload root、RAG ingest 文档行、RAG route 列表/命中行、shared merge 结果、session create/detail/list/messages/export、task/session usage、task detail/list/trace/export/stream-reconnect、auth/audit 列表相关 outward summary，以及由 `chat_persistence_service` 直接产出的 task summary/export/trace 批量聚合结果、task/session export response summary 与 export builder 路由入口，现在也不会再因后端 typed payload 被归一化成空对象或直接报错。
  - trace display/search 已能消费 `meta.tool_registry.entries`；model settings modal 已消费 `diagnostics_summary`，broken file-backed source 不会直接从设置里消失。
  - 后端 `extra_tools` / `overrides` 已可绑定 `execution.kind=http_json` 的真实执行器，因此 workbench 对 provider search / provider calc 一类 real tool 的 preview/output/result-summary/observation/export 回放，不再默认假设它们只是本地 template runner 的语义换壳。
  - model settings modal 的 tool detail summary 现会直接显示 `via http_json` 一类 `execution_kind`，前端可以更直观看到某个 provider/source tool 是否已经接到真实执行器。
  - 本轮后端继续补齐 `http_json` 成功 payload、RAG follow-up chunk、result-summary、HTTP error body preview、runtime error/artifact/observation summary、半迁移 provider/hosted trace display/export、session JSON trace_preview response/route coercion、task JSON `trace.steps[]` / 顶层 `rag_chunks` response/route coercion、display/markdown meta 的 `result_summary` 与嵌套 `meta.rag.chunks`、半迁移 provider/hosted `output_preview`/`output` 门控拓宽，以及 mock final-answer structured/generic fallback 的 raw text 脱敏；前端工作台、trace、JSON/Markdown 导出回放与 mock final answer 不会因 generic value/chunk/summary/error/input/content/excerpt/`result_summary` fallback 看到 `query_params.access_token`、`response_path.data.access_token`、`response_path=$.data.access_token`、`response_path=$['data']['access_token']`、`response_path=$.data['access_token']`、完整 URL 与嵌套 URL 参数/路径/fragment 值中的敏感 query / fragment / userinfo / path segment、成功 payload / raw fallback dict key 中的 diagnostic JSONPath/URL、半迁移 execution_summary `url_path` 里的嵌套 URL 与相对 query/fragment、`http_json` registry label/display name 与显式 `display_name` 后续事件里的 diagnostic URL/assignment、session export `trace_preview.title` 里的 `via http_json` diagnostic label、chat persistence task trace preview 与 parsed `trace_json.meta.tool.label` 里的 diagnostic label、`build_tool_step_output`、`build_tool_trace_event`、stream effects、attempt/retry loop 聚合结果及其 success/postprocess `rag_followup.step/trace`、plan item result success bundle trace/rag_followup、runtime artifacts / service action model 边界里的 wrapper `step+trace` 递归清洗、configured provider runtime service action model execution，以及 direct service action executor / service effects execution 里的 raw output/output_preview、display helper、task response parsed `trace_json` 与 session export response/route 中非 provider/hosted 标题的 `via http_json` trace/preview URL、`client_secret` 类 compound key 或 bare bearer 片段；后端也会在读完 HTTPError 错误响应体后关闭响应 wrapper，避免测试或运行时留下 ResourceWarning。
  - 当后端显式配置了无效 `execution` 时，当前策略是 fail-fast 而不是静默回退 stub runner；前端后续看到的是明确的配置错误，而不是“看似成功、实际跑了本地模板”的假语义。
  - 同时，provider/source diagnostics 现在也会把这类静态可判定的坏配置提前归一成 `invalid/tool_executions` 项；设置面板不需要等任务真跑起来，source diagnostics 就能先提示 real tool 的执行器配置已经坏掉。后端在 diagnostics summary、runtime trace/audit detail、旧 trace display 回放、configured provider runtime artifacts 的 raw diagnostics dict、`diagnostics_runtime.summary/trace/audit`、`audit_event`、service action `trace_step/trace_event/kwargs` 边界、direct tool-plan service action executor，以及 tool-plan step error update、attempt result/outcome、terminal-failure、plan-item result、attempt-retry loop、stream、terminal、next-action、service-actions、effects、execution 构建结果与 `loop_execution_result` 附加点都会清洗敏感 assignment 和字段路径，因此前端不会因为展示配置错误而看到 `api_key=...`、`token=...`、`query_params.access_token` 或 `result_fields['access_token']` 这类原文。
  - 对 `http_json.execution.method` / `timeout_ms` / `default_timeout_ms` 这类真实请求协议字段，后端现在也会提前治理：拼错 method 不再静默变成 `GET`，显式 `GET + json_body` 不再静默丢 body，坏 timeout（含 fractional/sub-millisecond、非有限数或超大整数）不再裸抛构建异常，而是作为 per-tool execution diagnostic 进入设置/回放链路，前端看到的是明确配置错误。
  - 后端对 `http_json` real tool 新增的安全 `execution_summary` 也会随 tool meta 进入 SSE/trace/export 主链；即使前端当前还没单独做专门 UI，这份 method/origin/path/query-body/result-field 概览已经会稳定跟着工作台回放语义走。后端还会在 extra tool / override 构造和运行态出口对半迁移 registration 里已有的 `execution_summary` 再做一次安全化，前端不会因 live tool meta 或 preflight tool details 看到旧摘要里的敏感 path/key。
  - 后端现在还支持 `http_json` 执行模板读取运行时 `settings_api_key/settings_base_url/tool_registry_provider_source` 上下文，并在 `headers/url/query/json_body` 中使用 `${...}` 做安全字符串插值；可由 settings/source 上下文渲染出的 URL endpoint 会进入安全 `execution_summary` 与 diagnostics，前端不会把 secret 模板值直接带进设置面板或 trace UI。
  - 即使 provider/source 改成 file-backed registry manifest，后端也会继续把同一套 source 级模板上下文灌进 `extra_tools/overrides`；因此前端看到的 source diagnostics、tool detail summary 与运行态 trace 语义不会再因配置承载形态不同而分叉。
  - 对 `http_json` 模板里拼错的 `settings_*` / `tool_registry_*` 运行时变量，后端现在会更早在 source diagnostics 中给出 `invalid/tool_executions` 提示；前端不必等真实 tool 执行到上游请求阶段，设置治理面就能先看出是模板变量 typo，而不是网络/权限波动。
  - 对 URL、header/query value shape、请求 JSON header、`json_body` 严格 JSON 与 response mapping path，后端也会给出更明确的配置诊断：相对 URL、带 userinfo credentials 的 URL、显式端口非法、含原始空格/控制字符或 fragment 的 URL、URL 内联 path/query 里 percent-decoded 后的控制字符、dot-segments、坏参数名或坏值、URL 内联 query 重名或与 `query_params` 同名、静态 settings/source 渲染后才出现的 header CR/LF 或其他控制字符注入、非法 header name、大小写变体重复 header、非 JSON `Content-Type`、非 UTF-8 JSON request charset、缺少 `=` 或值的 `charset`、不接受 JSON 或把 JSON media range 标成 `q=0` / 非法 q 值的 `Accept`、缺少 `=` 或值的 `q`、含 query 结构分隔符的 query 参数名、对象型 header/query、运行时渲染成对象的 query 参数、`json_body` 里的 `NaN` / `Infinity` 或不可序列化对象，以及非法 bracket path 不会再被静默字符串化、延后裸抛或部分解析；请求侧 `Content-Type` / `Accept` 参数也会按 quote-aware 规则解析，quoted profile 里的 `charset` / `q` 不会被误当真实协议参数，未闭合 quoted 参数会在设置诊断或运行时渲染后直接失败，重复 charset 参数必须全部等价于 UTF-8，重复 `q` 参数也必须全部是有效正权重，显式拒绝 JSON 的 `q=0` / 非法 q 也不会被后续 `*/*` 掩盖，因此前端设置面不会再把合法 header profile 误报成非 UTF-8 body，也不会放过冲突 charset、半残 charset、冲突 q、半残 q、未闭合 quote 或 wildcard masking 请求头；前端设置面与运行态 trace 看到的是同一类 real-tool execution 配置错误，敏感 header/path/query 诊断会先脱敏，`execution_summary.url_origin/url_path` 也会按解码后的 path 脱敏，避免半可信 endpoint 或 path 内 token 泄漏。
  - 当 `http_json` 上游返回 HTTP 错误、连接/传输错误、非 2xx 响应对象、2xx 非 JSON 响应、显式非 JSON `Content-Type`、204/空成功体、redirected response URL drift 或非法 UTF-8 响应体时，后端现在会带出稳定的 HTTP status、脱敏限长后的 reason、`transport error`、`invalid JSON response`、`empty JSON response`、`invalid JSON response charset`、`invalid JSON response content-type` 或 redirected response 诊断与有限长度 preview；除 `HTTPError` 外，`status/code/status_code/getcode()` 这类 adapter 响应状态也会在响应映射前被拦截，支持 bytes 与 `503 Service Unavailable` 这类 status-line 形态，且不可解析或越界状态会直接报 `invalid HTTP response status`，前端看到的是明确的上游协议错误，而不是 302/503 被误当成功或变成 response mapping fatal error；response final URL 与 reason/msg 会接收 bytes-like adapter value，URL drift 比对会忽略大小写 host、默认端口、fragment、query 参数顺序、等价 query encoding 与 path unreserved percent-encoding 噪音，但真实 query drift 仍会在映射前 fail-fast 且不泄漏跳转 URL token；2xx/未知状态响应一旦出现 final URL drift，会先于 body read、坏 gzip/deflate 或 unsupported encoding 暴露 redirected response 诊断，前端不会再把登录/网关跳转误看成普通 body/encoding 问题；response body reader 缺失、`read()` / `__enter__` 抛错、body 类型不支持会稳定落成脱敏 `transport error`，且非 2xx 或 invalid status 场景会优先保留 HTTP status/invalid-status 诊断；`Content-Encoding` 支持 `gzip/deflate/identity` 及其安全链式组合，其中 `deflate` 同时兼容 zlib-wrapped 与 raw deflate，会在 JSON 解析前解码，HTTPError 的压缩错误体也会走同一条 preview 链路，HTTPError body read 失败、坏压缩体或暂不支持的 encoding 会保留 status/reason 并带脱敏 preview；2xx 成功响应里的坏压缩体或暂不支持 encoding 也会按上游响应协议错报出，不再混成 `transport error`；非 2xx 响应对象即使 body 压缩声明坏掉或读取失败，也会优先保留 HTTP status/reason，并附带安全化的失败 preview；HTTPError、非 2xx/invalid status、显式非 JSON content-type、invalid JSON 与 unsupported encoding 的失败 body preview 现在也会在可用时按响应 `Content-Type` charset 先解码再脱敏，前端 trace/export/workbench 里看到的 UTF-16 等真实上游错误体不再退化成乱码或绕过结构化脱敏；response adapter 的 `status/reason/geturl/getheader/headers/info` 局部回调异常会继续尝试备用来源，不再直接遮掉 HTTP status、redirect 或 content-type/encoding 诊断；response header mapping 会大小写不敏感解析，`getheader(name, default)`、`headers.get(name, default)`、`get_all()`、`getheaders(name)`、bytes-like header name/value、bytes-only `get(...)` candidate、malformed `items()` entry、`raw_items()` / `multi_items()` entry、pair-list headers/info 或 list/tuple header value 会先安全归一或跳过；重复 `Content-Type` / `Content-Encoding` 会按多值 header 合并处理，避免第一值把非 JSON content-type 或 gzip/identity 链式 encoding 吞掉，重复同义 JSON / `+json` content-type 仍可接受；`Content-Type` 的 `application/json` 与 `+json` subtype 会继续接受，quoted/uppercase charset 会按声明解码，quoted 参数里的逗号/分号不会被误拆成 media type 或 charset，但未闭合 quoted 参数会在映射前变成 `invalid JSON response content-type`，缺少 `=` 或值的 charset 参数会变成 `invalid JSON response charset`，前端不会再看到坏 response header 伪装出的成功 tool output；重复同义 charset 会接受，重复冲突 charset 会以 `invalid JSON response charset` 安全失败，未知或敏感 charset 也会脱敏失败；bytes 形态的 `text/html` 网关/登录页即使 body 形似 JSON 也不会再落成成功 tool output；JSON error body 的敏感 key、普通字符串值里的敏感 assignment、HTML/raw text preview、transport reason 与 bytes-like reason 里的 `token/api_key/secret=...` 会连标签和值一起显示为 `[redacted]`。
  - 对 `http_json` 上游错误，后端现在还会把白名单响应 header hint 带到错误文案：`HTTPError`、非 2xx/invalid status、redirected response URL drift、已拿到响应头后的 body reader/read/body type transport error、2xx 响应协议错误（显式非 JSON content-type、invalid JSON、invalid charset / charset decode error、unsupported success content-encoding），以及 response mapping schema drift（`response_path` 缺失、`result_fields` 全部落空）都会让 `Retry-After`、`X-Request-ID`、`X-Correlation-ID`、`X-Amzn-RequestId`、`CF-Ray` 继续脱敏限长后进入 trace/export/workbench，帮助前端排查限流、网关与上游工单关联；`Location` 这类可能携带 token 的 header 不会展示，bearer-like、带空白或过长的 request-id 类 header 也不会作为安全 request id 展示。
  - 对那些只有任务执行时才知道会不会缺失的 `$top_k`、`$precision` 一类模板输入，后端现在也会在真正发请求前直接报出 `query_params.limit`、`json_body.precision` 这类缺参路径；前端看到的会是明确的运行时模板缺参错误，而不是“请求发出去了但语义残缺”的假成功或假网络问题。
  - 对请求侧 diagnostics 中的敏感字段路径与模板变量名，后端现在也会先脱敏再交给前端：`query_params.api_key`、`json_body.access_token`、嵌套的 `client_secret` 路径，以及 `runtime_access_token` / `tool_registry_api_key_typo` 一类变量名会显示成 `[redacted]`，settings 面板、tool_start、trace subtitle/search 与导出回放都不会因为错误定位而显示敏感字段名。
  - 对 `execution.kind` 这类执行协议枚举的坏配置，后端也会先做敏感值脱敏；如果 provider/source 把 kind 误写成 `token=...` / `api_key=...` 一类字符串，前端设置面、tool_start、trace 与导出回放只会看到 `[redacted]`。
  - 对 `headers/query_params/json_body` 里只有空白字段名这类原本会被请求构建过程静默吞掉的配置，后端现在也会在 settings/source diagnostics 与 preflight 阶段提前报出 `invalid_tool_executions`；前端设置治理面可以更早指出“请求模板字段名本身就坏了”。
  - 对显式配置了 `response_path` 的 real tool，如果后端在真实响应里找不到这条路径，或者配置本身只是空白字符串，现在也会直接报配置/协议错误，并对错误里的 path 做敏感 assignment 脱敏，同时附带安全且限长的上游 payload shape / available response keys 摘要与白名单 header hint，而不是静默退回根 payload；前端看到的会是明确且安全化的响应映射失败，而不是 trace/export 中混入根响应兜底后的假结果。
  - 对显式配置了 `result_fields` 的 real tool，如果所有字段映射都没命中，后端现在也会直接报出有限数量的映射失败摘要，并补充脱敏后的可用响应 key / payload 类型提示与白名单 header hint；如果 scoped payload 是数组，还会带出首项对象 key 摘要，而不是返回空结果对象、超长 mapping 列表或超长 key 摘要；前端看到的会是明确的 response mapping 错误，不再需要从“运行成功但没有任何 preview/output”这种假信号里倒推问题。
  - 对 `http_json` 成功返回的真实上游 payload，后端现在也会在进入 preview/output/observation/export 前脱敏敏感 key 与字符串 assignment；即使 registry 没显式写 `result_fields`，前端也不会直接回放上游根 payload 或 scoped payload 里的 `secret/token/api_key/...` 原文。真实搜索上游如果只映射出 `items`、`results` 或 `matches` 列表，后端也会分别补出 `documents_total` / `hit_count`；如果 `documents/results` 等同义字段只是元数据对象，或显式 count 字段是不可用值，不会挡住后续真实列表计数；字符串数字、整型小数字符串或整型浮点形式的计数字段也会归一成非负整数。这套归一化已经下沉到 helper 投影，且 helper 会先规范化半迁移 registration 的 `execution_kind` 再决定是否走 `http_json` 安全 output shape；无 registry 的 step meta 回放层、markdown meta safe-output / preview fallback、task/session JSON export 的 `steps[].content`、trace delta snapshot、TaskResponse `trace_json` outward summary，以及 task/session markdown 旧 real-retrieval preview 的显式 `Preview:` / `Output:` 与 `trace_preview.content_excerpt` 字符串回放也会继续复用这条链路，让前端 trace/export 回放继续拿到可用于 preview、summary 与 observation 的数量字段。
  - `http_json` 成功输出现在也会继承安全响应 header request id：真实上游如果只在 `X-Request-ID` / `Request-ID` / `X-Amzn-RequestId` / `CF-Ray` 返回请求关联号，后端会在结构化 output 中补 `request_id`，并继续进入 result summary、observation、trace 与导出回放；疑似敏感、带空白/bearer-like、过长或会被截断的 header/body request id 不会进入 output，敏感 body request_id 也不会压过安全 header。旧 trace/helper 回放里已经落下的 unsafe `request_id` 也会在 summary、observation、markdown meta、display content 与 mock final-answer observation summary / generic payload summary 前被移除；helper 级 result output/preview/summary、tool observation generic fallback、`normalize_tool_output_for_registration(...)` 的半迁移 raw output 兜底、RAG follow-up chunks、`build_tool_error_meta/payload(...)` 的 raw error message 兜底、success meta raw `last_error` 兜底、generic `error` SSE event / retry transition / terminal failure message 兜底、chat persistence raw `http_json` preview/output 回放、task/session JSON export step meta、session export 泛化 provider/hosted trace preview fallback，以及 mock final-answer 泛化 structured/text output summary 与 Tool context fallback 也会复用安全 output shape / 敏感字段过滤，前端不会再看到 `request id Bearer ...`、`access_token` 明文、`token=hidden` 这类历史摘要/最终回答/导出文案，或 task_failed/failure event 里的 raw upstream error assignment。
  - 后端现在还会对 `http_json` 的可见 `tool.input` 做展示层脱敏：`tool_start`、action step meta、success/error meta，以及 task/session JSON export 与 markdown meta 回放里的旧 `tool.input` 进入工作台 trace、JSON export 或会话回放前会清洗敏感 key 与字符串 assignment；真实执行输入仍不变，因此前端不会因为后端隐藏 `Authorization` / `access_token` 而看到真实请求模板执行语义被改写。
  - 对 `execution_summary.result_field_names` / `response_path` 与显式 `result_preview_keys` / `result_output_keys` 这类结果元数据，后端现在也会过滤或脱敏敏感字段名、assignment 与 path segment；如果 provider/source 显式只声明了 `access_token` / `api_key` 一类敏感输出 key，或 `result_fields.access_token` / `$.meta.api_key` 映射配置出错，前端设置面、tool_start、trace 与导出回放也不会再因摘要、诊断或模板默认投影回退而重新显示这些字段名。
  - 对 `result_fields.*` 里静态就能看出的坏 path，后端现在也会在 settings/source diagnostics 与 preflight 阶段提前报出 `invalid_tool_executions`；像 path 本身坏掉、`result_fields` 里混入空白字段名、只有空白字段名，或显式给了空对象这类问题，前端设置治理面都能更早指出，而不是只在任务失败后回放运行态错误。
  - workbench trace subtitle 与搜索现在会直接消费 `execution_summary`；真实工具运行中的 `POST https://.../search`、response path、result fields 等安全摘要已经能在前端回放和检索里直接看到。
  - model settings modal 的 tool detail summary 现在也会直接显示 `execution_summary` 的 endpoint 与 query/body/response-field 摘要；provider/source 治理面不需要进入运行态 trace，就能先看出某个 `http_json` real tool 会打到什么路径、响应会映射到哪些字段。
  - model settings modal 的 tool detail summary 现在也会继续拼出 per-tool `execution_diagnostics`；source diagnostics 不再只告诉你“这个 source 有坏配置”，而是能直接看出具体是哪个 real tool 的 `http_json` 配置出错。后端合并 per-tool diagnostics 时也会先脱敏，前端设置面板不会因为详情展开而重新看到 `api_key=...`、`token=...` 或 `query_params.access_token` 这类原文。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续进入运行态 tool meta、live store 与 trace subtitle/search；如果坏掉的 real tool 真被规划并执行到，前端不需要只看泛化 error message，就能直接看到是哪条执行配置坏了。后端在 registry 构造和写入 live runtime meta 前都会脱敏半迁移 diagnostics，避免 settings 面已安全但 SSE/trace 又露出 `token=...` 或敏感字段路径。
  - 对 retrieval family 的 `http_json` real tool，后端现在也会从 `documents`、`items`、`results`、`hits` 或 `matches` 列表自动提炼 `snippet/content/text/excerpt/summary/description/body/...` snippets，并能受控解析 `metadata/document/payload/chunk/node/...` 多层嵌套对象；如果 `documents` 只有 id/title 元数据，也会继续降级查看后续别名列表，不再要求上游额外伪造本地 stub 风格的 `chunks`，前端看到的 rag follow-up / trace 回放会因此更接近真实检索响应语义。
  - 对 docs-only 的 real retrieval 结果，后端现在也会把 `documents_total` 纳入默认 preview/output key 推断；前端在 `tool_end` 预览、trace/export 回放里不再只看到空 preview 或退化文案，而是能继续看到文档数量级摘要。对显式映射 `items` / `results` / `matches` 的 `http_json` 搜索工具，后端也会把这些常见列表别名转成可投影的数量字段，并继续从列表项里提炼 snippets，避免真实 provider 响应字段名不是 `documents/hits` 时前端摘要链或 RAG follow-up 断掉。
  - 对 docs-only 的真实 provider 检索结果，如果 `documents_total` 同时带有 `knowledge_base_id`，后端返回给前端的 result summary、observation、session export markdown 与 mock final answer 会显示 provider KB 来源（例如 `from hosted-kb`），但不会把 provider/source KB 误描述成本地默认知识库；只有 `Hosted Search` / `Provider Search` label、没有显式 semantic meta 的旧 trace / Tool observations 回放也会保持同一文案。
  - 同一路 docs-only retrieval fallback 现在还会保留默认 output 里的 `request_id`；前端在 result summary、observation 与导出回放里可以继续看到真实 provider 请求关联号，而不必依赖工具显式补 `result_output_keys`。
  - 对 `hit_count` 风格的 real/provider retrieval，后端现在也会把 `request_id` 带进 result summary 与 observation；前端在工作台、trace 与导出回放里不会再看到“结构化 output 有请求关联号，但摘要文案没有”的分叉。
  - 对 `http_json` real/provider calc，后端现在也会在默认 output projection 中保留 `request_id`，并把只有 `result/request_id` 的返回转成 `Calculated result = ... (request id ...)`；前端工作台、trace 与导出回放不再只看到 generic payload 文案。
  - mock final answer / 回放链路现在也会沿这套 `request_id` 语义输出 retrieval hit summary 与 real calc summary；前端看到的最终回答、trace 摘要与导出文案更一致。
  - 对旧 trace / typed payload 那些没有显式 `result_summary`、但仍保留了 safe output 的 real tool step，工作台、trace 与导出回放现在也会直接推断出 `Retrieved ...` / `Calculated result = ...` 摘要，而不是继续停留在 `Tool done: ...` 加 JSON。
  - 同一条 fallback 现在也已经落到 task/session preview 摘要展示；前端看到的 trace preview、session export preview 与 workbench 主回放会尽量使用推断后的结果摘要，而不是继续把 `Tool done: ...` 当作旧数据的主文案。
  - 这条 fallback 现在也覆盖只有 `output_preview` 的旧 tool step；即使历史 payload 把 `output_preview` 存成 JSON 字符串，前端 workbench、task trace preview、tool observation 与 task export markdown 回放在 planner/retrieval/calc 的 preview-only 场景下，也会先恢复可解析结构化 preview，并优先显示 `Planned steps - ...` / `Retrieved ...` / `Calculated result = ...` 摘要，而不是保留 `Tool done: ...`。
  - 前端 workbench 的 preview-only 回放现在也会恢复合法双层 JSON 字符串形态的 `output_preview`；`"{\"result\":7,...}"` 会先变回结构化对象，再用于摘要推断和 `Preview:` 展示，避免 quoted JSON 直接出现在 UI。
  - 后端 trace display helper 的 `Preview:` 行也已补齐同类恢复；因此前端消费后端 task/session preview 或 export helper 文案时，不会再看到“摘要正确、preview 仍是 quoted JSON”的分叉。
  - 同一条 safe-output fallback 现在也继续覆盖 `effective_result_output_keys` 已存在、但 `tool.output` 仍落成 JSON 字符串的半迁移旧 payload；workbench display、标题/语义分类、搜索与 trace preview 回放会先按 output policy 恢复结构化安全 output，再推断 retrieval / calc / planner 摘要，不再直接显示原始 JSON，也不会把被过滤字段重新带回 UI。
  - `chat-stream-store` 的 `tool_end` 合并现在也会对这类 JSON 字符串 `output` 复用同一条 output-policy 裁剪语义；即使 live SSE / reconnect payload 里还残留半迁移字符串结果，store 内的 tool meta 也会先收成安全 output 对象，再交给 workbench display、搜索和 semantic stats，而不会把整段原始 JSON 挂在前端运行态。
  - 同一条前端 safe-output coercion 现在也覆盖合法双层 JSON 字符串形态的 `tool.output`；live store 与 workbench display 会先把 `"{\"result\":7,...}"` 解回对象并按 output policy 裁剪，避免 quoted JSON 或 `secret` 重新出现在运行态与回放文案。
  - 后端 session markdown / preview route 现在也补齐了 quoted JSON fallback；因此前端发起会话导出时，旧 `Output: "{\"result\":7,...}"` 这类双重转义 excerpt 也会被恢复成安全 output 回放，不会再把 `kind/secret` 一类旁路字段带回导出结果。
  - 后端 session markdown direct-label preview 也补齐同类恢复；因此前端发起会话导出时，旧 `Hosted Math: "{\"result\":7,...}"` excerpt 也会被导出成 `Calculated result = ...` 摘要和产品化标题，而不是 quoted JSON。
  - 对更老的非严格外层引号 direct-label excerpt（例如 `Hosted Math: "{"result":7,...}"`），后端导出也会做窄恢复；前端不会再在会话 markdown 导出里看到这类 quoted JSON 原文。
  - task export markdown / markdown meta 这一层现在也已补上同类防回归覆盖；因此前端发起任务导出或消费旧 trace markdown meta 时，JSON-string safe output 也会继续按 output policy 裁成安全字段，`http_json` 显式 `output_preview` 也会先按列表别名归一化与 preview key 投影后再进入 `Preview:` 文案，而不会把旁路字段带回导出结果。
  - 后端 mock final-answer observation parser 现在也会恢复 quoted JSON payload；因此前端看到的最终回答在旧 `Tool observations:` 只剩双层 JSON 字符串或 `"{"result":...}"` excerpt 时，也会继续显示 `Calculated result = ...` 这类摘要，而不是原始 JSON 或旁路字段。
  - 后端 session export markdown builder 现在也会把旧 `trace_preview.content_excerpt` 里的 `Label: {...}` 与 `Tool done: ... Preview: ... Output: ...` 归一成推断摘要，并对 `http_json` real retrieval 的显式 preview/output 片段做列表别名归一化和安全投影；前端发起的会话 markdown 导出和工作台内的 trace/export 回放文案会更一致，也不会把 `secret` 或坏 count 原样带回 `Preview:`。
  - 后端现在还会对无法解析为 JSON 的旧 `http_json` raw `output_preview` / `output` 字符串 fallback 做原始文本脱敏；因此前端消费 observation、trace display、task/session markdown export 时，不会因为 malformed preview 重新看到 `token=...`、敏感字段路径或 bare bearer 片段。
  - mock final-answer 的纯文本 observation fallback 也会清洗敏感字段路径与 bare bearer 片段；前端看到的最终回答不会再因为旧 `Tool observations:` 里只有不可解析文本而回显 `query_params.access_token` 或 `Bearer ...`。
  - 后端 observation helper 现在也会在只剩 safe output / preview output 的 real tool 场景下优先产出结果摘要；前端看到的最终回答、observation 回放与导出文案会更接近工作台主展示链。
  - 当 registry/source 已经取不到、但 step meta 里仍保留 `semantic_family` 与结构化 output 时，后端 observation helper 现在也会继续推断 real tool 摘要；前端工作台、最终回答与导出回放不会因为 registry 缺席而退回 JSON-only observation。
  - 当更老的 real tool step meta 连 `semantic_family` 都已经丢失、但还保留了 `provider_retrieval` / `provider_calc` 这类 structural `kind` 与结构化 safe output 时，后端 observation / final-answer 链也会继续推断 `Retrieved ...` / `Calculated result = ...` 摘要；前端最终看到的回放与最终回答因此更少退回 JSON-only 文案，而 builtin/generic tool 仍保持原先更保守的显示语义。
  - 后端 mock final-answer 现在也会把 name-only 的旧 real/provider retrieval observation 视作更保守的 real tool 语义；前端看到的最终回答不再把 `Provider Search` / `Hosted Search` 这类旧 observation 误写成默认本地 knowledge-base 命中，而 builtin `Knowledge Retrieval` 仍保留本地语义。
  - 后端 mock final-answer 现在也会继续识别旧 observation payload 里的 structural `kind`（例如 `provider_calc`）；因此前端最终看到的最终回答在这类旧 real calc observation 场景下，也会更稳定地保留 `Calculated result = ...` 语义，而不是退回 generic payload output。
  - 对只有 name-only label 的旧 real/provider calc，前端 workbench display 现在也会和后端 final answer / observation / export preview 保持一致：当 step meta、preview，或 registry 中未显式声明语义族但 label 是 `Hosted Math` / `Provider Math` 的真实计算工具只剩 `result + request_id` 时，会优先显示 `Calculated result = ... (request id ...)`，而不是继续停在 `Tool done: ...` 或 generic payload 摘要。
  - 对 registry/source 中已接 `http_json`、但还没显式声明 `kind/runtime_semantic_kind/result_*_keys` 的 label-only real tools，后端现在也会按 `Hosted Math` / `Hosted Search` / `Hosted Planner` 推断默认 preview/output keys，并在 runtime meta / preflight details 中补出工具名级 `semantic_kind` 与 family 级 `semantic_family`；如果这类 real tool 显式配置了 `result_preview_keys`、但没有配置 `result_output_keys`，后端仍会先过滤半迁移 legacy preview keys 里的敏感字段，再保留安全 preview keys 并按类型补诊断字段（retrieval 补 `knowledge_base_id/request_id`，calc 补 `request_id`，planner 保留 planner preview keys）；如果半迁移对象已经显式带了 `result_output_keys`，effective output keys 也会再次过滤敏感字段名；前端消费到的 workbench trace、preview、observation、settings tool details 与导出回放因此不会因为 source 只配置了 label/name 或只配置 preview/output keys 就出现空 output、generic payload、敏感 `effective_result_preview_keys/effective_result_output_keys` 或语义分类缺失。
  - 后端 session export / trace preview summary 现在也会继续识别旧 preview payload 里的 structural `kind`（例如 `provider_calc`）；因此前端发起 markdown 导出或消费 session trace preview 时，在缺少 `tool_kind` / `semantic_family` 的旧 real calc payload 场景下，也更少看到原始 JSON 回退。
  - 前端 `resolveTraceStepDisplayContent(...)` 现在也会在 safe output 因 output policy 过滤掉 `kind` 之后，继续回看原始 `tool.output` / `tool.output_preview` 里的 structural `kind`；因此工作台 trace 回放遇到只把 `provider_calc` 留在 raw output 的旧 real calc step 时，也会继续显示 `Calculated result = ...`，而不是退回 `Tool done: ...`。
  - 同一层 name-only fallback 现在也继续补到了 semantic filter / semantic stats：当旧 trace 里只剩 `Hosted Search` / `Hosted Math` 这类 real tool label 与 `documents_total` / `result` 输出时，workbench 的 retrieval/calculator 筛选和计数也会继续识别它们，而不是漏成 `other`。
  - 同一层 semantic fallback 现在也继续覆盖 name-only planner 历史 step：当旧 trace 里只剩 `Hosted Planner` / `Provider Planner` 这类 label 与 `plan` / `steps` 输出时，workbench 的 planner 筛选和计数也会继续识别它们，而不是漏成 `other`。
  - 这套派生 semantic category 现在也继续进入 trace subtitle 与搜索：name-only 历史 step 即使没有显式 `semantic_kind` / `semantic_family`，subtitle 也会回退显示 `[planner] / [retrieval] / [calculator]`，而工作台按这些语义词搜索时也不会再漏掉旧 real tool 轨迹。
  - `getStepTitle(...)` 现在也复用了同一套派生 semantic fallback；因此这批 name-only 历史 step 的标题会尽量补成带 `[planner]` / `[retrieval]` / `[calculator]` 的产品化标题，而不再只剩裸 label。
  - 后端 `chat_persistence_service` 现在也把同一套 name-only semantic fallback 补到了 task/session trace preview title；因此前端消费旧 preview/export 数据时，`Hosted Search` / `Hosted Math` / `Hosted Planner` 这类 real tool 历史标题也更稳定地带上 `[retrieval]` / `[calculator]` / `[planner]`，不再只剩裸 label。
  - 后端 session markdown 导出现在也会把旧 `trace_preview.title` 还是裸 label 的历史 payload heading 继续补成同一套产品化标题；因此前端发起会话 markdown 导出时，`Hosted Search` / `Hosted Math` / `Hosted Planner` 与 structural-kind old calc preview 也更稳定地显示 `[retrieval]` / `[calculator]` / `[planner]`，同时不会把 real retrieval 误写成默认本地 knowledge base 命中。
  - 后端 session markdown fallback 现在还会避免把这类仅用于展示的通用 `[retrieval]` 标题反向当成 builtin retrieval 语义；因此前端导出旧 real retrieval 历史 payload 时，即使 title 已经产品化，markdown 摘要也不会被误写成 `from knowledge base ...`。
  - 后端 observation / mock final-answer 现在也会忽略产品化 label 中仅用于展示的 bracket descriptor；因此前端最终看到的旧 real calc observation，即使 label 已变成 `Hosted Math [calculator]` 且 canonical name 已丢，也会更稳定地保留 `Calculated result = ... (request id ...)` 语义，而不是退回 JSON-only 文案。
  - 前端 `normalizeTraceToolLabel(...)` 现在也会忽略这类仅用于展示的 bracket descriptor；因此旧 history step 即使 label 已被产品化成 `Provider Search [retrieval]` / `Hosted Math [calculator]`，workbench 的结果摘要推断、semantic filter、search 与 stats 也会继续识别出 retrieval / calculator 语义，而不是退回 `Tool done: ...` 或漏成 `other`。
  - 后端 provider branch 现在也会在解析 planner 输出的 extra-tool label 前剥掉同一层 bracket descriptor；因此前端后续看到的 productized planner 输出如果回传成 `Fast Calculator [calculator]` 这类 label，后端也会继续稳定命中真实 registry tool，而不会因为 label 已产品化就丢回 `task_plan`-only 路径。
  - 后端 `task_plan` 自己现在也会在消费历史 `planned_tool_names` 时剥掉同一层 bracket descriptor；因此前端回放旧 planner payload 时，即使计划工具名已经被产品化成 `calc_eval [calculator]`，trace/export 里的 planner steps 也仍会稳定显示 `Evaluate calculation` / `Retrieve supporting context`，而不是退回 `Run ...`。
  - 后端 governance summary 现在也会在仍保留 canonical tool name 的场景下剥掉 `allowed_tool_labels` 里的同类 bracket descriptor；因此前端工作台、导出回放与治理视图后续看到的 `Calculator Suite [calculator]` 一类旧标签，会更稳定地回落到 canonical label，而不会把展示噪音继续带进治理 UI；如果旧 session summary 里先残留了 label-only 的产品化旧标签、后续 task 才补回 canonical tool name，后端聚合也会把这两份标签收敛成一份 canonical label；而对直接读取 persisted session governance summary 的前端入口，只要 summary 自身已收敛到单一 provider source/profile，后端也会按那条治理上下文给出对应 canonical label，不再误回退到默认 source。
  - 对直接来自 typed payload / `model_dump()` 的 task/session governance，后端现在也会在 task detail/list response、task/session export route builder、task export/response、session export/response 内嵌 task trace governance 与 usage dashboard response/route 上继续做同一层 canonical label 归一化；即使外层 response summary 已是 dict、但内层 governance 仍是 typed/model_dump 的半迁移 payload，task/detail/list/usage 与 session export route 里的旧 `calc_eval + calculator_suite` 一类治理也不会再把内部名原样露到工作台、导出回放或 usage 面板，而会稳定显示对应 source 的 canonical label，同时不打乱 service dict 信任边界。
  - 同一条保守语义现在也继续落到前端旧 trace display / session export preview 回放：当旧 step meta 或 preview 里只剩 `hit_count + knowledge_base_id + request_id`，且 label 只是 `Provider Search` / `Hosted Search` 这类 real retrieval 名称时，workbench 不会再误补 `from knowledge base ...`，也不会因为缺 registration/semantic family 退回 JSON-only 文案。
  - 后端 runtime semantic 现在还会对未显式补 `runtime_semantic_kind` 的 noncanonical real tool 保留工具自身名称，并把 retrieval/calc/planner family 留在 `semantic_family`；因此前端后续消费到这类 step meta 时，`Provider Search` 一类 real tool 的标题、observation 与 rag follow-up 会更稳定地保留真实工具语义，而不是塌回 builtin family 名称。
  - 后端对 label-only `http_json` real tool 的显式 result key 策略也继续收口：如果半迁移 preview/output key 列表过滤敏感字段后为空，helper preview/output 与 success meta 会返回空投影，不再回退到默认 safe shape；前端看到的 trace/export 因此不会因为旧配置只声明了 `access_token/api_key/...` 而重新出现默认字段。
  - 后端底层 output normalizer 也不会再为这类 label-only real tool 写入 `tool_kind: null`；前端 trace/effects 继续依赖 `semantic_kind/semantic_family` 展示语义，不会在原始 output 里看到 null kind 噪音。
  - task/session preview excerpt 现在也会尽量保留完整的 `request_id` 与 safe output 片段；前端不会再经常只看到 `req-...` 这种被后端 preview 截断的半残摘要。
  - real/provider retrieval 与 runtime override real tool 的 follow-up、result summary、observation、导出回放已不再误写成本地默认知识库命中。
  - extra/real tool 的注册语义、safe output 与计划项输入会优先沿 configured registry 继承；后端 provider planner 与真实 remote provider 现在也共用一套 response text / usage 提取语义，能稳定消费 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 usage alias、脏 usage 值与流式 delta 文本字段变体；task/session export route builder 也会在 plain dict summary 内继续浅归一化内层 `messages`、task `trace_preview`、task trace `rag_chunks/steps` 的 `model_dump()` 对象，因此前端发起 JSON/Markdown 导出或回放半迁移历史 payload 时，不会因为最后一层 response model 只接受 dict 而中断。
  - 后端 mock final-answer observation parser 现在也会恢复 payload 内层 `safe_output` / `output` / `output_preview` / `result_preview` JSON 字符串；因此前端最终回答在旧 observation 只剩嵌套 preview 时，也会继续显示 real calc / real retrieval 摘要，而不是 `output_preview=...` 或旁路字段。
- 当前最近一次已记录校验基线：
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`1356/1356`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`68/68`）
  - `cd frontend && npm run build` 通过
  - `cd frontend && npx playwright test e2e/usage-dashboard.spec.ts -g "task detail replay preserves retrieval_only registry trace metadata" --reporter=line` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-edge-cases.spec.ts -g "cancel allows immediate resend with identical prompt without dedupe loss" --reporter=line` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-edge-cases.spec.ts -g "cancel allows immediate resend with identical prompt without dedupe loss|mock cancel does not show retry affordance and send recovers quickly|trace delta sync retries, pauses in background, and resumes when foreground returns" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`9/9`）
  - `cd frontend && npx playwright test e2e/workbench-remote-errors.spec.ts -g "remote cancel enters cooldown and recovers send" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-main-path.spec.ts -g "workbench main path covers trace, rag and task/session export" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test --project=chromium --reporter=line --workers=1` 通过（完整 Chromium e2e，`47/47`）
  - `git diff --check` 通过

## 全仓库审计结论

- 前端当前文档与代码主线一致：workbench / live store / model settings 已承接 `execution_summary`、`execution_diagnostics`、JSON-string safe output、name-only semantic fallback 与 task/session export 回放语义。
- 最近收尾的 display / observation / export fallback 子线已转为回归守护；后续不再优先扩大本地 display fallback，而是跟随后端 `real-tool-execution` 主线验证真实上游工具在 UI 中的配置诊断、运行态 trace、搜索、semantic stats 与导出回放。
- 下一阶段前端重点是让 provider/source real tools 的设置治理面、运行 trace 与导出回放保持同一语义，而不是发散出新的前端专用解释层。

## 当前已有内容

- 三栏工作台：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试，失败后自动回登录
- Workbench：聊天主视图、任务中心抽屉、任务详情页 `/tasks/[taskId]`
- Inspector：Trace 时间线 / 流程图双视图、Context 概览、同步诊断、当前任务
- 流式链路：SSE 状态、token 追加、trace 实时更新、`trace/delta` 自动静默轮询与结束补拉
- running task 恢复：刷新页面或切回会话时自动接管 `pending/running` 任务流
- 导出：任务与会话 JSON / Markdown 导出
- 模型设置：`mock / remote` 模式切换、校验、保存、错误码友好提示、provider/source diagnostics 说明
- RAG / Memory 调试：设置中的运行调试子页
- 知识库治理：列表、来源采样、shared 权限显隐、清空/删除
- 审计日志：筛选、分页、详情、导出
- usage dashboard：趋势、会话榜、任务榜与来源分布

## 当前运行态重点

- 实时流、持久化 trace 与导出回放当前共用同一套 `TraceStep` 消费主干，前端优先避免派生本地专用语义。
- `tool_end.result_summary`、preview/output key、retrieval follow-up 与 registry diagnostics 已进入工作台主展示链，当前重点是继续跟随后端消除 helper fallback 漏洞。
- running task recovery、remote cancel、model settings diagnostics 与知识库治理 shared 权限是当前最容易回归的前端运行态重点。
- 当前前端回归重点仍围绕 workbench 主链、remote errors、settings、usage dashboard 与 common tooling。

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、会话导出入口与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：模型设置、审计、用量统计、知识库治理与当前用户信息入口
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/usage-dashboard-modal.tsx`：用量仪表盘
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx`：审计日志筛选、分页、展开与导出
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库治理
- `app/components/workbench/runtime-debug-modal.tsx`：Memory / RAG 调试
- `app/tasks/[taskId]/page.tsx`：任务详情页与任务导出入口
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/stores/chat-stream-store-utils.ts`：tool_end / tool meta 合并、preview/output/result-summary 归一化
- `app/components/workbench/utils.ts`：trace display、tool result preview、follow-up 展示与搜索辅助
- `app/components/workbench/model-settings-modal-utils.ts`：settings 预览、provider/source/tool registry diagnostics 说明
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期
- `lib/types/trace.ts`：前端 TraceStep 类型

## SSE 消费与契约对齐

当前前端按以下事件消费：

- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `cancelled`
- `timeout`
- `done`
- `error`

对齐规则：

- `trace` 事件中的 `step` 与后端 REST `TraceStep` 同构。
- `tool_start/tool_end` 会先驱动 action 节点状态，再由 `trace` 事件补齐持久化快照。
- Workbench 会定时静默拉取 `trace/delta`，失败时退避重试，并在流结束后自动补拉一次。
- 同步健康度会在 Inspector Context 区域展示，便于定位网络抖动或增量拉取异常。

## Memory（会话级）

- collection 规则：`memory_{session_id}`
- 状态读取：`GET /api/sessions/{session_id}/memory/status`
- 写入调试：`POST /api/sessions/{session_id}/memory/add`
- 检索调试：`POST /api/sessions/{session_id}/memory/query`

## RAG（知识库）

- 状态：`GET /api/rag/status?knowledge_base_id=...`
- 写入：`POST /api/rag/ingest`
- 检索：`POST /api/rag/query`
- 默认知识库 ID：`default`
- 实际 collection：`kb_{user_hash}_{knowledge_base_id}`

## PostgreSQL / Memory / RAG 怎么看（前端通俗版）

- `PostgreSQL`：完整历史，支撑会话、消息、任务、trace、usage、导出。
- `Memory`：当前会话便签，适合放“本次对话临时约束和结论”。
- `RAG`：外部知识库，适合放手册、FAQ、产品文档。

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

说明：

- `npm run dev` / `npm run start` 固定监听 `127.0.0.1:3001`
- 默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端；未设置时使用 `http://127.0.0.1:8000`

前端 e2e 常用命令：

```bash
npm run test:e2e
npm run test:e2e:smoke:matrix
```

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

## 当前约束

- 当前前端优先保持与后端 SSE / trace / export 契约稳定对齐，不主动发散出新的本地语义分支。
- 下一阶段优先跟进真实工具执行本体接入后的 settings/preflight/runtime trace/display/export 一致性，不优先继续扩张旧 payload fallback。
- 文档只保留当前能力、当前主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
