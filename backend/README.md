# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前状态

- W1-W4 主链路已完成并收口。
- 阶段 5 已完成的基础能力包括：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时、`RBAC-lite`、`rag-rbac-lite`、任务取消/超时、running task 恢复支撑、任务/会话导出、usage dashboard、审计事件扩展。
- 当前活跃主线不再是 `tool-runtime-productionization` 文档化收口，而是：
  - 默认工具去 mock 化
  - 真实工具接入
  - `tool registry / profile / provider source` 治理产品化
  - extra/real tool 在执行本体、trace、observation、result preview、export 语义上的真实化
- 最近已对齐到代码的高信号能力：
  - 默认 canonical tool 名已统一到 `task_plan / task_retrieve`，`mock_*` 仅保留兼容 alias；planner 已能规划 real/extra tools 与动态 registry/source 候选。
  - provider / provider source 已支持 `loader_factory`，tool-registry diagnostics 已进入 entry 级 trace/export/preflight 语义，settings、selected source 与 runtime artifacts 使用同一治理主干。
  - `extra_tools` / registry `overrides` 现可直接声明 `execution.kind=http_json` 的真实执行器；provider/real tool 已不必再只靠模板 runner 做语义换壳，HTTP JSON 返回的 `documents_total/request_id/chunks/result` 等字段会继续沿 preview/output/result-summary、observation、rag follow-up 与 export 主链复用。
  - configured provider preflight 与 settings summary/validate 返回的 `tool_details` 现也显式包含 `execution_kind`；file/source 治理与前端设置面板可以直接识别哪些 tool 已切到真实 `http_json` runner。
  - 本轮继续补齐 `http_json` 成功 payload、RAG follow-up chunk、result-summary、HTTP error body preview、runtime error/artifact/observation summary、半迁移 provider/hosted trace display/export、session JSON trace_preview response/route coercion、task JSON `trace.steps[]` / 顶层 `rag_chunks` response/route coercion、display/markdown meta 的 `result_summary` 与嵌套 `meta.rag.chunks`、半迁移 provider/hosted `output_preview`/`output` 门控拓宽，以及 mock final-answer structured/generic fallback 的 raw text 脱敏：generic value/chunk/summary/error/input/content/excerpt fallback 会清洗 `query_params.access_token` / `response_path.data.access_token` / `response_path=$.data.access_token` / `response_path=$['data']['access_token']` / `response_path=$.data['access_token']` 一类字段路径、完整 URL 与嵌套 URL 参数/路径/fragment 值中的敏感 query / fragment / userinfo / path segment、成功 payload / raw fallback dict key 中的 diagnostic JSONPath/URL、半迁移 execution_summary `url_path` 里的嵌套 URL 与相对 query/fragment、`http_json` registry label/display name 里的 diagnostic URL/assignment、display helper、task response parsed `trace_json` 与 session export response/route 中非 provider/hosted 标题的 `via http_json` trace/preview URL、`client_secret` 类 compound key 与 bare bearer 片段；HTTPError 错误响应体读完后也会显式关闭响应 wrapper，完整 backend slice 当前为 `1334/1334`。
  - 若 registry `extra_tools` / `overrides` 显式声明了 `execution`，但 `kind` 缺失、shape 非法或写成不支持的执行器，tool runtime 现会直接返回配置错误，不再静默回退到模板 stub runner。
  - 同一批坏掉的 `execution` 配置现在也会进入 `invalid/tool_executions` diagnostics：file/source/global settings、selected source、configured provider preflight 以及 trace/audit 可以在真正跑 tool 之前就把问题暴露出来，而不是只在运行期 fail-fast；diagnostics summary、runtime trace/audit detail、旧 trace display 回放里的 values、configured provider runtime artifacts 的 `selected_source_diagnostics/source_diagnostics`、`diagnostics_runtime.summary/trace/audit`、`audit_event`、service action `trace_step/trace_event/kwargs` raw dict 边界、direct tool-plan service action executor，以及 tool-plan step error update、attempt result/outcome、terminal-failure、plan-item result、attempt-retry loop、stream、terminal、next-action、service-actions、effects、execution 构建结果与 `loop_execution_result` 附加点也会清洗敏感 assignment 和 `query_params.access_token` / `json_body.client_secret` / `result_fields['access_token']` 一类字段路径，避免 registry diagnostics 自身重新暴露请求侧 secret 语义。
  - `http_json.execution.method`、`timeout_ms` 与 tool 级 `default_timeout_ms` 现在也会被纳入同一套真实执行器治理：显式 method 只接受 `GET / POST / PUT / PATCH / DELETE`，显式 `GET + json_body` 会被视为协议配置错而不是静默丢 body，显式 timeout 只接受至少 1ms 的正整数毫秒；`POTS` / `FETCH` / `method=GET` 同时声明 `json_body` / `timeout_ms="slow"` / `default_timeout_ms="slow"` / fractional/sub-millisecond / `NaN` / `Infinity` / 超大整数一类坏配置会提前落进 `invalid/tool_executions`，运行时也会 fail-fast 或安全回退到模板默认值，不再静默降级成 `GET`、静默丢弃请求体或裸抛构建异常。
  - 对已接上 `http_json` 的 real tool，runtime 现在还会生成一份安全的 `execution_summary` 并挂到 tool semantic meta 上；`tool_start`、action step、持久化 trace 与 export 回放都能看到 method、origin/path、query/body/result-field 概览，同时避免把 header value 等敏感配置直接写进 trace。若 registry registration 本身已经携带半迁移 `execution_summary`，extra tool / override 构造、runtime meta 与 preflight tool details 也会重新清洗 `url_path`、`response_path` 与 `result_field_names`，不会把旧摘要里的敏感 path/key 原样透出。
  - `http_json` execution template 现在也会复用运行时 settings/source 上下文：global extra tool、source extra tool、registry override 与 file-backed source 都可以在 `headers/url/query/json_body` 中读取 `settings_api_key`、`settings_base_url`、`tool_registry_provider_source` 等变量，并支持 `${...}` 字符串插值来拼接 bearer/header 模板；能由 settings/source 上下文静态渲染的 URL 模板会按渲染后的绝对 endpoint 做 diagnostics 与 `execution_summary`，而无需把敏感值硬编码进 registry 配置。
  - file-backed source manifest 里的 `extra_tools` / `overrides` 现也继续走同一套 source 级模板上下文传递；把 source 从内联 JSON 切到 `registry_file` 后，`tool_registry_provider_source` 一类运行时变量不会再丢失。
  - 对 `http_json` 模板中的保留命名空间变量，runtime 现在也会做更细粒度静态诊断：`settings_*` / `tool_registry_*` typo 会直接落进 `invalid_tool_executions`，并在 runner 构建时继续 fail-fast，而不是静默丢掉 header/query 参数后才在真实上游请求里暴露成旁路错误。
  - `http_json` URL、header/query value shape、请求 JSON header、`json_body` 严格 JSON 与 response mapping path 现在也会提前治理：URL 必须是绝对 `http(s)` 地址、不得携带 userinfo credentials，显式端口必须合法，且不得包含原始空格/控制字符或 fragment；URL 自带 path 与 query string 也会在 percent-decoded 后检查控制字符、dot-segments、参数名和值，不能绕过 `query_params` 治理或 path 脱敏，URL 内联 query 参数名自身不得重复，也不得和 `query_params` 声明同名参数，避免真实上游按首值/末值产生歧义；header name 必须是合法 HTTP token，header value 不允许 CR/LF 注入或其他 HTTP 控制字符，header 名不得以大小写变体重复，声明 `json_body` 时显式 `Content-Type` 必须是 `application/json` 或 `+json`，若声明 charset 则必须是 UTF-8，重复 charset 参数必须全部等价于 UTF-8，缺少 `=` 或值的 `charset` 参数会按非 UTF-8 配置失败；显式 `Accept` 必须允许 JSON 且对应 media range 的每一个 `q` 参数都必须是有限的 `(0, 1]`，缺少 `=` 或值的 `q` 也会按非法 q 失败，显式 JSON / `+json` / `application/*` / `*/*` media range 一旦声明 `q=0` 或非法 q，不会再被后续 wildcard 掩盖；请求侧 `Content-Type` / `Accept` 参数也会按 quote-aware 规则解析，quoted profile 里的 `charset` / `q` 不会被误当真实协议参数，未闭合 quoted 参数会在 settings/source diagnostics 或运行时渲染后 fail-fast；query 参数名不得包含空白/控制字符或 `= & ? #` 这类 query 结构分隔符，query 参数值只接受 string/number/boolean 或这些值的列表；`json_body` 必须能编码成严格 JSON，静态配置里的 `NaN` / `Infinity` 或运行时模板渲染出的不可序列化对象都会按具体路径进入 diagnostics / fail-fast。settings/source 能静态渲染出的 URL/header/query/body 模板也会按渲染后结果进入 diagnostics；如果运行时模板把 URL 渲染成相对地址、带 credentials、非法端口、带 fragment、含控制字符或 dot-segments 的地址，或把 header/query/body 渲染成非法协议形态，runner 会在发请求前 fail-fast；`execution_summary.url_origin` 与 `url_path` 也会做安全化处理，避免非法端口裸抛、半可信 origin，或 path 中的 `token=...`、`api_key/...`、`api_key%2Fsecret` 这类编码片段泄漏进 trace/export，`response_path` / `result_fields.*` 只接受 dot field 与数字索引语法，避免 `[-1]` / `[]` 一类非法 bracket 被部分解析成假路径。
  - `http_json` 上游 HTTP 错误、连接/传输错误、非 2xx 响应对象、2xx 非 JSON 响应、显式非 JSON `Content-Type`、204/空成功体、redirected response URL drift 或非法 UTF-8 响应体现在会归一成稳定可读的 runtime error：错误信息包含 HTTP status、脱敏限长后的 reason、`transport error`、`invalid JSON response`、`empty JSON response`、`invalid JSON response charset`、`invalid JSON response content-type` 或 redirected response 诊断与有限长度 preview，便于 trace/observation/export 排障；除 `HTTPError` 外，`status/code/status_code/getcode()` 这类 adapter 响应状态也会在响应映射前被拦截，支持 bytes 与 `503 Service Unavailable` 这类 status-line 形态，且不可解析或越界状态会直接报 `invalid HTTP response status`，避免真实上游状态被误当成功或落成 fatal mapping error；response final URL 与 reason/msg 会接收 bytes-like adapter value，URL drift 比对会忽略大小写 host、默认端口、fragment、query 参数顺序、等价 query encoding 与 path unreserved percent-encoding 噪音，但真实 query drift 仍会在映射前 fail-fast 且不泄漏跳转 URL token；2xx/未知状态响应一旦出现 final URL drift，会优先于 body read、坏 gzip/deflate 或 unsupported encoding 失败暴露 redirected response 诊断，避免登录/网关跳转被坏 body 遮掉；response body reader 缺失、`read()` / `__enter__` 抛错、body 类型不支持会稳定落成脱敏 `transport error`，且非 2xx 或 invalid status 场景会优先保留 HTTP status/invalid-status 诊断；`Content-Encoding` 支持 `gzip/deflate/identity` 及其安全链式组合，其中 `deflate` 同时兼容 zlib-wrapped 与 raw deflate，会在 JSON 解析前解码，HTTPError 的压缩错误体也会走同一条 preview 链路，HTTPError body read 失败、坏压缩体或暂不支持的 encoding 会保留 status/reason 并带脱敏 preview；2xx 成功响应里的坏压缩体或暂不支持 encoding 也会按上游响应协议错报出，不再混成 `transport error`；非 2xx 响应对象即使 body 压缩声明坏掉或读取失败，也会优先保留 HTTP status/reason，并附带安全化的失败 preview；HTTPError、非 2xx/invalid status、显式非 JSON content-type、invalid JSON 与 unsupported encoding 的失败 body preview 也会在可用时按响应 `Content-Type` charset 先解码再脱敏，避免 UTF-16 等真实上游错误体在 trace/observation/export 中退化成乱码或绕过结构化脱敏；response adapter 的 `status/reason/geturl/getheader/headers/info` 局部回调异常会继续尝试备用来源，不再直接遮掉 HTTP status、redirect 或 content-type/encoding 诊断；response header mapping 会大小写不敏感解析，`getheader(name, default)`、`headers.get(name, default)`、`get_all()`、`getheaders(name)`、bytes-like header name/value、bytes-only `get(...)` candidate、malformed `items()` entry、`raw_items()` / `multi_items()` entry、pair-list headers/info 或 list/tuple header value 会先安全归一或跳过；重复 `Content-Type` / `Content-Encoding` 会按多值 header 合并处理，避免第一值把非 JSON content-type 或 gzip/identity 链式 encoding 吞掉，重复同义 JSON / `+json` content-type 仍可接受；`Content-Type` 的 `application/json` 与 `+json` subtype 会继续作为 JSON 响应接受，quoted/uppercase charset 会按声明解码，quoted 参数里的逗号/分号不会被误拆成 media type 或 charset，但未闭合 quoted 参数会在 response mapping 前按 `invalid JSON response content-type` 失败，缺少 `=` 或值的 charset 参数会按 `invalid JSON response charset` 失败，避免网关/代理用坏 header 把 `text/html` 或坏 charset 藏成 JSON 成功；重复同义 charset 会接受，重复冲突 charset 会以 `invalid JSON response charset` 安全失败，未知或敏感 charset 也会脱敏失败；bytes 形态的 `text/html` 网关/登录页即使 body 形似 JSON，也会在响应映射前 fail 为上游协议错误；JSON error body 的敏感 key、普通字符串值里的敏感 assignment、HTML/raw text preview、transport reason 与 bytes-like reason 里的 `token/api_key/secret=...` 会连标签和值一起显示为 `[redacted]`。
  - `http_json` 上游错误诊断现在也会安全带出响应 header hint：`HTTPError`、非 2xx adapter、invalid status、redirected response URL drift、已拿到响应头后的 body reader/read/body type transport error、2xx 响应协议错误（显式非 JSON content-type、invalid JSON、invalid charset / charset decode error、unsupported success content-encoding），以及 response mapping schema drift（`response_path` 缺失、`result_fields` 全部落空）会追加 `Retry-After`、`X-Request-ID`、`X-Correlation-ID`、`X-Amzn-RequestId`、`CF-Ray` 等白名单值，且继续脱敏限长；可能携带跳转 token 的 `Location` 不会被写入 trace/export 错误信息，bearer-like、带空白或过长的 request-id 类 header 也会被跳过，不会伪装成安全请求关联号。
  - 对只能到 tool 真正执行时才知道是否缺失的请求模板变量，`http_json` runner 现在也会在发请求前直接 fail-fast：像 `$top_k`、`$precision` 这类缺参会明确报到 `query_params.limit`、`json_body.precision` 等路径上，而不是先静默删字段再把问题伪装成上游协议或网络异常。
  - 请求侧 diagnostics 的路径与模板变量名现在也会做敏感字段名脱敏：query/body 协议错误、静态 unsupported runtime template variable 与运行时 missing template variable 如果落在 `query_params.api_key`、`json_body.access_token`、`json_body.filters[0].client_secret` 这类字段上，会统一显示为 `[redacted]`；`runtime_access_token` / `tool_registry_api_key_typo` 一类变量名也会脱敏，避免 source/settings diagnostics、runtime error、trace/export 通过 path 或 variable name 泄漏敏感请求语义。
  - unsupported `execution.kind` 的诊断现在也会复用同一套安全 formatter：如果坏 kind 本身包含 `token=...` / `api_key=...` 这类敏感语义，settings diagnostics 与 runtime invalid runner 只会显示 `[redacted]`，不会把配置值原样带进治理面或 trace/export。
  - 对 `headers/query_params/json_body` 里那些静态就能看出的空白字段名，settings/source diagnostics 与 configured provider preflight 现在也会提前报成 `invalid_tool_executions`；这类原本会在 request normalizer 中被静默忽略的坏配置，不必再等运行时才旁路消失。
  - 对显式声明了 `response_path` 的 `http_json` real tool，runtime 现在也不再在路径缺失时偷偷退回根响应 payload；如果上游响应里找不到该路径，或者配置里给的是空白 `response_path`，都会直接按配置/协议错 fail-fast，且错误里的 path 会做敏感 assignment 脱敏，并附带安全且限长的上游 payload shape / available response keys 摘要与白名单 header hint，避免 response mapping 坏掉后仍产出看似“有结果”的假成功或把敏感 path / key / value 带进回放。
  - 对显式声明了 `result_fields` 的 `http_json` real tool，runtime 现在也会在“所有字段映射都落空”时直接 fail-fast，并把失败的映射项以有限数量摘要带出来，同时补充脱敏后的可用响应 key / payload 类型提示与白名单 header hint；当 `response_path` scoped 到数组时，还会给出首项对象 key 摘要，帮助定位真实搜索/列表类上游 schema drift。上游响应结构漂移或 mapping 写错时，不会再默默返回空输出对象，把真实配置/协议问题伪装成成功，也不会让超长 mapping 列表、超长 key 或真实上游 secret 撑爆 trace/export。
  - `http_json` 成功输出现在也会复用同一套敏感 payload 脱敏与列表计数归一化：没有 `result_fields` 的根响应 / `response_path` scoped 响应，以及显式 `result_fields` 映射后的字段输出，都会在进入 preview/output/observation/export 前替换敏感 key 与字符串 assignment；真实搜索上游如果只映射出 `items`、`results` 或 `matches` 列表，也会分别补出 `documents_total` / `hit_count`，且 `documents/results` 这类同义字段是元数据对象而非列表，或显式 count 字段是 `unknown` / 负数这类不可用值时，不会挡住后续真实列表计数；`documents_total` / `hit_count` 的字符串数字、整型小数字符串与整型浮点也会归一成非负整数。归一化现在同时覆盖 `http_json` 注册工具的 helper 级 preview/output/result-summary/observation 投影，且 helper 会先规范化半迁移 registration 的 `execution_kind` 再决定是否走安全 output shape；只有 step meta `execution_kind=http_json` 且没有 registry registration 的 trace/export 回放、`chat_persistence_service` 的 markdown meta safe-output / preview fallback、task/session JSON export 的 `steps[].content`、trace delta snapshot、TaskResponse `trace_json` outward summary，以及 task/session markdown 的旧 real-retrieval preview 显式 `Preview:` / `Output:` 与 `trace_preview.content_excerpt` 字符串回放也会继续复用这条链路，避免真实上游成功 payload 旁路带出 secret、因为字段别名断链，或因为计数字段类型漂移退回 generic 文案。
  - `http_json` 成功输出现在还会继承安全响应 header request id：当真实上游只在 `X-Request-ID` / `Request-ID` / `X-Amzn-RequestId` / `CF-Ray` 里返回请求关联号时，runtime 会在 JSON body / `result_fields` 未提供可展示 `request_id` 的情况下补进 output，并继续贯通默认 output projection、result summary、observation 与 export；会被脱敏、带空白/bearer-like、过长或截断的 header/body request id 不会进入结构化 output，敏感 body request_id 也不会压过安全 header。旧 trace/helper 回放里已经落下的 unsafe `request_id` 也会在 summary、observation、markdown meta、display content 与 mock final-answer observation summary / generic payload summary 前被移除；helper 级 `build_tool_result_output/preview/summary`、`build_tool_observation_entry(...)` 的 step meta / direct output generic fallback、`normalize_tool_output_for_registration(...)` 的半迁移 raw output 兜底、RAG follow-up chunks、`build_tool_error_meta/payload(...)` 的 raw error message 兜底、success meta raw `last_error` 兜底、generic `error` SSE event / retry transition / terminal failure message 兜底、chat persistence raw `http_json` preview/output 回放、task/session JSON export step meta，以及 session export 的泛化 provider/hosted trace preview fallback 也会复用安全 output shape / error text，避免旧 payload 的 `access_token`、`api_key`、unsafe `request_id`、`token=...` 或 raw error assignment 旁路进入 trace/export/task_failed；mock final-answer 的泛化 structured output summary、纯文本 observation summary 与 `Tool context` fallback 也会跳过敏感 key 或脱敏 `token=...` 这类字符串 assignment，不再把旁路字段写进最终回答。
  - `http_json` 可见输入现在也会在 runtime/helper 与 trace export 层单独安全化：`tool_start` SSE payload、action step 初始 meta、success meta、error meta，以及 task/session JSON export 与 markdown meta 回放里的旧 `tool.input` 会脱敏敏感 key 与字符串 assignment，避免请求参数中的 `access_token`、`Authorization`、`client_secret` 或 `token=...` 提前进入 trace/export；`run_tool(...)` 与真实 runner 仍使用未脱敏的业务输入，所以请求模板渲染、URL credentials fail-fast 与鉴权参数不会被展示层脱敏污染。
  - `http_json` 结果字段元数据与响应映射诊断现在也会复用这条治理链：`execution_summary.result_field_names` 与 `response_path` 会对敏感字段名、assignment 或 path segment 做脱敏；显式 `result_preview_keys` / `result_output_keys` 会过滤敏感 key，`result_fields.access_token`、`$.meta.api_key` 一类静态/运行时映射诊断也会显示为 `[redacted]`，且显式非空列表如果只声明了敏感 key，不会再回退到模板默认 key，避免 registry settings、tool_start、trace 或 export 通过“字段名/path/投影 key”重新泄漏敏感语义。
  - 对 `result_fields.*` 里那些静态就能看出的坏 path，settings/source diagnostics 与 configured provider preflight 现在也会提前报成 `invalid_tool_executions`；像非字符串 path、空白 path，`result_fields` 里混入空白字段名、根本没有有效字段名，或显式给了空对象这类问题，都不必再等真实请求出去后才变成运行时错误。
  - 前端 workbench 的 trace subtitle/search 现也开始消费这份 `execution_summary`；后端这边输出的安全执行摘要已经不再只停留在 JSON trace/export 里，而是能直接参与 UI 回放与检索。
  - configured provider preflight、settings summary/validate 的 `tool_details` 现在也继续带上 `execution_summary`；真实工具的 endpoint 与 query/body/response-field 摘要已经不再只存在于运行期 trace，settings 治理面就能先读到。
  - source/settings/preflight 的 `tool_details` 现在还会继续挂上 per-tool `execution_diagnostics`；`invalid/tool_executions` 不再只停留在 source 级 summary，治理面可以直接指出是哪个 real tool 的 `http_json` 配置坏掉了。per-tool diagnostics 合并 registration 与外层 diagnostics 时也会复用同一套脱敏，半迁移 payload 里的 `api_key=...`、`token=...` 或敏感字段路径不会从 settings/preflight 详情侧路透出。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续挂进 runtime tool semantic；对显式声明了坏执行器的 real tool，`tool_start`、`tool_end`、error meta 与 action trace step 会直接带出配置诊断，不再只有 settings/preflight 才知道“为什么这个工具必然失败”。extra tool / override 构造与 runtime meta 都会清洗半迁移 registration diagnostics 里的敏感 assignment 与字段路径，保持 registry 内部对象、live SSE/trace 与 settings/preflight 详情一致。
  - retrieval family 的 real tool 现在也不再要求上游必须额外返回本地 stub 风格的 `chunks`：只要 `http_json` 响应里有 `documents`、`items`、`results`、`hits` 或 `matches` 列表，runtime 也会自动从 `snippet/content/text/excerpt/summary/description/body/...` 提炼 snippets；列表项里的 `metadata/document/payload/chunk/node/...` 多层嵌套对象也会受控向下解析，且当优先级更高的 `documents` 只有 id/title 元数据时会继续降级查看后续别名列表，避免“真实检索已成功、但 trace follow-up 仍因为没手工补 chunks、字段名不是 documents 或正文藏在 vector metadata 而断链”。
  - 对 retrieval family 的 runtime override / real tool，如果上游只返回 `documents` / `documents_total` 且没有显式配置 `result_preview_keys`，默认 preview/output key 推断现在也会把 `documents_total` 带上；这样 docs-only real retrieval 结果不会再在 `tool_end` preview、result_summary、observation 与 export 回放里退化成空投影。对显式映射 `items` / `results` / `matches` 的 `http_json` 搜索工具，runtime 也会把这些常见列表别名转成可投影的数量字段，并继续从列表项里提炼 snippets，避免真实 provider 响应字段名不是 `documents/hits` 时摘要链或 RAG follow-up 断掉。
  - 对 docs-only 的真实 provider 检索结果，如果 `documents_total` 同时带有 `knowledge_base_id`，后端现在会在 live result summary、observation、session export markdown 与 mock final answer 中显示 provider KB 来源（例如 `from hosted-kb`），同时避免误落成本地默认知识库的 `from knowledge base ...` 文案；即使旧 trace / Tool observations 只有 `Hosted Search` / `Provider Search` label、没有显式 semantic meta，也会走同一条 provider KB 摘要规则。
  - 同一条 docs-only retrieval 推断链现在也会在默认 result output projection 中保留 `request_id`；即使 registry 没单独声明 `result_output_keys`，provider/real retrieval 的 result summary、observation、success output 与 export trace 仍能带出请求关联号。
  - 对 retrieval family 的 runtime override / real tool，如果上游返回的是 `hit_count` 命中投影，runtime 现在也会把 `request_id` 继续写进 result summary 与 observation；provider search 不会再出现安全 output 已保留请求关联号、但 trace/export 文案仍退化成 `Retrieved N hits.` 的割裂语义。
  - 对 `http_json` 的 real/provider calc，如果只映射了 `result` 却没显式声明 `result_output_keys`，runtime 现在也会在默认 output projection 中继续保留 `request_id`；同时对只返回 `result/request_id` 的真实计算结果，result summary 与 observation 也会直接输出 `Calculated result = ... (request id ...)`，不再退回 generic payload summary。
  - `MockLLMProvider` 的 Summary 语义现在也继续复用同一套 `request_id` 感知规则；real/provider retrieval 的 `hit_count + request_id` 以及 real/provider calc 的 `result + request_id` 在 mock final answer 中也不会再丢掉请求关联号或退回 generic payload 文案。
  - `chat_persistence_service` 与前端 workbench 的 trace/export display helper 现在也会在缺少显式 `result_summary` 时，继续从 safe output + semantic meta 回推出人类可读摘要；旧 trace、session export preview 与 typed payload 回放不再只能停留在 `Tool done: ...` 加原始 JSON。
  - task trace preview 与 session export preview 现也继续复用这条 inferred summary 语义；旧 preview 数据在缺少显式 `result_summary` 时，也会优先展示 `Retrieved ...` / `Calculated result = ...`，而不是保留 `Tool done: ...` 作为 excerpt 主文案。
  - 同一条 inferred summary 现在也会继续覆盖 preview-only 的旧 tool step；即使 step meta 里只剩 `output_preview`，或者历史 payload 把 `output_preview` 存成 JSON 字符串，planner/retrieval/calc 的 observation、task trace preview、task export markdown 与前端回放也会先恢复可解析结构化 preview，并优先显示 `Planned steps - ...` / `Retrieved ...` / `Calculated result = ...` 一类摘要。
  - 前端 workbench 的 `output_preview` 回放现在也和后端 preview helper 对齐到合法双层 JSON 字符串；旧 preview 如果写成 `"{\"result\":7,...}"`，UI 会先恢复结构化对象再显示摘要与 preview，不再停在 `Tool done: ...` 加 quoted JSON。
  - `chat_persistence_service` 的 display helper 现在也会在渲染 `Preview:` 行前恢复 quoted JSON `output_preview`；旧 step 不会再出现摘要已正确推断、但 preview 行仍是 `"{\"result\":...}"` 的半收口状态。
  - 同一条 safe-output fallback 现在也继续覆盖 `effective_result_output_keys` 已存在、但 step meta `output` 仍是 JSON 字符串的半迁移旧 payload；`build_tool_observation_entry(...)`、mock final answer、task trace preview 与 export display helper 会先按 output policy 恢复结构化安全 output，再推断 retrieval / calc / planner 摘要，不再退回原始 JSON 或重新透出被过滤字段。
  - 同一条 safe-output coercion 现在也覆盖合法双层 JSON 字符串形态的 `output`；`tool_runtime` 与 `chat_persistence_service` 会先把 `"{\"result\":7,...}"` 这类 payload 恢复成结构化对象，再按 `effective_result_output_keys` 裁剪，避免 observation 与 markdown meta 重新带出 quoted JSON 或旁路字段。
  - session export markdown / preview route 现在也补齐了 quoted JSON fallback：旧 `content_excerpt` 即使写成 `Output: "{\"result\":7,...}"` 这类双重转义字符串，route 也会先解回结构化 payload，再按语义裁出安全 output keys，避免 `kind/secret` 一类字段重新外溢到 markdown 回放。
  - session export markdown 的 direct-label preview 现在也会走同一条 quoted JSON 恢复：`Hosted Math: "{\"result\":7,...}"` 这类旧 excerpt 不再绕过 parser，而会继续推断 real calc/retrieval/planner 摘要与产品化标题。
  - 对历史里更松散的 `Hosted Math: "{"result":7,...}"` 形态，direct-label parser 也会只在内层看起来是 JSON object 时恢复结构化 payload，避免继续把旁路字段写进 markdown。
  - task export markdown / markdown meta 这一层现在也已补上同类防回归覆盖：JSON-string safe output 会继续通过 `get_trace_step_markdown_meta(...)` 与共享 trace display helper 按 `effective_result_output_keys` 裁成安全 output；`execution_kind=http_json` 的显式 `output_preview` 也会先做列表别名归一化与 preview key 投影，而不会把 `secret` 一类旁路字段重新写进任务导出或 `Preview:` 文案。
  - `MockLLMProvider` 的 final-answer observation parser 现在也会恢复 quoted JSON payload：合法双层 JSON 字符串与旧 excerpt 形态的 `"{"result":...}"` 都会先解回结构化对象，再走 real calc/retrieval/planner 摘要推断，不再把原始字符串或 `secret` 写回 Summary。
  - session export markdown builder 现也会继续归一旧 `trace_preview.content_excerpt` 里的 `Label: {...}` 与 `Tool done: ... Preview: ... Output: ...`；即使导出入口拿到的是老 preview 字符串，导出的 markdown 也会优先显示推断摘要，并对 `http_json` real retrieval 的显式 preview/output 片段做列表别名归一化和安全投影，避免把 `secret` 或坏 count 原样带回 markdown。
  - 对无法解析为 JSON 的旧 `http_json` raw `output_preview` / `output` 字符串 fallback，`build_tool_observation_entry(...)`、`chat_persistence_service` 的 trace display / markdown meta 与 `sessions` markdown export 现在也会复用同一套原始文本脱敏，清洗敏感 assignment、敏感字段路径与 bare bearer 片段，避免 malformed preview 绕过结构化 safe-output 链。
  - `MockLLMProvider` 的纯文本 observation fallback 现在也会清洗敏感字段路径与 bare bearer 片段；当最终回答上下文只剩不可解析的 `Provider Status: ... query_params.access_token Bearer ...` 旧文本时，Summary / Tool context 不会再把这些 raw 诊断写回最终回答。
  - `build_tool_observation_entry(...)` 现也会在缺少完整 `output`、但 step meta 里仍保留 safe output 或 preview output 的 real tool 场景下优先产出结果摘要；observation、mock final answer prompt 与导出回放不再退回 JSON-only 文案。
  - 同一个 observation fallback 现在还会在 registry/provider source 已经取不到、但 step meta 里仍保留 `semantic_family` 的 real tool 场景下继续生效；旧 trace、断链 source 与导出回放不会再因为 registry 缺席而退回 JSON-only observation。
  - 对那些更老的 real tool step meta，如果 `semantic_family` 已经缺失，但 `kind` 仍保留为 `provider_retrieval` / `provider_calc` 一类真实 structural family，同时 safe output / output keys 还在，`build_tool_observation_entry(...)` 现在也会继续推断 `Retrieved ...` / `Calculated result = ...` 摘要；builtin calculator 与 generic custom tool 仍保持原先更保守的 preview/JSON observation 形态。
  - `MockLLMProvider` 现在也会对 name-only 的旧 real/provider retrieval JSON observation 保持更保守的总结规则：如果 payload 里只有 `hit_count + knowledge_base_id`、但缺少显式 semantic 字段，只有 builtin/local retrieval label 才会继续输出 `from knowledge base ...`；`Provider Search` / `Hosted Search` 这类旧 real tool observation 不再被误写成本地知识库命中。
  - `MockLLMProvider` 的 final-answer observation summarizer 现在也会继续把旧 payload 里的 structural `kind` 当作 runtime semantic fallback；即使 observation 里没有 `tool_kind` / `semantic_family`，只要保留了 `provider_calc` 这类 real structural family，mock summary 也会继续输出 `Calculated result = ...`，而不是退回 generic payload output。
  - 同一条 name-only real retrieval 保守语义现在也继续贯通到 session trace preview/export 与无 registration 的 observation fallback：当 step meta / preview 里只剩 `hit_count + knowledge_base_id + request_id` 且 label 是 `Provider Search` / `Hosted Search` 这类 real retrieval 名称时，后端会优先产出 `Retrieved ... (request id ...)` 摘要，而不是误补本地 knowledge base 文案或退回 JSON-only observation。
  - 同一套保守 fallback 现在也继续覆盖只有 name-only label 的旧 real/provider calc：当 step meta、preview excerpt、observation，或 registry 中未显式声明语义族但 label 是 `Hosted Math` / `Provider Math` 的真实计算工具，只剩 `result + request_id` 时，后端 final answer、`build_tool_result_summary(...)`、`build_tool_observation_entry(...)`、task trace preview、session export markdown 与共享 trace display helper 也会优先产出 `Calculated result = ... (request id ...)`，而不是退回 generic payload / `Tool done:` 文案或在 summary helper 中断链。
  - 对 registry/source 中已接 `http_json`、但还没显式声明 `kind/runtime_semantic_kind/result_*_keys` 的 label-only real tools，`get_tool_effective_result_preview_keys(...)` / `get_tool_effective_result_output_keys(...)` 现在也会从 `Hosted Math` / `Hosted Search` / `Hosted Planner` 这类 name/label 推断默认投影：calc 使用 `expression/result/request_id`，retrieval 使用 `documents_total/hit_count/knowledge_base_id/request_id`，planner 使用 `plan/steps`，从而让 helper 级 preview/output/result-summary/observation 不再空投影；如果这类 real tool 已经显式配置 `result_preview_keys` 但缺省 `result_output_keys`，preview/output effective keys 会先过滤半迁移 legacy preview keys 里的敏感字段，再保留安全 preview keys，并按类型补齐诊断字段（retrieval 补 `knowledge_base_id/request_id`，calc 补 `request_id`，planner 保留 planner preview keys）；如果半迁移对象已经显式带了 `result_output_keys`，effective output keys 也会再次过滤敏感字段名；如果显式非空 preview/output keys 过滤后只剩敏感字段，helper 级 preview/output 与 success meta 会保持空投影，不再回退到默认 safe shape；底层 `normalize_tool_output_for_registration(...)` 也不会在这类 label-only real tool 输出里写入 `tool_kind: null`；`build_tool_runtime_semantics_meta(...)` 与 preflight `tool_details` 继续同步补出工具名级 `semantic_kind` 与 family 级 `semantic_family`。
  - `chat_persistence_service` 的 session export / trace preview 结果摘要 helper 现在也会继续把旧 preview payload 里的 structural `kind` 当作 runtime semantic fallback；像 `{"kind":"provider_calc","result":7,"request_id":"..."}` 这类老 excerpt 即使缺少 `tool_kind` / `semantic_family`，markdown 导出与 preview excerpt 也会继续产出 `Calculated result = ...` 摘要，而不是退回原始 JSON。
  - 同一个 `chat_persistence_service` helper 现在也会在 safe output 因 `effective_result_output_keys` 被裁掉 `kind` 时，继续回看原始 `tool.output` / `tool.output_preview` 里的 structural `kind`；因此 task trace preview、task export markdown 与共享 trace display 在旧 real calc payload 只把 `provider_calc` 留在 raw output 的场景下，也不会再退回 `Tool done: ...`。
  - `chat_persistence_service` 的 trace/session preview title 现在也会在显式 `semantic_kind` / `semantic_family` 缺失时，继续按 name-only real tool label 与结构化输出推断 `[retrieval]` / `[calculator]` / `[planner]`；像 `Hosted Search` / `Hosted Math` / `Hosted Planner` 这类旧 preview step 不会再只剩裸 title。
  - `sessions` markdown export builder 现在也会对旧 `trace_preview.title` 仍是裸 label 的 payload 继续补同一套 title 语义；因此历史 session markdown 里的 `Hosted Search` / `Hosted Math` / `Hosted Planner` 与 structural-kind calc preview heading 也会补成带 `[retrieval]` / `[calculator]` / `[planner]` 的产品化标题，同时仍保持对 name-only real retrieval 的保守摘要，不会误补本地 knowledge base 文案。
  - `sessions` markdown export builder 现在还会忽略 title 中那些仅用于展示的通用 `[retrieval] / [calculator] / [planner]` 标签对摘要推断的反向污染；因此旧 real retrieval preview 即使 heading 已经补成 `[retrieval]`，excerpt 仍是原始 JSON 时也不会被误摘要成 `from knowledge base ...`。
  - `MockLLMProvider` 与 `build_tool_observation_entry(...)` 现在也会把产品化 label 里的展示性 bracket descriptor 当成可剥离噪音；因此像 `Hosted Math [calculator]` 这类旧 real calc observation，即使 name 已经不是 canonical registry 名、又缺少显式 semantic hints，也会继续推断 `Calculated result = ... (request id ...)`，而不是退回 generic payload / JSON-only observation。
  - provider 规划结果里的产品化 extra-tool label 现在也会在 `_resolve_provider_tool_name(...)` 之前先剥掉同一层 bracket descriptor；因此像 `Fast Calculator [calculator]` 这类已经产品化过的 planner 输出，provider branch 也能继续稳定解回真实 registry tool name，而不会在 tool plan 归一化时被静默丢弃。
  - 同一层 bracket-strip 规则现在也补到了 `normalize_tool_registry_name(...)`，因此 `task_plan` 自己在消费历史 `planned_tool_names` 时，如果老 payload 把工具名写成 `calc_eval [calculator]` 这类产品化形式，planner steps 也会继续回放成 `Evaluate calculation` / `Retrieve supporting context` 一类语义步骤，而不是退回泛化 `Run ...`。
  - 同一层 bracket-strip 规则现在也补到了治理摘要的 `allowed_tool_labels` 归一化：当 task/session governance 里同时还有 canonical `allowed_tool_names` 可对齐时，像 `Calculator Suite [calculator]` 这类仅用于展示的旧标签会自动折叠回 canonical label，避免 export/governance 继续泄漏产品化展示噪音；session-level governance merge 遇到“旧 summary 里先残留了 label-only 产品化标签，后续 task 才补回 canonical tool name”的历史数据时，也会在聚合阶段把 stale label 去重掉，不再把两份标签一起外溢；而对直接持久化后的 session governance summary，只要 `profiles/provider_sources` 已经收敛成单一治理上下文，normalizer 也会按这条上下文挑选对应 source/profile 的 canonical label，而不会误回退到默认 source 的显示名。
  - 对直接来自 typed payload / `model_dump()` 的 task/session governance，`get_task_response_summary_from_task(...)`、`get_task_export_summary_from_task(...)`、`get_task_export_response_summary(...)`、`get_session_export_response_summary(...)`、`get_tasks_usage_dashboard_response_summary(...)`、task detail/list/usage dashboard route 以及 task/session export route builder 现在也会继续走同一层治理归一化；旧 typed governance 即使仍保留 `calc_eval` 这类内部名，只要 source/profile 已知，也会按对应 registry/source 解析成 canonical label。外层 response summary 已是 dict、但内层 governance 仍是 typed/model_dump 的半迁移 payload 也会在 task/detail/list/usage 与 session export route 侧被收口，同时保留原有 sparse/full payload 形态、response-ready trace/task model 身份与 service dict 信任边界，避免对外 response/export/usage 契约额外膨胀。
  - 对没有显式补 `runtime_semantic_kind` 的 noncanonical real tool，后端 runtime semantic 现在也会在运行态优先保留工具自身名称作为 `semantic_kind`，并继续把 retrieval/calc/planner family 留在 `semantic_family`；这样 `Provider Search` / `Provider Math` 这类 real tool 的 action trace、observation 与 rag follow-up 不会再塌回 builtin family 名称，而 settings/preflight 的治理视角仍保持 family 级摘要与 preview/output key 推断。
  - trace/session preview excerpt 的默认截断长度也已同步上调；这类 `request_id`、safe output preview 与 inferred summary 组合不会再在 `req-...` 处被过早截断。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 与 retrieval follow-up 已贯通 action step、`tool_start/tool_end`、persisted trace、export 与 mock final answer。
  - real/provider retrieval 与 runtime override real tool 已不再在 result summary、observation、rag follow-up 或 task export 中伪造默认本地 knowledge-base 语义。
  - name-only success/helper fallback 会优先复用 configured registry 或 step meta 中已落下的 label / result summary / output preview，而不是退回 provider 通用名或原始 JSON；即使原始 `output` 未保留成 dict，observation、success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 聚合仍会优先沿 step meta 或 typed payload 的结构化结果回放；task/session export route builder 也会在 plain dict summary 内继续浅归一化内层 `messages`、task `trace_preview`、task trace `rag_chunks/steps` 的 `model_dump()` 对象，同时保留 response-ready Pydantic model 身份；会话 Memory query、RAG ingest/query、RAG route 层与 shared knowledge-base merge 的 metadata、query payload root、document row、row list，以及 session create/detail/list/messages/export、task/session usage、task create/detail/list/cancel/trace/delta/export/stream-reconnect、auth register/refresh/session list/user list、audit log list 这些 outward summary route，以及 `chat_persistence_service` 的 task trace/usage/response/export/delta、`task_rows_*` 批量聚合 helper、task/session export response summary 外层 payload，以及 task/session export builder 路由入口，也已接受 typed Chroma / typed service payload / `model_dump()` 行，不再在归一化阶段静默清空或直接报错，nested metadata 也会继续保留。
  - `MockLLMProvider` 的 final-answer observation parser 现在也会从 payload 内层 `safe_output` / `output` / `output_preview` / `result_preview` JSON 字符串恢复结构化结果，并继承父级 semantic / request 上下文；半迁移 observation 不再退回 `output_preview=...` generic summary，也不会把旁路字段写进最终 Summary。
  - runtime helper、governance/export、registry diagnostics 与 planner 输入归一化已统一兼容旁路结构化载荷；当前 provider planner 与真实 `OpenAICompatibleLLMProvider` 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
