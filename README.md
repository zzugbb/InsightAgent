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
  - 显式声明了 `execution` 但 `kind` 缺失、类型错误或写成不支持的执行器时，runtime 现会直接 fail-fast，而不是悄悄退回模板 stub runner。
  - 对 `execution` 的坏配置也不再只能等到运行期才炸出错：file/source/global settings 侧现在会把它们归一成 `invalid/tool_executions` diagnostics，继续沿 selected source、settings summary/validate、configured provider preflight 与 trace/audit 主链提前暴露。
  - `http_json` real tool 的安全执行摘要现也会进入 tool runtime semantic：`tool_start`、action step meta、持久化 trace 与 export 回放可以直接看到 method、origin/path、query/body/result-field 概览，而不会把 header value 或其他敏感配置原样透出。
  - `http_json` 执行模板现已继续支持运行时上下文与字符串插值：global extra tool、provider source extra tool、registry override、file-backed source 都可以在 `headers/url/query/json_body` 中读取 `settings_api_key`、`settings_base_url`、`tool_registry_provider_source` 等安全上下文，并通过 `${...}` 形式拼接鉴权/header 模板，而不用把 secret 明文写进 trace/export。
  - file-backed source 的 registry manifest 现在也和内联 source 配置使用同一套运行时模板语义：manifest 内的 `extra_tools` 与 `overrides` 都会继续继承 source 级 `provider_source_name`，不会再出现“source 内联配置能吃到上下文、切到 `registry_file` 就退化”的分叉行为。
  - `http_json` 模板里如果把保留运行时变量写错，例如 `settings_*` / `tool_registry_*` 命名空间 typo，当前会在 settings/source diagnostics 阶段直接归一成 `invalid/tool_executions`，同时运行时仍保持 fail-fast，不再静默丢 header/query 后才在上游请求里表现成假性网络或协议问题。
  - 对 `http_json` 请求模板里那些只能到运行时才知道是否齐备的输入变量，例如 `$top_k`、`$precision`，当前 runner 也会在真正发请求前直接 fail-fast，并把缺失变量与 `query_params.limit`、`json_body.precision` 这类路径一起报出来，不再静默删字段后发出半残 HTTP 请求。
  - 对 `headers/query_params/json_body` 里只有空白字段名这类本来会被静默吞掉的请求模板配置，当前 settings/source diagnostics 与 preflight 也会提前归一成 `invalid/tool_executions`，不再等到 runner 正常化请求对象时再悄悄忽略。
  - 对显式声明了 `response_path` 的 `http_json` real tool，当前 runner 也不再悄悄退回根 payload：如果上游响应里根本找不到这个路径，或者配置里给的是空白 `response_path`，都会直接按配置/协议错 fail-fast，避免把坏掉的响应映射伪装成“工具还能跑，只是结果有点怪”。
  - 对显式声明了 `result_fields` 的 `http_json` real tool，如果所有字段映射都落空，当前 runner 也会直接 fail-fast，并把失败的映射项一起报出来；这样上游响应漂移或 registry mapping 写错时，不会再返回空结果对象伪装成成功执行。
  - 对 `result_fields.documents_total: 123`、`result_fields.request_id: " "`，以及 `result_fields` 里混入空白字段名、只有空白字段名或干脆是空对象这类明显坏掉的映射配置，当前 settings/source diagnostics 与 preflight 也会提前归一成 `invalid/tool_executions`，不必再等到任务真正执行时才暴露。
  - workbench trace subtitle/search 现也开始消费这份 `execution_summary`：真实工具不仅能在后端 trace/export 里留下安全执行摘要，前端回放与检索也能直接按 `POST https://.../search`、response path、result fields 这类信息排障。
  - settings/preflight 的 `tool_details` 与前端 model settings tool detail summary 现也继续透出并展示 `execution_summary`；不用进任务 trace，就能先看出某个 real tool 当前会打到哪类 HTTP endpoint，以及大致的 query/body/response-field 形态。
  - source/settings/preflight 的 `tool_details` 现在还会把 `invalid/tool_executions` 继续下沉成 per-tool `execution_diagnostics`；不需要只看 source 级 diagnostics summary，也能直接定位是哪个 real tool 的 `http_json` 配置坏了。
  - 同一份 per-tool `execution_diagnostics` 现在也会继续挂进 runtime tool semantic：坏掉的 real tool 一旦真的进入任务执行，`tool_start/tool_end`、action trace meta、前端 live store 与 trace subtitle/search 也能直接看到是哪条执行配置坏了，而不再只有 settings/preflight 能解释错误来源。
  - retrieval family 的 real tool 现在也不再强依赖本地 stub 风格的 `chunks` 字段：`http_json` 只要返回 `documents` 列表，runtime 也会从 `snippet/content/text/body/...` 中自动提炼 follow-up 片段，继续打通 rag follow-up、trace 与 observation 主链。
  - 对 retrieval family 的 runtime override / real tool，如果上游只返回 `documents` / `documents_total` 而没有显式配置 `result_preview_keys`，默认 preview/output key 推断现在也会显式覆盖 `documents_total`；docs-only 检索结果不再在 `tool_end` preview、result_summary、observation 与 trace/export 回放里退化成空投影或泛化文案。
  - 同一路 docs-only retrieval fallback 现在还会在默认 output key 推断里保留 `request_id`；因此真实 provider/real search 工具即使没单独声明 `result_output_keys`，`result_summary`、observation、success output 与导出回放也能继续带出上游请求关联号，而不会只剩文档数量。
  - tool execution 的规范化输入、preview/output/result-summary、runtime semantic 已贯通 action step、`tool_start/tool_end`、持久化 trace、export 与 mock final answer。
  - retrieval / observation / helper fallback 已不再把 provider/real tool 误解释为默认本地知识库语义，name-only 路径也会优先复用已落盘的 registry 语义；即使原始 `output` 缺失，observation、success output、markdown export meta、task-row batch trace preview、session export trace preview，以及 task/session export 的 `rag_chunks`、task rows、session export payload `tasks/messages/stats` 聚合也会优先复用 step meta 或 typed payload 中已落下的结构化结果；会话 Memory query、RAG ingest/query、RAG route 层与 shared knowledge-base merge 的 metadata、query payload root、document row、row list，以及 session create/detail/list/messages/export、task/session usage、task create/detail/list/cancel/trace/delta/export/stream-reconnect、auth register/refresh/session list/user list、audit log list 这批 outward summary route，以及 `chat_persistence_service` 的 task trace/usage/response/export/delta 与 `task_rows_*` 批量聚合 helper，也不再因 typed service payload / `model_dump()` payload 而退化成空结构或直接报错，nested metadata 也能继续保留。
  - runtime helper、governance/export、registry diagnostics 与 planner payload 归一化已收口对旁路结构化载荷的兼容；当前 provider planner 与真实 remote provider 已共享一套 response text / usage 提取语义，支持 response envelope、content-part 文本响应、raw `choices/output` 载荷、`output_text` / `content.text`、`dict/list/tuple` 与 typed SDK-style object，以及 `input_tokens/output_tokens` usage alias、脏 usage 值容错与流式 delta 文本字段变体。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`862/862`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`46/46`）
  - `git diff --check` 通过

## 当前主线

1. 默认工具去 mock 化：优先补“已经能被规划，但执行本体、结果预览、trace/observation/export 仍残留默认 stub 语义”的缺口。
2. 真实工具接入：优先推进 extra/real tools 的执行本体产品化，而不是只停留在 planner payload 兼容。
3. registry / profile / provider source 治理：保持 loader、provider、source、diagnostics、selected source 与 settings summary 一套语义。
4. 契约稳定：外部 SSE / trace / export / e2e 契约尽量不乱改，优先做内部 helper、runtime 与 display 语义收口。

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
