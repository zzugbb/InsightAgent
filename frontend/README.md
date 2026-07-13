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
  - 当后端显式配置了无效 `execution` 时，当前策略是 fail-fast 而不是静默回退 stub runner；前端后续看到的是明确的配置错误，而不是“看似成功、实际跑了本地模板”的假语义。
  - 同时，provider/source diagnostics 现在也会把这类静态可判定的坏配置提前归一成 `invalid/tool_executions` 项；设置面板不需要等任务真跑起来，source diagnostics 就能先提示 real tool 的执行器配置已经坏掉。
  - 对 `http_json.execution.method` / `timeout_ms` / `default_timeout_ms` 这类真实请求协议字段，后端现在也会提前治理：拼错 method 不再静默变成 `GET`，坏 timeout（含 fractional/sub-millisecond、非有限数或超大整数）不再裸抛构建异常，而是作为 per-tool execution diagnostic 进入设置/回放链路，前端看到的是明确配置错误。
  - 后端对 `http_json` real tool 新增的安全 `execution_summary` 也会随 tool meta 进入 SSE/trace/export 主链；即使前端当前还没单独做专门 UI，这份 method/origin/path/query-body/result-field 概览已经会稳定跟着工作台回放语义走。
  - 后端现在还支持 `http_json` 执行模板读取运行时 `settings_api_key/settings_base_url/tool_registry_provider_source` 上下文，并在 `headers/url/query/json_body` 中使用 `${...}` 做安全字符串插值；前端继续只消费安全 `execution_summary` 与 diagnostics，不会把 secret 模板值直接带进设置面板或 trace UI。
  - 即使 provider/source 改成 file-backed registry manifest，后端也会继续把同一套 source 级模板上下文灌进 `extra_tools/overrides`；因此前端看到的 source diagnostics、tool detail summary 与运行态 trace 语义不会再因配置承载形态不同而分叉。
  - 对 `http_json` 模板里拼错的 `settings_*` / `tool_registry_*` 运行时变量，后端现在会更早在 source diagnostics 中给出 `invalid/tool_executions` 提示；前端不必等真实 tool 执行到上游请求阶段，设置治理面就能先看出是模板变量 typo，而不是网络/权限波动。
  - 对那些只有任务执行时才知道会不会缺失的 `$top_k`、`$precision` 一类模板输入，后端现在也会在真正发请求前直接报出 `query_params.limit`、`json_body.precision` 这类缺参路径；前端看到的会是明确的运行时模板缺参错误，而不是“请求发出去了但语义残缺”的假成功或假网络问题。
  - 对 `headers/query_params/json_body` 里只有空白字段名这类原本会被请求构建过程静默吞掉的配置，后端现在也会在 settings/source diagnostics 与 preflight 阶段提前报出 `invalid_tool_executions`；前端设置治理面可以更早指出“请求模板字段名本身就坏了”。
  - 对显式配置了 `response_path` 的 real tool，如果后端在真实响应里找不到这条路径，或者配置本身只是空白字符串，现在也会直接报配置/协议错误，而不是静默退回根 payload；前端看到的会是明确的响应映射失败，而不是 trace/export 中混入根响应兜底后的假结果。
  - 对显式配置了 `result_fields` 的 real tool，如果所有字段映射都没命中，后端现在也会直接报出映射失败，而不是返回空结果对象；前端看到的会是明确的 response mapping 错误，不再需要从“运行成功但没有任何 preview/output”这种假信号里倒推问题。
  - 对 `result_fields.*` 里静态就能看出的坏 path，后端现在也会在 settings/source diagnostics 与 preflight 阶段提前报出 `invalid_tool_executions`；像 path 本身坏掉、`result_fields` 里混入空白字段名、只有空白字段名，或显式给了空对象这类问题，前端设置治理面都能更早指出，而不是只在任务失败后回放运行态错误。
  - workbench trace subtitle 与搜索现在会直接消费 `execution_summary`；真实工具运行中的 `POST https://.../search`、response path、result fields 等安全摘要已经能在前端回放和检索里直接看到。
  - model settings modal 的 tool detail summary 现在也会直接显示 `execution_summary` 的 endpoint 与 query/body/response-field 摘要；provider/source 治理面不需要进入运行态 trace，就能先看出某个 `http_json` real tool 会打到什么路径、响应会映射到哪些字段。
  - model settings modal 的 tool detail summary 现在也会继续拼出 per-tool `execution_diagnostics`；source diagnostics 不再只告诉你“这个 source 有坏配置”，而是能直接看出具体是哪个 real tool 的 `http_json` 配置出错。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续进入运行态 tool meta、live store 与 trace subtitle/search；如果坏掉的 real tool 真被规划并执行到，前端不需要只看泛化 error message，就能直接看到是哪条执行配置坏了。
  - 对 retrieval family 的 `http_json` real tool，后端现在也会从 `documents` 列表自动提炼 snippets，不再要求上游额外伪造本地 stub 风格的 `chunks`；前端看到的 rag follow-up / trace 回放会因此更接近真实检索响应语义。
  - 对 docs-only 的 real retrieval 结果，后端现在也会把 `documents_total` 纳入默认 preview/output key 推断；前端在 `tool_end` 预览、trace/export 回放里不再只看到空 preview 或退化文案，而是能继续看到文档数量级摘要。
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
  - task export markdown / markdown meta 这一层现在也已补上同类防回归覆盖；因此前端发起任务导出或消费旧 trace markdown meta 时，JSON-string safe output 也会继续按 output policy 裁成安全字段，而不会把旁路字段带回导出结果。
  - 后端 mock final-answer observation parser 现在也会恢复 quoted JSON payload；因此前端看到的最终回答在旧 `Tool observations:` 只剩双层 JSON 字符串或 `"{"result":...}"` excerpt 时，也会继续显示 `Calculated result = ...` 这类摘要，而不是原始 JSON 或旁路字段。
  - 后端 session export markdown builder 现在也会把旧 `trace_preview.content_excerpt` 里的 `Label: {...}` 与 `Tool done: ... Preview: ... Output: ...` 归一成推断摘要；前端发起的会话 markdown 导出和工作台内的 trace/export 回放文案会更一致。
  - 后端 observation helper 现在也会在只剩 safe output / preview output 的 real tool 场景下优先产出结果摘要；前端看到的最终回答、observation 回放与导出文案会更接近工作台主展示链。
  - 当 registry/source 已经取不到、但 step meta 里仍保留 `semantic_family` 与结构化 output 时，后端 observation helper 现在也会继续推断 real tool 摘要；前端工作台、最终回答与导出回放不会因为 registry 缺席而退回 JSON-only observation。
  - 当更老的 real tool step meta 连 `semantic_family` 都已经丢失、但还保留了 `provider_retrieval` / `provider_calc` 这类 structural `kind` 与结构化 safe output 时，后端 observation / final-answer 链也会继续推断 `Retrieved ...` / `Calculated result = ...` 摘要；前端最终看到的回放与最终回答因此更少退回 JSON-only 文案，而 builtin/generic tool 仍保持原先更保守的显示语义。
  - 后端 mock final-answer 现在也会把 name-only 的旧 real/provider retrieval observation 视作更保守的 real tool 语义；前端看到的最终回答不再把 `Provider Search` / `Hosted Search` 这类旧 observation 误写成默认本地 knowledge-base 命中，而 builtin `Knowledge Retrieval` 仍保留本地语义。
  - 后端 mock final-answer 现在也会继续识别旧 observation payload 里的 structural `kind`（例如 `provider_calc`）；因此前端最终看到的最终回答在这类旧 real calc observation 场景下，也会更稳定地保留 `Calculated result = ...` 语义，而不是退回 generic payload output。
  - 对只有 name-only label 的旧 real/provider calc，前端 workbench display 现在也会和后端 final answer / observation / export preview 保持一致：当 step meta 或 preview 里只剩 `result + request_id`，且 label 是 `Hosted Math` / `Provider Math` 这类 real calc 名称时，会优先显示 `Calculated result = ... (request id ...)`，而不是继续停在 `Tool done: ...`。
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
  - task/session preview excerpt 现在也会尽量保留完整的 `request_id` 与 safe output 片段；前端不会再经常只看到 `req-...` 这种被后端 preview 截断的半残摘要。
  - real/provider retrieval 与 runtime override real tool 的 follow-up、result summary、observation、导出回放已不再误写成本地默认知识库命中。
  - extra/real tool 的注册语义、safe output 与计划项输入会优先沿 configured registry 继承；后端 provider planner 与真实 remote provider 现在也共用一套 response text / usage 提取语义，能稳定消费 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 usage alias、脏 usage 值与流式 delta 文本字段变体；task/session export route builder 也会在 plain dict summary 内继续浅归一化内层 `messages`、task `trace_preview`、task trace `rag_chunks/steps` 的 `model_dump()` 对象，因此前端发起 JSON/Markdown 导出或回放半迁移历史 payload 时，不会因为最后一层 response model 只接受 dict 而中断。
  - 后端 mock final-answer observation parser 现在也会恢复 payload 内层 `safe_output` / `output` / `output_preview` / `result_preview` JSON 字符串；因此前端最终回答在旧 observation 只剩嵌套 preview 时，也会继续显示 real calc / real retrieval 摘要，而不是 `output_preview=...` 或旁路字段。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`948/948`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`68/68`）
  - `cd frontend && npm run build` 通过
  - `cd frontend && npx playwright test e2e/usage-dashboard.spec.ts -g "task detail replay preserves retrieval_only registry trace metadata" --reporter=line` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-edge-cases.spec.ts -g "cancel allows immediate resend with identical prompt without dedupe loss" --reporter=line` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-edge-cases.spec.ts -g "cancel allows immediate resend with identical prompt without dedupe loss|mock cancel does not show retry affordance and send recovers quickly|trace delta sync retries, pauses in background, and resumes when foreground returns" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`9/9`）
  - `cd frontend && npx playwright test e2e/workbench-remote-errors.spec.ts -g "remote cancel enters cooldown and recovers send" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test e2e/workbench-main-path.spec.ts -g "workbench main path covers trace, rag and task/session export" --reporter=line --workers=1` 通过（Chromium/Firefox/WebKit，`3/3`）
  - `cd frontend && npx playwright test --project=chromium --reporter=line --workers=1` 通过（完整 Chromium e2e，`47/47`）
  - `git diff --check` 通过

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
- 文档只保留当前能力、当前主线、关键实现位置和最近校验基线，不继续累积长串历史同步记录。