- `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`1334/1334`）
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

- 后端当前主线与 README / 前端 README / 实时计划一致：最近收尾的 final-answer、observation、trace/export fallback 与 `http_json` execution diagnostics 已基本闭环。
- 下一阶段后端优先做 `real-tool-execution`，也就是把 provider/source 中已经能注册和规划的 real tools 继续推进到真实请求模板、真实上游响应映射、result preview/output、runtime semantic、trace/observation/export 诊断的一体化执行链。
- registry/source 治理继续作为第二优先级：保持 loader_factory、file-backed source、selected source、settings/preflight、per-tool diagnostics 与 runtime semantic 使用同一套语义。
- 单机任务队列/并发治理与更细粒度 RAG 治理保留为后续模块，不与当前真实工具执行主线混在同一轮里改外部契约。

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- `app/providers/`：provider 抽象、mock provider、OpenAI-compatible remote provider
- `app/services/chat_execution_service.py`：任务流编排与 SSE 主链
- `app/services/tool_runtime.py`：tool registry / provider / source、tool runtime helper、preflight、diagnostics、result preview/output/summary 语义
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/chroma_rag_service.py`：RAG ingest/query/status、knowledge base list/clear/delete 与 shared/private 语义
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 usage，供任务列表、导出与 dashboard 复用

