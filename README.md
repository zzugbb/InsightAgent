# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- W1-W4 已完成并收口：会话/任务/消息持久化、SSE 流、Trace 回放与增量同步、Memory、RAG、Token/Cost 展示、基础前后端工作台闭环已可用。
- 当前主线已切到默认工具去 mock 化、真实工具接入，以及 `tool registry / profile / provider source` 治理产品化。
- `tool-runtime-productionization` 已归档，不再把那两份 runtime spec 当作活跃文档维护；当前以代码、三份 README 和本计划文件为准。
- 默认运行策略仍是：配置完整真实 provider/model/api_key 时自动走 `remote`，否则回退 canonical `mock`。
- 最近代码主线已经打通：
  - planner 已能规划 real/extra tools、动态 registry/source 候选，并优先使用 configured registry 语义。
  - provider / provider source 已支持 `loader_factory`；file-backed diagnostics、selected source 与 settings/preflight/artifacts 已对齐到同一治理主干。
  - `extra_tools` / registry `overrides` 已支持声明 `execution.kind=http_json` 的真实执行器，provider/real tool 不再只能复用本地 `task_retrieve` / `calc_eval` stub runner 换壳，HTTP JSON 响应也会继续沿既有 preview/output/result-summary、trace/observation/export 语义产品化。
  - tool-registry preflight、settings summary/validate 与前端 model settings tool details 现已显式暴露 `execution_kind`，可以直接区分“仍是本地 runner”还是“已经挂了 `http_json` 真执行器”的 real tool。
  - 本轮继续补齐 `http_json` 成功 payload、RAG follow-up chunk、result-summary、HTTP error body preview、runtime error/artifact/observation summary、半迁移 provider/hosted trace display/export、session JSON trace_preview response/route coercion、task JSON `trace.steps[]` / 顶层 `rag_chunks` response/route coercion、display/markdown meta 的 `result_summary`、`tool_registry.entries`、`diagnostics_runtime`、`runtime_artifacts`、`service_execution`、`preflight_result`、`execution_result`、`audit_event` 与嵌套 `meta.rag.chunks`、半迁移 provider/hosted `output_preview`/`output` 门控拓宽，以及 mock final-answer structured/generic fallback 的 raw text 脱敏：generic value/chunk/summary/error/input/content/excerpt fallback 会清洗 `query_params.access_token` / `response_path.data.access_token` / `response_path=$.data.access_token` / `response_path=$['data']['access_token']` / `response_path=$.data['access_token']` 一类字段路径、完整 URL 与嵌套 URL 参数/路径/fragment 值中的敏感 query / fragment / userinfo / path segment、成功 payload / raw fallback dict key 中的 diagnostic JSONPath/URL、半迁移 execution_summary `url_path` 里的嵌套 URL 与相对 query/fragment、`http_json` registry label/display name 与显式 `display_name` 后续事件里的 diagnostic URL/assignment、session export `trace_preview.title` 里的 `via http_json` diagnostic label、chat persistence task trace preview 与 parsed `trace_json.meta.tool.label` 里的 diagnostic label、`build_tool_step_output`、`build_tool_trace_event`、stream effects、attempt/retry loop 聚合结果及其 success/postprocess `rag_followup.step/trace`、plan item result success bundle trace/rag_followup、runtime artifacts / service action model 边界里的 wrapper `step+trace` 递归清洗、configured provider runtime service action model execution，以及 direct service action executor / service effects execution 里的 raw output/output_preview、display helper、task response service/route parsed `trace_json`、task trace/delta response route `steps[]`、session messages detail route、task/session export payload/response summary service 与 task/session export route 的 `messages[].content`（含 response-ready BaseModel item）、task export route 的 response-ready `TaskExportTrace.rag_chunks[].content`、session export route 的 response-ready `SessionExportTaskSummary.trace_preview[].content_excerpt`、task markdown builder 直写的 `messages[].content` / `trace.rag_chunks[].content`、session markdown builder 直写的 `messages[].content` / generic `trace_preview.content_excerpt`、settings validate remote preflight `error`、SSE error payload `message/detail`、audit event detail 写入与 audit log list 读取侧、HTTP JSON 上游错误 `RateLimit-*` / `Traceparent` / `X-Trace-ID` 安全 header hint、HTTP response adapter `read()` 空 body 后 `.content/.body/.data/.text` body fallback、仅支持 `read(amt)` 的分块 reader 兼容、只暴露 `json()` parsed body 的 adapter 兼容、只暴露 `iter_bytes()`/`iter_content()`/`iter_text()`/`iter_lines()` streaming body 的 adapter 兼容，以及 session export response/route 中非 provider/hosted 标题的 `via http_json` trace/preview URL、`client_secret` 类 compound key 与 bare bearer 片段；HTTPError 错误响应体读完后也会显式关闭响应 wrapper，完整 backend slice 当前为 `1394/1394`。
  - 显式声明了 `execution` 但 `kind` 缺失、类型错误或写成不支持的执行器时，runtime 现会直接 fail-fast，而不是悄悄退回模板 stub runner。
  - 对 `execution` 的坏配置也不再只能等到运行期才炸出错：file/source/global settings 侧现在会把它们归一成 `invalid/tool_executions` diagnostics，继续沿 selected source、settings summary/validate、configured provider preflight 与 trace/audit 主链提前暴露；diagnostics summary、runtime trace/audit detail、旧 trace display 回放里的 values、configured provider runtime artifacts 的 `selected_source_diagnostics/source_diagnostics`、`diagnostics_runtime.summary/trace/audit`、`audit_event`、service action `trace_step/trace_event/kwargs` raw dict 边界、direct tool-plan service action executor，以及 tool-plan step error update、attempt result/outcome、terminal-failure、plan-item result、attempt-retry loop、stream、terminal、next-action、service-actions、effects、execution 构建结果与 `loop_execution_result` 附加点都会清洗敏感 assignment 和 `query_params.access_token` / `json_body.client_secret` / `result_fields['access_token']` 一类字段路径，避免治理面自身成为泄漏侧路。
  - `http_json.execution.method`、`timeout_ms` 与 tool 级 `default_timeout_ms` 现在也按真实协议配置治理：显式 method 必须是 `GET / POST / PUT / PATCH / DELETE`，显式 `GET + json_body` 会被视为协议配置错而不是静默丢 body，显式 timeout 必须是至少 1ms 的正整数毫秒；拼错不会再静默归一成 `GET`，坏 timeout（含 fractional/sub-millisecond、`NaN` / `Infinity` 这类非有限数或超大整数）不会在 provider 构建时裸抛异常，而会提前进入 `invalid/tool_executions` 并在运行时 fail-fast 或安全回退到模板默认值。
  - `http_json` real tool 的安全执行摘要现也会进入 tool runtime semantic：`tool_start`、action step meta、持久化 trace 与 export 回放可以直接看到 method、origin/path、query/body/result-field 概览，而不会把 header value 或其他敏感配置原样透出；即使 registry registration 里已经带着半迁移 `execution_summary`，extra tool / override 构造、runtime meta 与 preflight details 也会重新清洗 `url_path`、`response_path` 与 `result_field_names` 后再进入 SSE/trace。
  - `http_json` 执行模板现已继续支持运行时上下文与字符串插值：global extra tool、provider source extra tool、registry override、file-backed source 都可以在 `headers/url/query/json_body` 中读取 `settings_api_key`、`settings_base_url`、`tool_registry_provider_source` 等安全上下文，并通过 `${...}` 形式拼接鉴权/header 模板；能由 settings/source 上下文静态渲染的 URL 模板会按渲染后的绝对 endpoint 做 diagnostics 与 `execution_summary`，不用把 secret 明文写进 trace/export。
  - file-backed source 的 registry manifest 现在也和内联 source 配置使用同一套运行时模板语义：manifest 内的 `extra_tools` 与 `overrides` 都会继续继承 source 级 `provider_source_name`，不会再出现“source 内联配置能吃到上下文、切到 `registry_file` 就退化”的分叉行为。
  - `http_json` 模板里如果把保留运行时变量写错，例如 `settings_*` / `tool_registry_*` 命名空间 typo，当前会在 settings/source diagnostics 阶段直接归一成 `invalid/tool_executions`，同时运行时仍保持 fail-fast，不再静默丢 header/query 后才在上游请求里表现成假性网络或协议问题。
  - `http_json` 的 URL、header/query value shape、请求 JSON header、`json_body` 严格 JSON 与 response mapping path 也继续收紧：URL 必须是绝对 `http(s)` 地址、不得携带 userinfo credentials，显式端口必须合法，不得包含原始空格/控制字符或 fragment；URL 自带 path 与 query string 也会在 percent-decoded 后检查控制字符、dot-segments、参数名和值，不能绕过 `query_params` 治理或 path 脱敏，URL 内联 query 参数名自身不得重复，也不得和 `query_params` 声明同名参数，避免真实上游按首值/末值产生歧义；header name 必须是合法 HTTP token，header value 不允许 CR/LF 注入或其他 HTTP 控制字符，header 名不得以大小写变体重复，显式 `Content-Type` 在声明 `json_body` 时必须是 `application/json` 或 `+json`，若声明 charset 则必须是 UTF-8，重复 charset 参数必须全部等价于 UTF-8，缺少 `=` 或值的 `charset` 参数会按非 UTF-8 配置失败；显式 `Accept` 必须允许 JSON 且对应 media range 的每一个 `q` 参数都必须是有限的 `(0, 1]`，缺少 `=` 或值的 `q` 也会按非法 q 失败，显式 JSON / `+json` / `application/*` / `*/*` media range 一旦声明 `q=0` 或非法 q，不会再被后续 wildcard 掩盖；请求侧 `Content-Type` / `Accept` 参数也会按 quote-aware 规则解析，quoted profile 里的 `charset` / `q` 不会被误当真实协议参数，未闭合 quoted 参数会在 settings/source diagnostics 或运行时渲染后 fail-fast；query 参数名不得包含空白/控制字符或 `= & ? #` 这类 query 结构分隔符，query 值只接受标量或标量列表；`json_body` 必须能编码成严格 JSON，`NaN` / `Infinity` 这类非有限数或运行时模板渲染出的不可序列化对象都会按 `json_body.score` / `json_body.payload` 这类路径提前诊断。settings/source 能静态渲染出的 URL/header/query/body 模板也会按渲染后结果进入 diagnostics；运行时模板若把 URL 渲染成相对地址、带 credentials、非法端口、带 fragment、含控制字符或 dot-segments 的地址，或把 header/query/body 渲染成非法协议形态，都会在发请求前 fail-fast；`execution_summary.url_origin` 与 `url_path` 也会做安全化处理，避免非法端口裸抛、半可信 origin，或 path 中的 `token=...`、`api_key/...`、`api_key%2Fsecret` 这类编码片段泄漏进 trace/export，`response_path` / `result_fields.*` 只接受 dot field 与数字索引语法，避免非法 bracket 片段被部分解析成错误上游路径。
  - `http_json` 上游返回 HTTP 错误、连接/传输错误、非 2xx 响应对象、2xx 非 JSON 响应、显式非 JSON `Content-Type`、204/空成功体、redirected response URL drift 或非法 UTF-8 响应体时，runtime 现在会把稳定的 HTTP status、脱敏限长后的 reason、`transport error`、`invalid JSON response`、`empty JSON response`、`invalid JSON response charset`、`invalid JSON response content-type` 或 redirected response 诊断与有限 preview 一起落入错误信息；除 `HTTPError` 外，`status/code/status_code/getcode()` 这类 adapter 响应状态也会在 response mapping 前拦截，支持 bytes 与 `503 Service Unavailable` 这类 status-line 形态，且不可解析或越界状态会直接报 `invalid HTTP response status`，避免真实上游状态被伪装成成功或 fatal mapping error；response final URL 与 reason/msg 会接收 bytes-like adapter value，URL drift 比对会忽略大小写 host、默认端口、fragment、query 参数顺序、等价 query encoding 与 path unreserved percent-encoding 噪音，但真实 query drift 仍会在映射前 fail-fast 且不泄漏跳转 URL token；2xx/未知状态响应一旦出现 final URL drift，会优先于 body read、坏 gzip/deflate 或 unsupported encoding 失败暴露 redirected response 诊断，避免登录/网关跳转被坏 body 遮掉；response body reader 会优先使用 `read()`，并兼容 `.content` / `.body` / `.data` / `.text` 这类常见 adapter body 属性，`read()` 返回不可用 body 类型时也会继续尝试这些属性；对只支持 `read(amt)` 的 adapter，会按固定 chunk size 分块读到 EOF 后再进入同一条响应解析链；只暴露 `json()` parsed body 的 adapter 会先重新序列化为 UTF-8 JSON bytes 再进入同一条映射链；只暴露 `iter_bytes()`/`iter_content()`/`iter_text()`/`iter_lines()` streaming body 的 adapter 会拼接 bytes-like chunk 后继续解析；reader 缺失、`read()` / `__enter__` 抛错、body 类型不支持会稳定落成脱敏 `transport error`，且非 2xx 或 invalid status 场景会优先保留 HTTP status/invalid-status 诊断；`Content-Encoding` 支持 `gzip/deflate/identity` 及其安全链式组合，其中 `deflate` 同时兼容 zlib-wrapped 与 raw deflate，会在 JSON 解析前解码，HTTPError 的压缩错误体也会走同一条 preview 链路，HTTPError body read 失败、坏压缩体或暂不支持的 encoding 会保留 status/reason 并带脱敏 preview；2xx 成功响应里的坏压缩体或暂不支持 encoding 也会按上游响应协议错报出，不再混成 `transport error`；非 2xx 响应对象即使 body 压缩声明坏掉或读取失败，也会优先保留 HTTP status/reason，并附带安全化的失败 preview；HTTPError、非 2xx/invalid status、显式非 JSON content-type、invalid JSON 与 unsupported encoding 的失败 body preview 现在也会在可用时按响应 `Content-Type` charset 先解码再脱敏，避免 UTF-16 等真实上游错误体在 trace/observation/export 中退化成乱码或绕过结构化脱敏；response adapter 的 `status/reason/geturl/getheader/headers/info` 局部回调异常会继续尝试备用来源，不再直接遮掉 HTTP status、redirect 或 content-type/encoding 诊断；response header mapping 会大小写不敏感解析，`getheader(name, default)`、`headers.get(name, default)`、`get_all()`、`getheaders(name)`、bytes-like header name/value、bytes-only `get(...)` candidate、malformed `items()` entry、`raw_items()` / `multi_items()` entry、pair-list headers/info 或 list/tuple header value 会先安全归一或跳过；重复 `Content-Type` / `Content-Encoding` 会按多值 header 合并处理，避免第一值把非 JSON content-type 或 gzip/identity 链式 encoding 吞掉，重复同义 JSON / `+json` content-type 仍可接受；`Content-Type` 的 `application/json` 与 `+json` subtype 继续作为 JSON 响应接受，quoted/uppercase charset 会按声明解码，quoted 参数里的逗号/分号不会被误拆成 media type 或 charset，但未闭合 quoted 参数会在 response mapping 前按 `invalid JSON response content-type` 失败，缺少 `=` 或值的 charset 参数会按 `invalid JSON response charset` 失败，避免网关/代理用坏 header 把 `text/html` 或坏 charset 藏成 JSON 成功；重复同义 charset 会接受，重复冲突 charset 会以 `invalid JSON response charset` 安全失败，未知或敏感 charset 也会脱敏失败；bytes 形态的 `text/html` 网关/登录页即使 body 形似 JSON 也不会再伪装成成功映射；JSON error body 的敏感 key、普通字符串值里的敏感 assignment、HTML/raw text preview、transport reason 与 bytes-like reason 里的 `token/api_key/secret=...` 现在会连标签和值一起显示为 `[redacted]`。
  - `http_json` 的真实上游错误诊断现在也会带出安全响应 header hint：`HTTPError`、非 2xx adapter、invalid status、redirected response URL drift、已拿到响应头后的 body reader/read/body type transport error、2xx 响应协议错误（显式非 JSON content-type、invalid JSON、invalid charset / charset decode error、unsupported success content-encoding），以及 response mapping schema drift（`response_path` 缺失、`result_fields` 全部落空）会在错误信息中追加脱敏限长后的 `Retry-After` / `X-RateLimit-*` / `RateLimit-*` / `X-Request-ID` / `X-Correlation-ID` / `Traceparent` / `X-Trace-ID` 等白名单信息；`Location` 等可能携带 token 的跳转 URL 不会进入 hint，敏感 header 值也只会显示 `[redacted]`，而 bearer-like、带空白或过长的 request-id 类 header 会直接跳过，不再被当成安全请求关联号。
  - 对 `http_json` 请求模板里那些只能到运行时才知道是否齐备的输入变量，例如 `$top_k`、`$precision`，当前 runner 也会在真正发请求前直接 fail-fast，并把缺失变量与 `query_params.limit`、`json_body.precision` 这类路径一起报出来，不再静默删字段后发出半残 HTTP 请求。
  - 同一条请求侧 diagnostics 现在也会安全化敏感字段路径与敏感模板变量名：`query_params.api_key`、`json_body.access_token`、`json_body.filters[0].client_secret` 这类协议错误或缺失模板变量路径会显示为 `[redacted]`，`runtime_access_token` / `tool_registry_api_key_typo` 这类变量名也会脱敏，避免 settings/source diagnostics、runtime error、trace/export 为了定位请求配置问题而重新暴露敏感字段语义。
  - `execution.kind` 这类执行协议枚举如果被误配置成带敏感语义的坏值，也会在 settings diagnostics 与 runtime error 中显示为 `[redacted]`；unsupported execution kind 不再把 `token=...` / `api_key=...` 这类配置值原样带到治理面或 trace/export。
  - 对 `headers/query_params/json_body` 里只有空白字段名这类本来会被静默吞掉的请求模板配置，当前 settings/source diagnostics 与 preflight 也会提前归一成 `invalid/tool_executions`，不再等到 runner 正常化请求对象时再悄悄忽略。
  - 对显式声明了 `response_path` 的 `http_json` real tool，当前 runner 也不再悄悄退回根 payload：如果上游响应里根本找不到这个路径，或者配置里给的是空白 `response_path`，都会直接按配置/协议错 fail-fast，且错误里的 path 会做敏感 assignment 脱敏，并附带安全且限长的上游 payload shape / available response keys 摘要与白名单 header hint，避免把坏掉的响应映射伪装成“工具还能跑，只是结果有点怪”或把敏感 path / key / value 带进回放。
  - 对显式声明了 `result_fields` 的 `http_json` real tool，如果所有字段映射都落空，当前 runner 也会直接 fail-fast，并把失败的映射项以有限数量摘要带出来，同时补充脱敏后的可用响应 key / payload 类型提示与白名单 header hint；当 `response_path` scoped 到数组时，还会给出首项对象 key 摘要，帮助定位真实搜索/列表类上游 schema drift。这样上游响应漂移或 registry mapping 写错时，不会再返回空结果对象伪装成成功执行，也不会让超长 mapping 列表、超长 key 或真实上游 secret 撑进 trace/export。
  - `http_json` 成功输出现在也会复用同一套敏感 payload 脱敏与列表计数归一化：无论是没有 `result_fields` 的根响应 / `response_path` scoped 响应，还是显式映射后的字段输出，`secret/token/api_key/password/...` key 与字符串里的敏感 assignment 都会在进入 preview/output/observation/export 前被替换为 `[redacted]`；真实搜索上游如果只映射出 `items`、`results` 或 `matches` 列表，也会分别补出 `documents_total` / `hit_count`，且同义字段里出现非列表元数据，或显式 count 字段是 `unknown` / 负数这类不可用值时，都不会挡住后续真实列表计数；`documents_total` / `hit_count` 的字符串数字、整型小数字符串与整型浮点也会归一成非负整数。归一化现在同时覆盖 `http_json` 注册工具的 helper 级 preview/output/result-summary/observation 投影，且 helper 会先规范化半迁移 registration 的 `execution_kind` 再决定是否走安全 output shape；只有 step meta `execution_kind=http_json` 且没有 registry registration 的 trace/export 回放、`chat_persistence_service` 的 markdown meta safe-output / preview fallback、task/session JSON export 的 `steps[].content`、trace delta snapshot、TaskResponse `trace_json` outward summary，以及 task/session markdown 里旧 real-retrieval preview 的显式 `Preview:` / `Output:` 和 `trace_preview.content_excerpt` 字符串回放也会继续复用这条链路。
  - `http_json` 成功输出现在还会从白名单响应 header 继承安全 `request_id`：当上游只在 `X-Request-ID` / `Request-ID` / `X-Amzn-RequestId` / `CF-Ray` 里返回请求关联号，而 JSON body 或 `result_fields` 没映射出可展示的 `request_id` 时，runtime 会补进结构化 output，并继续进入默认 output projection、result summary、observation 与 export；看起来会被脱敏、带空白/bearer-like、过长或截断的 header/body request id 不会进入结构化 output，敏感 body request_id 也不会压过安全 header。旧 trace/helper 回放里已经落下的 unsafe `request_id` 也会在 summary、observation、markdown meta、display content 与 mock final-answer observation summary / generic payload summary 前被移除；helper 级 `build_tool_result_output/preview/summary`、`build_tool_observation_entry(...)` 的 step meta / direct output generic fallback、`normalize_tool_output_for_registration(...)` 的半迁移 raw output 兜底、RAG follow-up chunks、`build_tool_error_meta/payload(...)` 的 raw error message 兜底、success meta raw `last_error` 兜底、generic `error` SSE event / retry transition / terminal failure message 兜底、chat persistence raw `http_json` preview/output 回放、task/session JSON export step meta，以及 session export 的泛化 provider/hosted trace preview fallback 也会复用安全 output shape / error text，避免旧 payload 的 `access_token`、`api_key`、unsafe `request_id`、`token=...` 或 raw error assignment 旁路进入 trace/export/task_failed；mock final-answer 的泛化 structured output summary、纯文本 observation summary 与 `Tool context` fallback 也会跳过敏感 key 或脱敏 `token=...` 这类字符串 assignment，不再把旁路字段写进最终回答。
  - `http_json` 的可见 tool input 现在也按同一条安全 payload 规则处理：`tool_start` SSE payload、action step 初始 meta、success/error meta，以及 task/session JSON export 与 markdown meta 回放里的旧 `tool.input` 都会脱敏敏感 key 与字符串 assignment，避免 `access_token`、`Authorization`、`client_secret` 或 `token=...` 参数先于执行结果进入 trace/export；真实 runner 仍使用未脱敏的业务输入渲染请求模板，因此不会破坏 `$base_url`、鉴权参数或其他真实上游协议校验。
  - `http_json` 的结果元数据与响应映射诊断现在也会进入同一条敏感字段治理：`execution_summary.result_field_names` 与 `response_path` 会脱敏敏感字段名、assignment 和 path segment；显式配置的 `result_preview_keys` / `result_output_keys` 会过滤敏感 key，`result_fields.access_token`、`$.meta.api_key` 一类静态/运行时映射诊断会显示为 `[redacted]`，且当显式非空列表只剩敏感 key 时不会回退到模板默认 key；helper 级 preview/output 与 success meta 也会固定为空投影，避免 settings/tool_start/trace/export 通过字段名、path 或投影策略重新暴露敏感语义。
  - 对 `result_fields.documents_total: 123`、`result_fields.request_id: " "`，以及 `result_fields` 里混入空白字段名、只有空白字段名或干脆是空对象这类明显坏掉的映射配置，当前 settings/source diagnostics 与 preflight 也会提前归一成 `invalid/tool_executions`，不必再等到任务真正执行时才暴露。
  - workbench trace subtitle/search 现也开始消费这份 `execution_summary`：真实工具不仅能在后端 trace/export 里留下安全执行摘要，前端回放与检索也能直接按 `POST https://.../search`、response path、result fields 这类信息排障。
  - settings/preflight 的 `tool_details` 与前端 model settings tool detail summary 现也继续透出并展示 `execution_summary`；不用进任务 trace，就能先看出某个 real tool 当前会打到哪类 HTTP endpoint，以及大致的 query/body/response-field 形态。
  - source/settings/preflight 的 `tool_details` 现在还会把 `invalid/tool_executions` 继续下沉成 per-tool `execution_diagnostics`；不需要只看 source 级 diagnostics summary，也能直接定位是哪个 real tool 的 `http_json` 配置坏了。这里也会复用 registry diagnostics 的安全化规则，外层 diagnostics 或 registration 半迁移 payload 里的 `api_key=...`、`token=...` 与敏感字段路径不会从 tool details 侧路重新透出。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续挂进 runtime tool semantic：坏掉的 real tool 一旦真的进入任务执行，`tool_start/tool_end`、action trace meta、前端 live store 与 trace subtitle/search 也能直接看到是哪条执行配置坏了，而不再只有 settings/preflight 能解释错误来源；半迁移 registration diagnostics 里的敏感 assignment 与字段路径也会在 extra tool / override 构造和进入 live runtime meta 前脱敏。
  - retrieval family 的 real tool 现在也不再强依赖本地 stub 风格的 `chunks` 字段：`http_json` 只要返回 `documents`、`items`、`results`、`hits` 或 `matches` 列表，runtime 也会从 `snippet/content/text/excerpt/summary/description/body/...` 中自动提炼 follow-up 片段；列表项里的 `metadata/document/payload/chunk/node/...` 多层嵌套对象也会受控向下解析，且当 `documents` 只有 id/title 这类元数据时会继续降级查看后续别名列表，继续打通真实检索的 rag follow-up、trace 与 observation 主链。
  - 对 retrieval family 的 runtime override / real tool，如果上游只返回 `documents` / `documents_total` 而没有显式配置 `result_preview_keys`，默认 preview/output key 推断现在也会显式覆盖 `documents_total`；docs-only 检索结果不再在 `tool_end` preview、result_summary、observation 与 trace/export 回放里退化成空投影或泛化文案。对显式映射 `items` / `results` / `matches` 的 `http_json` 搜索工具，runtime 也会把这些常见列表别名转成可投影的数量字段，并继续从列表项里提炼 snippets，避免真实 provider 响应字段名不是 `documents/hits` 时摘要链或 RAG follow-up 断掉。
  - 对 docs-only 的真实 provider 检索结果，如果 `documents_total` 同时带有 `knowledge_base_id`，runtime result summary、observation、session export markdown 与 mock final answer 现在会显示 provider KB 来源（例如 `from hosted-kb`），但不会误写成本地默认知识库的 `from knowledge base ...` 语义；这条规则也覆盖只有 `Hosted Search` / `Provider Search` label、没有显式 semantic meta 的旧 trace 与 Tool observations 回放。
  - 同一路 docs-only retrieval fallback 现在还会在默认 output key 推断里保留 `request_id`；因此真实 provider/real search 工具即使没单独声明 `result_output_keys`，`result_summary`、observation、success output 与导出回放也能继续带出上游请求关联号，而不会只剩文档数量。
  - 对 retrieval family 的 runtime override / real tool，如果上游走的是 `hit_count` 命中投影而不是 docs-only 投影，`result_summary` 与 observation 现在也会继续带出 `request_id`；真实 provider search 不会再出现 output 里有请求关联号、但 trace/export 摘要文案仍丢失它的分叉。
  - 对 `http_json` 的 real/provider calc，如果 registry 只声明了 `result` 映射而没单独补 `result_output_keys`，默认 output projection 现在也会继续保留 `request_id`，并把只有 `result/request_id` 的返回总结成人类可读的 `Calculated result = ... (request id ...)`，避免 trace/observation/export 退回生硬的 generic payload 文案。
  - mock final answer 这一层现在也和 runtime helper 对齐了 `request_id` 语义：无论是 `hit_count + request_id` 的 real/provider retrieval，还是 `result + request_id` 的 real/provider calc，mock provider 生成的 Summary 都会继续带出请求关联号，不再退回旧的无请求号摘要或 generic payload 文案。
  - 对旧 trace、session export preview 或 typed payload 里那些只保留了 `output + effective_result_output_keys`、却还没显式落 `result_summary` 的 real tool step，trace/workbench/export display helper 现在也会继续从 safe output 回推出人类可读摘要；因此老数据回放不再只能看到 `Tool done: ...` 加原始 JSON，而会尽量复用 `Retrieved ... (request id ...)` / `Calculated result = ...` 语义。
  - 同一条 safe-output fallback 现在也已经贯通到 task trace preview、session export preview 与前端 workbench display helper；旧 preview 数据即使没有显式 `result_summary`，也会优先展示推断后的摘要，而不是继续把 `Tool done: ...` 当成主文案。
  - 同一套推断逻辑现在也会继续覆盖只有 `output_preview` 的旧 tool step；即使老 payload 没落 `output + effective_result_output_keys`，或把 `output_preview` 存成 JSON 字符串，planner/retrieval/calc 的 trace preview、task export markdown、tool observation 与前端 workbench 回放也会先把可解析对象恢复为结构化 preview，并优先展示 `Planned steps - ...` / `Retrieved ...` / `Calculated result = ...` 一类摘要，再附带 preview 片段。
  - 前端 workbench 的 `output_preview` 回放现在也覆盖合法双层 JSON 字符串；像 `"{\"result\":7,...}"` 这类 preview 会先恢复成结构化对象再参与摘要推断与 preview 展示，不再回退到 `Tool done: ...` 加 quoted JSON。
  - 后端 trace display helper 的 `Preview:` 行现在也会对 quoted JSON `output_preview` 做同样恢复；因此 task/session trace preview、export helper 与前端回放看到的 preview 文案更一致，不再一边能推断摘要、一边仍显示转义 JSON。
  - 同一条 safe-output fallback 现在也继续覆盖 `effective_result_output_keys` 已存在、但 `output` 仍落成 JSON 字符串的半迁移旧 payload；observation、mock final answer、task/session preview、export 回放与前端 workbench display 会先按安全 output policy 恢复结构化 output，再推断 real retrieval / calc / planner 摘要，不再回退到原始 JSON 或把被过滤字段重新透出。
  - 前端 live store 的 `tool_end` 合并现在也和这条半迁移治理语义对齐：即使 SSE / reconnect / 历史 payload 把 `output` 带成 JSON 字符串，只要已落下 `effective_result_output_keys`，store 也会先裁成安全 output 对象，再交给 workbench display / search / semantic stats 消费，而不会把整段原始 JSON 留在内存态工具元数据里。
  - 同一条 safe-output coercion 现在也覆盖合法双层 JSON 字符串形态的 `output`：例如 `"{\"result\":7,...}"` 会先解成结构化对象，再按 `effective_result_output_keys` 裁剪；后端 observation / markdown meta 与前端 live store / workbench display 不会再把 quoted JSON 或 `secret` 带回回放文案。
  - session markdown / preview 的旧字符串解析现在也补齐了 quoted JSON fallback：像 `Output: "{\"result\":7,...}"` 这类双重转义旧 excerpt，也会先恢复结构化 payload，再按 calculator / retrieval / planner 语义裁出安全 output keys，避免 `secret` 或 structural-only 字段重新混进导出回放。
  - session markdown 的 direct-label preview 也补齐同类 quoted JSON fallback：`Hosted Math: "{\"result\":7,...}"` 这类旧 `content_excerpt` 会先恢复结构化 payload，再产出 `Calculated result = ...` 摘要与产品化标题，不再把 quoted JSON 或旁路字段写进导出行。
  - 对更老的非严格外层引号 excerpt（例如 `Hosted Math: "{"result":7,...}"`），session markdown direct-label parser 也会做同一层窄恢复；普通非 JSON 文本仍保持原样 fallback。
  - task export markdown / markdown meta 这一层现在也已补上同类防回归覆盖：JSON-string safe output 会继续按 `effective_result_output_keys` 裁成安全 output，再交给 trace markdown 与 display helper 消费；`execution_kind=http_json` 的显式 `output_preview` 也会先做列表别名归一化与 preview key 投影，不会把旁路字段重新写回导出内容或 `Preview:` 文案。
  - mock final answer 的 observation parser 现在也补齐 quoted JSON payload 回放：当 `Tool observations:` 里只剩合法双层 JSON 字符串，或旧 preview/excerpt 形态的 `"{"result":...}"` 时，会先恢复结构化对象再推断 real calc/retrieval/planner 摘要，不再把原始 JSON 字符串或 `secret` 一类旁路字段写进最终 Summary。
  - session export markdown builder 现在也会继续把旧 `trace_preview.content_excerpt` 里的 `Label: {...}` 与 `Tool done: ... Preview: ... Output: ...` 归一成推断摘要，同时对 `http_json` real retrieval 的显式 preview/output 片段做列表别名归一化和安全投影；旧会话导出 markdown 不会再单独退回裸 JSON、泛化 `Tool done:` 文案，或把 `secret` / 坏 count 原样带进 `Preview:`。
  - 对无法解析为 JSON 的旧 `http_json` raw `output_preview` / `output` 字符串 fallback，observation helper、后端 trace display / markdown meta 与 session markdown export 现在也会复用同一套原始文本脱敏，清洗 `token=...`、`query_params.access_token` 与 bare bearer 片段，避免 malformed preview 旁路重新写进 observation、trace 或导出回放。
  - mock final-answer 的纯文本 observation fallback 也继续补齐同类字段路径与 bare bearer 脱敏；当旧 `Tool observations:` 里只有不可解析的 `Provider Status: status=... query_params.access_token Bearer ...` 文本时，最终 Summary / Tool context 不会再保留敏感字段名或 bearer token。
  - observation helper 现在也会在只剩 step meta safe output 或 preview output 的 real tool 场景下优先复用同一套结果摘要，而不是退回 `Provider Search: {"documents_total":2}` 这类 JSON-only 文案；因此 mock final answer、observation 回放与导出链的摘要语义更一致。
  - 对那些 registry 已经取不到、但 step meta 里仍保留了 `semantic_family` 与结构化 safe output / preview output 的 real tool，observation helper 现在也会继续按 step meta 语义推断 `Retrieved ...` / `Planned steps - ...` 摘要；旧 trace、断链 source 或导出回放不会再因为 registry 缺席而退回 JSON-only 文案。
  - 对那些更老的 real tool step meta，即使 `semantic_family` 已丢失，只要还保留了 real structural `kind`（例如 `provider_retrieval` / `provider_calc`）与结构化 safe output，observation helper 现在也会继续推断 `Retrieved ...` / `Calculated result = ...` 摘要；与此同时 builtin calculator 与 generic custom tool 仍保持原先更保守的 preview/JSON observation 语义，不会被误摘要化。
  - mock final answer 现在也会对 name-only 的旧 real/provider retrieval JSON observation 保持更保守的语义：当 observation 里只有 `hit_count + knowledge_base_id`、但缺少显式 semantic 字段时，只有 builtin/local retrieval label 才会继续补 `from knowledge base ...`；`Provider Search` / `Hosted Search` 这类 real tool 旧文案不再被误写成本地知识库命中。
  - mock final answer 这一层现在也会继续识别旧 observation payload 里的 structural `kind`（例如 `provider_calc`），即使缺少 `tool_kind` / `semantic_family`，也会沿 real tool 语义继续输出 `Calculated result = ...` 一类摘要，而不是退回 generic payload 文案。
  - 同一条保守语义现在也继续覆盖旧 trace preview / session export preview / workbench display 与无 registration 的 observation fallback：当 step meta 或 preview 里只剩 `hit_count + knowledge_base_id + request_id` 且 label 只是 `Provider Search` / `Hosted Search` 这类 real retrieval 名称时，trace/export/final-answer 不会再误补本地 knowledge base 语义，也不会退回 JSON-only observation。
  - 同一套保守 fallback 现在也继续覆盖只有 name-only label 的旧 real/provider calc：当 step meta、preview excerpt、observation，或 registry 中未显式声明语义族但 label 是 `Hosted Math` / `Provider Math` 的真实计算工具，只剩 `result + request_id` 时，final answer、tool observation、result summary、task/session preview、markdown export 与前端 workbench display 也会优先产出 `Calculated result = ... (request id ...)`，而不是退回 generic payload / `Tool done:` 文案或在 summary helper 中断链。
  - 对 registry/source 中已接 `http_json`、但还没显式声明 `kind/runtime_semantic_kind/result_*_keys` 的 label-only real tools，runtime helper 现在也会从 `Hosted Math` / `Hosted Search` / `Hosted Planner` 这类 name/label 推断默认 preview/output keys：calc 继承 `expression/result/request_id`，retrieval 继承 `documents_total/hit_count/knowledge_base_id/request_id`，planner 继承 `plan/steps`，让 preview/output/result-summary/observation 能直接闭环，而不是空投影；如果这类 real tool 已经显式配置了 `result_preview_keys`、但没有配置 `result_output_keys`，preview/output effective keys 会先过滤半迁移 legacy preview keys 里的敏感字段，再保留安全 preview keys，并按类型补齐诊断字段（retrieval 补 `knowledge_base_id/request_id`，calc 补 `request_id`，planner 保留 planner preview keys）；如果半迁移对象已经显式带了 `result_output_keys`，effective output keys 也会再次过滤敏感字段名，避免 `effective_result_preview_keys` / `effective_result_output_keys` 暴露 `access_token` 这类字段名；底层 output normalizer 对这类 label-only real tool 也不会再补 `tool_kind: null`，runtime semantic meta 与 settings/preflight tool details 则继续同步补出工具名级 `semantic_kind` 与 family 级 `semantic_family`。
  - session export / trace preview 这一层现在也会继续识别旧 preview payload 里的 structural `kind`（例如 `provider_calc`）；即使 excerpt 里没有 `tool_kind` / `semantic_family`，markdown 导出与 preview excerpt 也会继续优先展示 `Calculated result = ...` 一类 real tool 摘要，而不是回退到原始 JSON 文案。
  - task trace preview 与前端 workbench display helper 现在也会在 safe output 因 output policy 过滤掉 `kind` 之后，继续回看原始 `tool.output` / `tool.output_preview` 里的 structural `kind`；因此旧 real calc step 即使只把 `provider_calc` 留在 raw output 里，task preview、trace 回放与工作台显示也不会再退回 `Tool done: ...`。
  - 前端 semantic filter / semantic stats 现在也会对这批 name-only real retrieval / calc 历史 step 复用同一层保守分类：当旧 trace 里只剩 `Hosted Search` / `Hosted Math` 这类 label 加 `documents_total` / `result` 输出时，工作台的 retrieval/calculator 筛选与计数不会再把它们漏成 `other`。
  - 同一条前端 semantic fallback 现在也继续覆盖 name-only planner 历史 step：当旧 trace 里只剩 `Hosted Planner` / `Provider Planner` 这类 label 与 `plan` / `steps` 输出时，planner 筛选与计数也会继续识别它们，而不是漏成 `other`。
  - 同一套前端 semantic fallback 现在也已经贯通到 subtitle 与搜索：当 name-only 历史 step 缺少 `semantic_kind` / `semantic_family` 时，trace subtitle 会回退显示 `[planner] / [retrieval] / [calculator]`，而工作台按 `planner` / `retrieval` / `calculator` 文本搜索时也不会再漏掉这批旧 real tool 轨迹。
  - `getStepTitle(...)` 这一层现在也复用了同一套派生 semantic fallback；因此 name-only 历史 step 的标题不再只剩 `Hosted Planner` / `Hosted Math` 这类裸 label，而会尽量补成带 `[planner]` / `[calculator]` / `[retrieval]` 的产品化标题。
  - 同一套派生 semantic fallback 现在也补到了后端 `chat_persistence_service` 的 task/session trace preview title：当旧 preview 里只剩 `Hosted Search` / `Hosted Math` / `Hosted Planner` 这类 name-only real tool label 与 `documents_total` / `result` / `steps` 输出时，导出预览标题也会补成带 `[retrieval]` / `[calculator]` / `[planner]` 的产品化标题，与前端 workbench title 语义保持一致。
  - session markdown 导出现在也会对旧 `trace_preview.title` 还是裸 label 的历史 payload 继续补同一套 title 语义：即使只剩 `Hosted Search` / `Hosted Math` / `Hosted Planner` 或 structural-kind old preview，markdown 里的 trace preview heading 也会补成带 `[retrieval]` / `[calculator]` / `[planner]` 的产品化标题，同时仍保持对 real retrieval 的保守摘要，不会把 `Provider Search` 误写成本地 knowledge base 命中。
  - 同一条 session markdown fallback 现在也补齐了一个更隐蔽的旧 payload 边界：如果历史 `trace_preview.title` 已经是通用 `[retrieval]`、但 excerpt 仍是原始 real-tool JSON，导出摘要也会继续按 real retrieval 处理，不会因为这个通用语义标签反向误补 `from knowledge base ...`。
  - observation / mock final-answer 侧现在也会把产品化过的 label 后缀当成展示噪音处理：像 `Hosted Math [calculator]` 这类旧 observation label，即使缺少显式 semantic hints、甚至 name 已经不是 registry 里的 canonical real tool 名，也会继续产出 `Calculated result = ... (request id ...)`，而不是退回 generic payload/JSON-only 文案。
  - 前端 `normalizeTraceToolLabel(...)` 现在也会剥掉产品化 label 的 bracket descriptor；因此旧 history step 即使 label 已变成 `Provider Search [retrieval]` / `Hosted Math [calculator]`，workbench 的结果摘要推断、semantic filter、search/stats 也会继续按 real retrieval / calc 处理，而不是退回 `Tool done: ...` 或漏成 `other`。
  - provider 规划结果里的产品化 extra-tool label 现在也会在后端 registry 解析前先剥掉同一层 bracket descriptor；因此像 `Fast Calculator [calculator]` 这类已经产品化过的 planner 输出，也能继续稳定解回真实 registry tool name，而不会在 provider branch 里掉成只剩 `task_plan`。
  - 同一层 bracket-strip 规则现在也补到了 `task_plan` 自己消费历史 `planned_tool_names` 的回放链；因此旧 payload 即使把计划工具名写成 `calc_eval [calculator]` 这类产品化形式，planner step 也会继续产出 `Evaluate calculation` / `Retrieve supporting context` 这类语义步骤，而不是退回泛化 `Run ...`。
  - tool registry governance 的 `allowed_tool_labels` 现在也会在有 canonical tool name 可对齐时剥掉这类仅用于展示的 bracket descriptor；因此 task/session export、governance summary 与前端工作台后续看到的 `Calculator Suite [calculator]` 一类旧标签，会稳定回落到 canonical `Calculator Suite`，而不会把产品化展示噪音继续写进治理视图；session-level governance merge 遇到“旧 summary 里残留 label-only 噪音、后续 task 才补回 canonical tool name”的历史数据时，也会同步完成去重，不再把 stale productized label 和 canonical label 一起带出；如果是直接落盘的 persisted session summary，只要它自身已经收敛到单一 `profile/provider_source`，归一化时也会按这条治理线索解析 canonical label，而不再误退回默认 source 的 tool label。
  - 对直接来自 typed payload / `model_dump()` 的 task/session governance，task detail/list response、task export summary、task/session export route builder、task export response、session export response、session export 内嵌 task trace governance 与 usage dashboard response/route 现在也会继续走同一层治理归一化；即使外层 response summary 已是 dict、但内层 governance 仍是 typed/model_dump 的半迁移 payload，task/detail/list/usage 与 session export route 也不会再把 `calc_eval + calculator_suite` 这类旧治理原样透传到 response/export/usage，而会按对应 source 稳定落到 `Calculator Suite`，同时保持原有 sparse/full payload 形态、response-ready trace/task model 身份与 service dict 信任边界不乱改。
  - 对那些 registry/source 已经声明成 real retrieval / real calc / real planner、但没有显式补 `runtime_semantic_kind` 的 noncanonical tool，runtime trace semantic 现在也会默认保留工具自身名称作为 `semantic_kind`，同时继续把 retrieval/calc/planner family 留在 `semantic_family`；因此 `Provider Search` 一类 real tool 的 action step、observation 与 rag follow-up 不会再塌回 builtin `knowledge_retrieval` 语义，而设置/preflight 的治理视角仍保持 family 级语义。
  - task/session preview excerpt 的默认长度策略现在也继续保住了这类结构化摘要里的完整 `request_id`；真实 provider tool 的 preview 不再在 `req-...` 处被截断成半残文案。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 已贯通 action step、`tool_start/tool_end`、持久化 trace、export 与 mock final answer。
  - retrieval / observation / helper fallback 已不再把 provider/real tool 误解释为默认本地知识库语义，name-only 路径也会优先复用已落盘的 registry 语义；即使原始 `output` 缺失，observation、success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 聚合也会优先复用 step meta 或 typed payload 中已落下的结构化结果；task/session export route builder 现在也会在外层 summary 已是 plain dict、但内层 `messages`、task `trace_preview`、task trace `rag_chunks/steps` 仍是 `model_dump()` 对象时完成最后一层浅归一化，同时保留 response-ready Pydantic model 身份；会话 Memory query、RAG ingest/query、RAG route 层与 shared knowledge-base merge 的 metadata、query payload root、document row、row list，以及 session create/detail/list/messages/export、task/session usage、task create/detail/list/cancel/trace/delta/export/stream-reconnect、auth register/refresh/session list/user list、audit log list 这批 outward summary route，以及 `chat_persistence_service` 的 task trace/usage/response/export/delta 与 `task_rows_*` 批量聚合 helper，也不再因 typed service payload / `model_dump()` payload 而退化成空结构或直接报错，nested metadata 也能继续保留。
  - mock final answer 的 `Tool observations:` 汇总现在也会回收 payload 内层 `safe_output` / `output` / `output_preview` / `result_preview` 里的 JSON 字符串，并浅继承父级 semantic / request 上下文；因此半迁移 observation 只剩嵌套 preview 时，也会继续产出 real calc / real retrieval 摘要，不再退回 `output_preview=...` 或泄漏旁路字段。
  - runtime helper、governance/export、registry diagnostics 与 planner payload 归一化已收口对旁路结构化载荷的兼容；当前 provider planner 与真实 remote provider 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`1394/1394`）
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

