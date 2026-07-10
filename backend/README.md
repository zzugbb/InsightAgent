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
  - 若 registry `extra_tools` / `overrides` 显式声明了 `execution`，但 `kind` 缺失、shape 非法或写成不支持的执行器，tool runtime 现会直接返回配置错误，不再静默回退到模板 stub runner。
  - 同一批坏掉的 `execution` 配置现在也会进入 `invalid/tool_executions` diagnostics：file/source/global settings、selected source、configured provider preflight 以及 trace/audit 可以在真正跑 tool 之前就把问题暴露出来，而不是只在运行期 fail-fast。
  - 对已接上 `http_json` 的 real tool，runtime 现在还会生成一份安全的 `execution_summary` 并挂到 tool semantic meta 上；`tool_start`、action step、持久化 trace 与 export 回放都能看到 method、origin/path、query/body/result-field 概览，同时避免把 header value 等敏感配置直接写进 trace。
  - `http_json` execution template 现在也会复用运行时 settings/source 上下文：global extra tool、source extra tool、registry override 与 file-backed source 都可以在 `headers/url/query/json_body` 中读取 `settings_api_key`、`settings_base_url`、`tool_registry_provider_source` 等变量，并支持 `${...}` 字符串插值来拼接 bearer/header 模板，而无需把敏感值硬编码进 registry 配置。
  - file-backed source manifest 里的 `extra_tools` / `overrides` 现也继续走同一套 source 级模板上下文传递；把 source 从内联 JSON 切到 `registry_file` 后，`tool_registry_provider_source` 一类运行时变量不会再丢失。
  - 对 `http_json` 模板中的保留命名空间变量，runtime 现在也会做更细粒度静态诊断：`settings_*` / `tool_registry_*` typo 会直接落进 `invalid_tool_executions`，并在 runner 构建时继续 fail-fast，而不是静默丢掉 header/query 参数后才在真实上游请求里暴露成旁路错误。
  - 对只能到 tool 真正执行时才知道是否缺失的请求模板变量，`http_json` runner 现在也会在发请求前直接 fail-fast：像 `$top_k`、`$precision` 这类缺参会明确报到 `query_params.limit`、`json_body.precision` 等路径上，而不是先静默删字段再把问题伪装成上游协议或网络异常。
  - 对 `headers/query_params/json_body` 里那些静态就能看出的空白字段名，settings/source diagnostics 与 configured provider preflight 现在也会提前报成 `invalid_tool_executions`；这类原本会在 request normalizer 中被静默忽略的坏配置，不必再等运行时才旁路消失。
  - 对显式声明了 `response_path` 的 `http_json` real tool，runtime 现在也不再在路径缺失时偷偷退回根响应 payload；如果上游响应里找不到该路径，或者配置里给的是空白 `response_path`，都会直接按配置/协议错 fail-fast，避免 response mapping 坏掉后仍产出看似“有结果”的假成功。
  - 对显式声明了 `result_fields` 的 `http_json` real tool，runtime 现在也会在“所有字段映射都落空”时直接 fail-fast，并把失败的映射项一起带出来；上游响应结构漂移或 mapping 写错时，不会再默默返回空输出对象，把真实配置/协议问题伪装成成功。
  - 对 `result_fields.*` 里那些静态就能看出的坏 path，settings/source diagnostics 与 configured provider preflight 现在也会提前报成 `invalid_tool_executions`；像非字符串 path、空白 path，`result_fields` 里混入空白字段名、根本没有有效字段名，或显式给了空对象这类问题，都不必再等真实请求出去后才变成运行时错误。
  - 前端 workbench 的 trace subtitle/search 现也开始消费这份 `execution_summary`；后端这边输出的安全执行摘要已经不再只停留在 JSON trace/export 里，而是能直接参与 UI 回放与检索。
  - configured provider preflight、settings summary/validate 的 `tool_details` 现在也继续带上 `execution_summary`；真实工具的 endpoint 与 query/body/response-field 摘要已经不再只存在于运行期 trace，settings 治理面就能先读到。
  - source/settings/preflight 的 `tool_details` 现在还会继续挂上 per-tool `execution_diagnostics`；`invalid/tool_executions` 不再只停留在 source 级 summary，治理面可以直接指出是哪个 real tool 的 `http_json` 配置坏掉了。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续挂进 runtime tool semantic；对显式声明了坏执行器的 real tool，`tool_start`、`tool_end`、error meta 与 action trace step 会直接带出配置诊断，不再只有 settings/preflight 才知道“为什么这个工具必然失败”。
  - retrieval family 的 real tool 现在也不再要求上游必须额外返回本地 stub 风格的 `chunks`：只要 `http_json` 响应里有 `documents` 列表，runtime 也会自动从 `snippet/content/text/body/...` 提炼 snippets，继续产出 rag follow-up，避免“真实检索已成功、但 trace follow-up 仍因为没手工补 chunks 而断链”。
  - 对 retrieval family 的 runtime override / real tool，如果上游只返回 `documents` / `documents_total` 且没有显式配置 `result_preview_keys`，默认 preview/output key 推断现在也会把 `documents_total` 带上；这样 docs-only real retrieval 结果不会再在 `tool_end` preview、result_summary、observation 与 export 回放里退化成空投影。
  - 同一条 docs-only retrieval 推断链现在也会在默认 result output projection 中保留 `request_id`；即使 registry 没单独声明 `result_output_keys`，provider/real retrieval 的 result summary、observation、success output 与 export trace 仍能带出请求关联号。
  - 对 retrieval family 的 runtime override / real tool，如果上游返回的是 `hit_count` 命中投影，runtime 现在也会把 `request_id` 继续写进 result summary 与 observation；provider search 不会再出现安全 output 已保留请求关联号、但 trace/export 文案仍退化成 `Retrieved N hits.` 的割裂语义。
  - 对 `http_json` 的 real/provider calc，如果只映射了 `result` 却没显式声明 `result_output_keys`，runtime 现在也会在默认 output projection 中继续保留 `request_id`；同时对只返回 `result/request_id` 的真实计算结果，result summary 与 observation 也会直接输出 `Calculated result = ... (request id ...)`，不再退回 generic payload summary。
  - `MockLLMProvider` 的 Summary 语义现在也继续复用同一套 `request_id` 感知规则；real/provider retrieval 的 `hit_count + request_id` 以及 real/provider calc 的 `result + request_id` 在 mock final answer 中也不会再丢掉请求关联号或退回 generic payload 文案。
  - `chat_persistence_service` 与前端 workbench 的 trace/export display helper 现在也会在缺少显式 `result_summary` 时，继续从 safe output + semantic meta 回推出人类可读摘要；旧 trace、session export preview 与 typed payload 回放不再只能停留在 `Tool done: ...` 加原始 JSON。
  - task trace preview 与 session export preview 现也继续复用这条 inferred summary 语义；旧 preview 数据在缺少显式 `result_summary` 时，也会优先展示 `Retrieved ...` / `Calculated result = ...`，而不是保留 `Tool done: ...` 作为 excerpt 主文案。
  - 同一条 inferred summary 现在也会继续覆盖 preview-only 的旧 tool step；即使 step meta 里只剩 `output_preview`，或者历史 payload 把 `output_preview` 存成 JSON 字符串，planner/retrieval/calc 的 observation、task trace preview、task export markdown 与前端回放也会先恢复可解析结构化 preview，并优先显示 `Planned steps - ...` / `Retrieved ...` / `Calculated result = ...` 一类摘要。
  - session export markdown builder 现也会继续归一旧 `trace_preview.content_excerpt` 里的 `Label: {...}` 与 `Tool done: ... Preview: ... Output: ...`；即使导出入口拿到的是老 preview 字符串，导出的 markdown 也会优先显示推断摘要，并继续保留安全 preview/output 片段。
  - `build_tool_observation_entry(...)` 现也会在缺少完整 `output`、但 step meta 里仍保留 safe output 或 preview output 的 real tool 场景下优先产出结果摘要；observation、mock final answer prompt 与导出回放不再退回 JSON-only 文案。
  - 同一个 observation fallback 现在还会在 registry/provider source 已经取不到、但 step meta 里仍保留 `semantic_family` 的 real tool 场景下继续生效；旧 trace、断链 source 与导出回放不会再因为 registry 缺席而退回 JSON-only observation。
  - 对那些更老的 real tool step meta，如果 `semantic_family` 已经缺失，但 `kind` 仍保留为 `provider_retrieval` / `provider_calc` 一类真实 structural family，同时 safe output / output keys 还在，`build_tool_observation_entry(...)` 现在也会继续推断 `Retrieved ...` / `Calculated result = ...` 摘要；builtin calculator 与 generic custom tool 仍保持原先更保守的 preview/JSON observation 形态。
  - `MockLLMProvider` 现在也会对 name-only 的旧 real/provider retrieval JSON observation 保持更保守的总结规则：如果 payload 里只有 `hit_count + knowledge_base_id`、但缺少显式 semantic 字段，只有 builtin/local retrieval label 才会继续输出 `from knowledge base ...`；`Provider Search` / `Hosted Search` 这类旧 real tool observation 不再被误写成本地知识库命中。
  - `MockLLMProvider` 的 final-answer observation summarizer 现在也会继续把旧 payload 里的 structural `kind` 当作 runtime semantic fallback；即使 observation 里没有 `tool_kind` / `semantic_family`，只要保留了 `provider_calc` 这类 real structural family，mock summary 也会继续输出 `Calculated result = ...`，而不是退回 generic payload output。
  - 同一条 name-only real retrieval 保守语义现在也继续贯通到 session trace preview/export 与无 registration 的 observation fallback：当 step meta / preview 里只剩 `hit_count + knowledge_base_id + request_id` 且 label 是 `Provider Search` / `Hosted Search` 这类 real retrieval 名称时，后端会优先产出 `Retrieved ... (request id ...)` 摘要，而不是误补本地 knowledge base 文案或退回 JSON-only observation。
  - 同一套保守 fallback 现在也继续覆盖只有 name-only label 的旧 real/provider calc：当 step meta、preview excerpt 或 observation 里只剩 `result + request_id`，且 label 是 `Hosted Math` / `Provider Math` 这类 real calc 名称时，后端 final answer、`build_tool_observation_entry(...)`、task trace preview、session export markdown 与共享 trace display helper 也会优先产出 `Calculated result = ... (request id ...)`，而不是退回 generic payload / `Tool done:` 文案。
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
  - runtime helper、governance/export、registry diagnostics 与 planner 输入归一化已统一兼容旁路结构化载荷；当前 provider planner 与真实 `OpenAICompatibleLLMProvider` 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`919/919`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`61/61`）
  - `git diff --check` 通过

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
- 当前主线优先真实工具执行语义，不优先继续维护已归档的 runtime spec 历史文档。
- 文档只保留高信号当前状态，不继续累积按天流水账。