## HTTP 接口（摘要）

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- `GET /api/auth/users`（admin only）
- `GET /api/auth/me`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/export/json`
- `GET /api/sessions/{session_id}/export/markdown`
- `GET /api/sessions/{session_id}/memory/status`
- `GET /api/sessions/{session_id}/usage/summary`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=&query=`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`
- `GET /api/tasks/usage/summary`
- `GET /api/tasks/usage/dashboard`
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/query`
- `GET /api/rag/knowledge-bases`
- `POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}`

补充约定：

- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`。
- `GET /api/tasks*` 相关响应包含 `status_normalized`、`status_label`、`status_rank`。
- usage 接口支持来源维度统计：`provider / estimated / mixed / legacy`。
- `shared-*` 知识库走共享命名空间；admin 可写，普通用户只读。

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：

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

对齐说明：

- `event: trace` 的 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。
- `tool_start/tool_end` 使用与 action 节点一致的 `step_id`，与 trace 节点一一对齐。
- `trace/delta?after_seq=` 可在任务流式进行中拉取阶段性 `observation` 刷新内容。
- remote provider 异常会被归一成结构化错误码，并在 SSE `error` 中透传稳定的 `code / fatal / retryable / detail / status_code`。

## 当前实现边界

- `trace/delta` 支持 `limit` 参数控制单次增量返回量；当前默认 `200`，最大 `500`。
- `GET /api/tasks/usage/summary` 与 `GET /api/tasks/usage/dashboard` 都已支持 usage 来源统计；当前来源语义是 `provider / estimated / mixed / legacy`。
- 任务相关对外读取已优先走 task row 上的规范化治理摘要与 parsed trace 主干，不再鼓励在 route 层继续做 sibling fallback。
- 默认 settings 语义是：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`；remote `base_url/api_key` 继承链已打通到 get/save/validate。
- shared RAG 语义当前保持 `shared-*` 命名空间约定：admin 可写共享库，普通用户对共享库只读。
- 当前后端主线优先补真实工具执行与 registry-aware helper 语义，不优先继续扩写 archived runtime spec。
- 当前 registry extra tool / override 的真实执行器入口先以 `execution.kind=http_json` 为主；请求模板、响应字段映射与既有 runtime semantic/preview/export 主链保持同一契约，不额外发散独立 route。
- 显式给 tool 配了 `execution` 时，当前语义是“宁可报配置错，也不回退 stub”；这样 provider/source 治理不会把 real tool 假阳性地跑成本地模板行为。
- provider/source/global settings 侧当前也会把静态可判定的 `execution` 坏配置归一成 registry diagnostics；下一步优先继续补更细粒度的模板/映射诊断，而不是改外层接口。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- RAG collection 命名：`kb_{user_hash}_{knowledge_base_id}`
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务后的摘要写入为 best-effort