- 当前代码、三份 README 与 `.cursor/plans/insightagent_开发计划_306e7915.plan.md` 的主线判断一致：final answer / Tool observations / observation fallback / export fallback 子线已基本收口，后续只在审计扫出明确红测时补防回归。
- 当前没有旧测试计数残留；`data/insightagent.plan.back.md` 继续作为只读备份计划，不参与活跃开发同步。
- 下一阶段不再继续扩大旧 payload fallback 兼容面，主线切到“真实工具执行本体”：优先让已经能被 planner/registry/source 规划出来的 real/extra tools 真实打通上游协议、请求模板、响应映射、preview/output/result-summary、trace/observation/export 诊断闭环。

## 当前主线

1. `real-tool-execution`：把 provider/source 文件配置里的 real search / real calc 等 extra tool 从“可展示、可规划”推进到“可稳定接真实上游协议”。
2. `registry-governance`：继续收口 registry / profile / provider source / selected source / diagnostics / settings summary 的统一治理语义。
3. `queue-and-concurrency-lite`：在现有 cancel/timeout/running-task-recovery 基础上，推进单机任务排队、并发治理与运行可靠性。
4. `rag-governance-hardening`：在 `rag-rbac-lite` 之上继续补知识库版本化、来源治理与更细粒度 shared 规则。
5. 契约稳定：外部 SSE / trace / export / e2e 契约尽量不乱改，优先做内部 runtime/helper/display 收口。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard 与主链路 e2e / CI tooling 已落地。
- 当前未完成的重点不是这些基线能力，而是默认工具去 mock 化后的真实执行语义、registry 治理深化与单机并发治理。