### 通俗分工（后端视角）

- `PostgreSQL`：业务主存储，保存用户、会话、消息、任务、trace、usage、设置、审计。
- `Chroma Memory`：会话级语义记忆，服务当前对话上下文。
- `Chroma RAG`：知识库级文档检索，服务跨会话复用的资料。

## 本地启动

推荐使用 **Python 3.14**（与 `compose.full.yml`、根目录 `.python-version`、CI 保持一致）。

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端，可在仓库根目录执行：

```bash
./start_insightagent.command
```

如需将历史 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

常用校验：

```bash
python scripts/e2e_baseline.py --base-url http://127.0.0.1:8000
python scripts/e2e_main_path.py --base-url http://127.0.0.1:8000
python scripts/e2e_export_consistency.py --base-url http://127.0.0.1:8000
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout
backend/.venv/bin/python scripts/test_tool_runtime_slice.py
```

如需 Memory / RAG 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

当前常用运行参数：

- `TRACE_PERSIST_MIN_INTERVAL_SEC`：trace 增量持久化最小间隔
- `STREAM_RECONNECT_POLL_FAST_SEC`：running reconnect 快轮询间隔
- `STREAM_RECONNECT_POLL_MAX_SEC`：running reconnect 慢轮询上限
- `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`：reconnect heartbeat 间隔
- `TASK_TIMEOUT_SEC`：任务超时秒数

## 当前约束

- 当前外部 SSE / trace / export / e2e 契约尽量保持稳定，优先做内部 runtime/helper 收口。
- 当前主线优先真实工具执行本体与上游协议接入，不优先继续扩大旧 fallback 兼容面，也不继续维护已归档的 runtime spec 历史文档。
- 文档只保留高信号当前状态，不继续累积按天流水账。