## SSE 与 TraceStep 契约（当前实现）

`GET /api/tasks/{task_id}/stream` 的 `event: trace` 中 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。

当前 SSE 事件类型：

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

- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中可先为空或阶段性刷新，REST 中返回完整内容。
- 前端实时流、历史 trace 与导出回放都按同一 `TraceStep` 结构消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 知识库级 collection：`kb_{user_hash}_{knowledge_base_id}`（用户隔离）
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

### 通俗理解：为什么有 RAG 还需要 Memory

- `PostgreSQL`：完整账本，保存会话、消息、任务、trace、usage。
- `Chroma Memory`：当前会话便签本，保存可语义召回的会话记忆片段。
- `Chroma RAG`：长期知识库，保存导入文档的分块内容。

三者分工不同：

- `RAG` 解决“系统知道哪些外部资料”。
- `Memory` 解决“当前会话刚刚确认了什么偏好和约束”。
- `PostgreSQL` 解决“完整历史如何留档和回放”。

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
└── data/
```

## Docker（可选，Chroma）

在仓库根目录启动：

```bash
docker compose up -d chroma
```

默认后端连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

如需一键启动（会自动拉起 `postgres/chroma`，再启动 backend/frontend），可执行：

```bash
./start_insightagent.command
```

## 文档维护约定

- 活跃进度只保留“当前状态、当前主线、最近校验基线、下一步候选”这类高信号内容。
- 长串历史流水账、阶段内小切片和重复能力摘要不再继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
