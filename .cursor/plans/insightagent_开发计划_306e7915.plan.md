---
name: InsightAgent 开发计划
overview: real-tool-execution、queue-and-concurrency-lite、concurrency-fairness-policy、registry-governance、rag-governance-hardening、production-reliability-hardening、observability-experience 与 rag-product-experience 均已封板；当前主线为 provider-tool-expansion。
current_focus:
  - 当前主线：provider-tool-expansion 已启动，进度约 79%；HTTP JSON provider search 输出归一化已支持分页型 data/records 当前页结果配合 meta.page.total / pagination.total / paging.total 等显式总量元数据、GraphQL connection data.search.pageInfo.totalCount + edges[]、Meilisearch/Algolia estimatedTotalHits / nbHits、Brave web.results 嵌套结果容器、Bing webPages.totalEstimatedMatches + value[] 服务端总量、SearXNG/元搜索风格 number_of_results + results[] 总量、Crossref/学术检索风格 message.total-results + items[] 总量与当前页命中、引用型 answer-search citations / search_results 命中列表，也支持 totalResults: "1,234" 这类安全千分位总量字符串；显式 result_fields 支持 $['@odata.count'] / $["@odata.count"] 这类 bracket quoted 特殊字段键；documents_total 优先表示服务端总量，hit_count 保持当前页命中数；provider planner 已支持 Gemini/Vertex 风格 candidates[].content.parts[].functionCall{name,args} 与 Bedrock/Claude Converse 风格 content[].toolUse{name,input}，args/input 可为对象或 JSON 字符串；旧 trace/export/display 输出 shape 保持稳定。
  - 最新封板主线：rag-product-experience 已 100% 封板；知识库治理表版本明细、source/document 文档组摘要、文档组删除闭环、Runtime Debug RAG query 查询级召回摘要、质量分布、召回使用建议、质量/来源/未知来源筛选、组合筛选空结果提示、命中来源摘要与召回质量标签均已收口，RAG status/list、ingest/query、SSE、trace、export 外部契约保持稳定。
  - 最新封板主线：observability-experience 已 100% 封板；任务失败线索摘要与来源分类、Task Center audit failure hint 批量回放、观测筛选、失败来源诊断分组、本地下钻、registry profile/provider source 本地任务快照过滤、任务详情 failure 轨迹快捷定位、本地 failure 回放节点、跨视图 trace_semantic=failure 直达、稳定失败码可读映射、Usage Dashboard top tasks 失败摘要、Audit Logs 服务端 keyword 过滤与失败详情、Trace Failure 语义统计/过滤一致性均已收口，外部 SSE / trace / export shape 不变。
  - 最新封板主线：production-reliability-hardening 已 100% 封板，最新 GitHub checks 2/2 通过；waiting cleanup、execution owner/heartbeat、guarded running/terminal writes、duplicate active 防双执行、stale heartbeat 可选接管、terminal race 防误复活、reconnect SSE 终态回放、失败自愈、客户端断流保留 running / 服务端协程取消落 failed 均已收口。
  - 最近封板主线：rag-governance-hardening 已 100% 封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口均已完成治理收口。
  - 最近封板主线：registry-governance；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口。
  - 已封板主线：real-tool-execution、queue-and-concurrency-lite、concurrency-fairness-policy、registry-governance、rag-governance-hardening、production-reliability-hardening、observability-experience、rag-product-experience。
  - provider-tool-expansion 当前验证：paginated 红测、formatted_total 红测、bracket_quoted 红测、graphql_connection_total 红测、estimated_total_hits_alias 红测、nested_web_results 红测、bing_total_estimated_matches 红测、citations_as_hits 红测、number_of_results_total 红测、hyphenated_total_results 红测、Bedrock toolUse 与 toolUse string input 红测、provider_search 主题 slice、HTTP JSON 主题 slice、Gemini planner 红测、tool plan provider 主题 slice、backend full slice、frontend node/lint/build、diff hygiene 与备份计划 diff 检查均通过。
  - 后续候选主线：ci-release-engineering。
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
  - 每个主线确认封板后整理四份活跃文档，只保留当前状态、验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要
  - 测试/e2e/启动/提交先按 docs/development-runbook.md 使用固定依赖与提权边界，避免重复用失败探测环境
  - 控制单文件规模，新增测试/实现优先落到主题文件；主题文件明显膨胀时先拆新文件/新模块，沿用 test_tool_runtime_slice 与 tool_runtime facade 拆分经验
validation_baseline:
  backend_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1964/1964)
  backend_provider_tool_paginated_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k paginated (1/1)
  backend_provider_tool_formatted_total_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k formatted_total (1/1)
  backend_provider_tool_bracket_quoted_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bracket_quoted (1/1)
  backend_provider_tool_graphql_connection_total_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k graphql_connection_total (1/1)
  backend_provider_tool_estimated_total_hits_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k estimated_total_hits_alias (1/1)
  backend_provider_tool_nested_web_results_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k nested_web_results (1/1)
  backend_provider_tool_bing_total_estimated_matches_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bing_total_estimated_matches (1/1)
  backend_provider_tool_citations_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k citations_as_hits (1/1)
  backend_provider_tool_number_of_results_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k number_of_results_total (1/1)
  backend_provider_tool_hyphenated_total_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k hyphenated_total_results (1/1)
  backend_provider_tool_search_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k provider_search (9/9)
  backend_http_json_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k http_json (527/527)
  backend_provider_tool_use_string_input_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_use_string_input (1/1)
  backend_provider_tool_bedrock_tool_use_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bedrock_tool_use_content (1/1)
  backend_provider_tool_gemini_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k gemini (2/2)
  backend_tool_plan_provider_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_plan_provider (45/45)
  backend_production_reliability_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability (35/35)
  backend_queue_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue (66/66)
  backend_task_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task (361/361)
  backend_settings_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings (216/216)
  backend_rag_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag (79/79)
  backend_rag_route_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route (2/2)
  backend_result_summary_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary (30/30)
  frontend_node_tests: cd frontend && node --test --experimental-strip-types app/components/workbench/runtime-debug-modal-utils.node.test.ts app/components/workbench/knowledge-base-governance-modal-utils.node.test.ts app/components/workbench/utils.node.test.ts app/components/workbench/audit-logs-modal-utils.node.test.ts app/tasks/task-detail-page-utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts (121/121)
  frontend_lint: cd frontend && npm run lint
  frontend_build: cd frontend && npm run build
  frontend_type_contract: npx tsc --noEmit --strict --module esnext --moduleResolution bundler --target ES2020 --skipLibCheck app/components/workbench/task-queue-diagnostics-contract.type.test.ts
  frontend_targeted_ts: targeted tsc for runtime debug modal/rag results/utils, knowledge base governance modal/utils, i18n, workbench main path e2e, and usage dashboard e2e
  frontend_task_center_governance_chromium: e2e/usage-dashboard.spec.ts:372 (1/1, Task Center registry profile/source request + list visibility filtering)
  frontend_task_detail_replay_chromium: e2e/usage-dashboard.spec.ts:1329 (3/3, task detail semantic stats + semantic card drilldown + semantic filter count consistency)
  frontend_remote_error_observability_chromium: e2e/workbench-remote-errors.spec.ts:479 (1/1, Task Center audit failure hint replay + failure source diagnostic groups + diagnostic source chip local drilldown + Failure URL preset replay + readable failure text + needs attention / failed status filters + Audit Logs server keyword request + task detail audit failure hint recovery + failure trace shortcut)
  frontend_usage_audit_to_detail_chromium: e2e/usage-dashboard.spec.ts:774 (1/1)
  backend_e2e_main: baseline / main / export consistency / cancel-timeout passed against local backend
  backend_e2e_queue: TASK_QUEUE_MAX_CONCURRENT=1 backend queue phase passed (queued cancel + safe wait_position + settings diagnostics + followup completion + typed queue governance checks)
  frontend_queue_phase: low-concurrency backend/frontend scripts/ci_run_frontend_e2e.sh --phase queue passed (1 passed); default full skips this low-concurrency-only test
  frontend_running_cancel_chromium: default backend/frontend targeted Chromium passed (running task cancel reaches server terminal state and clears live UI)
  frontend_multitask_task_center_chromium: default backend/frontend targeted Chromium passed (task center separates active session tasks from global concurrent tasks)
  frontend_reload_isolation_chromium: default backend/frontend targeted Chromium passed (reload keeps background session stream detached until that session is active)
  frontend_reload_recovery_chromium: default backend/frontend targeted Chromium passed (running task can recover after reload and be cancelled)
  frontend_chromium_e2e: full Chromium passed, 51 passed / 1 skipped against real backend/frontend services, including knowledge governance version details
  frontend_knowledge_governance_chromium: e2e/usage-dashboard.spec.ts:1543 (1/1, knowledge governance version details + source/document groups + document delete)
  frontend_rag_main_path_chromium: e2e/workbench-main-path.spec.ts:352 and e2e/workbench-main-path.spec.ts:443 (2/2, RAG query insight summary + quality mix + recall guidance + recall quality filter + recall source filter + unattributed source filter + combined filter empty state + recall source attribution + recall quality label + distance explanation)
  frontend_diagnostics_finalize: scripts/ci_finalize_e2e_for_workflow.sh --scope frontend --summary-file /tmp/frontend-e2e-finalize-summary.md --event-name push --ref refs/heads/main passed with strict_level=any and 0 error-context alerts
  ci_e2e_tooling: bash scripts/test_ci_e2e_tooling.sh all
  diff_check: git diff --check
latest_validation_note: provider-tool-expansion 当前进度约 79%；本轮完成 Crossref/学术检索风格 message.total-results + items[] 总量与命中归一化；验证包括 hyphenated_total_results 1/1、provider_search 9/9、HTTP JSON 527/527、backend full slice 1964/1964、frontend node 121/121、frontend lint/build、py_compile、git diff --check 与备份计划 diff 检查通过；外部 SSE、trace、export、display shape 保持稳定。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档只保留当前状态、验证基线、后续候选主线、稳定契约和少量高信号摘要；主线封板后必须整理文档的规则已同步到 AGENTS.md 与 docs/development-runbook.md。
  - id: test-runtime-slice-split
    status: completed
    content: backend/scripts/test_tool_runtime_slice.py 已缩为兼容入口，测试主体拆到 backend/scripts/tool_runtime_slice/ 主题 mixin；二次细分后入口 363 行、最大主题模块约 4.7k 行，原入口命令保持不变。
  - id: tool-runtime-facade-split
    status: completed
    content: app/services/tool_runtime.py planner、execution、HTTP JSON、registry facade 拆分已完成，planner/provider planner 抽到 app/services/tool_runtime_planning.py，runtime context/result/attempt/trace/rag/plan-item execution 抽到 app/services/tool_runtime_execution.py，HTTP JSON/diagnostics 抽到 app/services/tool_runtime_http_json.py，registry/file-backed/provider-source 治理抽到 app/services/tool_runtime_registry.py；下一轮不再继续拆分。
  - id: queue-and-concurrency-lite
    status: completed
    content: 已封板；queued 状态、进程内执行槽位、安全 queue snapshot、queued cancel、恢复/隔离与低并发/full e2e 基线均已收口。
  - id: concurrency-fairness-policy
    status: completed
    content: 已 100% 封板；per-user/per-session 限额默认关闭，capacity-aware FIFO、settings diagnostics、前后端 typed 契约、backend queue e2e 与 full Chromium 基线均已收口，外部 SSE / trace / export shape 保持稳定。
  - id: development-runbook
    status: completed
    content: 新增 docs/development-runbook.md 并同步 AGENTS/README/backend/frontend/实时计划，固化 backend venv、frontend npm、本机端口/e2e 提权与 .git/index.lock 提交流程。
  - id: single-file-size-governance
    status: completed
    content: 新增单文件规模治理规则；后续不把历史大文件作为默认追加点，测试/实现优先进入主题文件，必要时先拆新主题文件或新模块。
  - id: registry-governance
    status: completed
    content: 已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口；通过 backend/full frontend/e2e fresh 复验。
  - id: rag-governance-hardening
    status: completed
    content: 已 100% 封板；RAG 来源/metadata、版本摘要、知识库标识、reserved alias、shared/private 边界、route/runtime trace/export/display、错误出口、前端治理表和 trace 搜索均已完成治理收口并通过完整复验。
  - id: next-mainline-candidates
    status: completed
    content: rag-product-experience 已封板；已选择 provider-tool-expansion 作为当前主线，ci-release-engineering 保留为后续候选。
  - id: production-reliability-hardening
    status: completed
    content: 已 100% 封板；waiting cleanup、execution owner/heartbeat、guarded running/terminal writes、duplicate active 防双执行、stale heartbeat 可选接管、terminal race 防误复活、reconnect SSE 终态回放、失败自愈、客户端断流保留 running 与服务端协程取消落 failed 均已收口；backend/frontend/e2e/CI finalize/GitHub checks/diff 封板验证通过。
  - id: observability-experience
    status: completed
    content: 已 100% 封板；任务失败线索摘要与来源分类、resolveTaskSnapshotSummary failureHint/failureSource、TaskResponse 与 task_failed audit event 兜底恢复、Task Center 列表 audit failure hint 批量回放、稳定错误码可读映射、观测筛选、失败来源诊断分组与本地下钻、registry profile/provider source 本地过滤、任务详情 Failure 轨迹快捷定位、本地 failure 回放节点、跨视图 trace_semantic=failure 直达、Usage Dashboard top tasks 失败摘要、Audit Logs 失败详情与服务端 keyword、Trace Failure 语义统计/过滤一致性均已收口；外部 SSE / trace / export shape 不变。
  - id: rag-product-experience
    status: completed
    content: 已 100% 封板；知识库治理表版本明细、source/document 文档组摘要、文档组删除治理、Runtime Debug RAG query 查询级召回摘要、质量分布、召回使用建议、质量/来源/未知来源筛选、组合筛选空结果提示、命中来源摘要与召回质量标签均已收口；RAG status/list、ingest/query、SSE、trace、export 外部契约保持稳定。
  - id: provider-tool-expansion
    status: in_progress
    content: 当前进度约 79%；已完成分页型 provider search 显式总量归一化、GraphQL connection 服务端总量归一化、Meilisearch/Algolia 服务端总量别名归一化、Brave web.results 嵌套搜索结果归一化、Bing webPages.totalEstimatedMatches + value[] 服务端总量归一化、SearXNG/元搜索风格 number_of_results + results[] 总量归一化、Crossref/学术检索风格 message.total-results + items[] 总量与命中归一化、引用型 answer-search citations / search_results 命中列表归一化、搜索 provider 千分位总量字符串归一化、显式 result_fields bracket quoted 特殊字段键解析，以及 Gemini/Vertex functionCall、Bedrock/Claude Converse toolUse planner 协议解析，并兼容 toolUse.input JSON 字符串参数；下一步继续按小红测补真实 provider/tool 协议输出差异。
logging_rule: 本计划文件只保存当前作战地图和少量高信号里程碑，不再保存按天流水账。
---

# InsightAgent 实时计划

## 当前仓库状态

- W1-W4 与阶段 5 基础产品化已完成并收口：SSE、Trace、Memory、RAG、Token/Cost、Auth、PostgreSQL、任务详情与导出、usage dashboard、审计、running task 恢复、任务取消/超时与基础工作台闭环已具备。
- `tool-runtime-productionization` 已归档；当前活跃判断以代码、三份 README 与本计划文件为准。
- `real-tool-execution` 当前验收基线已完成：provider/source/settings/file-backed 组合中的 real search / real calc 已稳定贯通真实上游协议、preview/output/result-summary、trace/observation/export 与 e2e 回归。
- `queue-and-concurrency-lite`、`concurrency-fairness-policy`、`registry-governance`、`rag-governance-hardening`、`production-reliability-hardening`、`observability-experience` 与 `rag-product-experience` 已封板：queued 状态、进程内执行槽位、capacity-aware FIFO、可选 per-user/per-session 限额、settings diagnostics、前端可观测入口、registry/provider source 治理、RAG 来源/版本/shared 边界治理、生产可靠性治理、失败诊断/任务回放/Trace 语义过滤、RAG 产品化检索解释与 e2e 基线均已收口。
- 当前主线为 `provider-tool-expansion`，进度约 79%；后续候选为 `ci-release-engineering`。
- 当前本机运行/提交路径已记录到 `docs/development-runbook.md`：slice/lint 多数普通运行，本机端口/Docker/e2e/服务启动/git index 写入按流程先普通尝试，失败后按 runbook 提权。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时自动走 `remote`，否则回退 canonical `mock`。
- planner / provider planner：支持 real/extra tools、动态 registry/source 候选、Chat Completions / Responses 风格工具调用输出、typed SDK-style payload 与 usage alias。
- `http_json` 真实执行器：支持请求模板、鉴权/header/query/body、timeout/method 模板、response_path、result_fields、raw/scalar fallback、typed/streaming response adapter、错误诊断与脱敏。
- 真实 search/calc 输出与 planner 协议：覆盖常见 REST/JS 字段别名、GraphQL connection pageInfo.totalCount + edges、Elastic/OpenSearch hits、Azure/OData、Meilisearch/Algolia estimatedTotalHits / nbHits、Brave web.results、Bing webPages.totalEstimatedMatches、SearXNG/元搜索 number_of_results、Crossref/学术检索 total-results/message.items、引用型 citations/search_results、organic search、分页型 data/records + meta.page/pagination/paging total、安全千分位总量字符串、显式 result_fields bracket quoted 特殊字段键、Qdrant/Milvus/LlamaIndex/Chroma/Weaviate 风格输出，provider planner 覆盖 OpenAI Chat/Responses、Gemini/Vertex functionCall 与 Bedrock/Claude Converse toolUse 形态，统一补齐 documents_total/hit_count/chunks/result/request_id。
- registry/source 治理：覆盖 extra_tools、overrides、profile、selected source、file manifest、named provider/loader、provider/loader factory、factory alias、profile reset、forward reference 与 diagnostics 并回。
- trace/export/display：result-summary、safe output、observation、rag follow-up、task/session JSON/Markdown export、settings diagnostics、audit/SSE error 与前端 workbench 回放已进入同一语义主干。

## 当前验证基线

- Backend slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`，当前 `1964/1964`。
- Backend provider-tool paginated slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k paginated`，当前 `1/1`。
- Backend provider-tool formatted total slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k formatted_total`，当前 `1/1`。
- Backend provider-tool bracket quoted slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bracket_quoted`，当前 `1/1`。
- Backend provider-tool GraphQL connection total slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k graphql_connection_total`，当前 `1/1`。
- Backend provider-tool estimated total hits slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k estimated_total_hits_alias`，当前 `1/1`。
- Backend provider-tool nested web results slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k nested_web_results`，当前 `1/1`。
- Backend provider-tool Bing total estimated matches slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bing_total_estimated_matches`，当前 `1/1`。
- Backend provider-tool citations slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k citations_as_hits`，当前 `1/1`。
- Backend provider-tool number of results slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k number_of_results_total`，当前 `1/1`。
- Backend provider-tool hyphenated total slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k hyphenated_total_results`，当前 `1/1`。
- Backend provider-tool search slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k provider_search`，当前 `9/9`。
- Backend HTTP JSON slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k http_json`，当前 `527/527`。
- Backend provider-tool string input slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_use_string_input`，当前 `1/1`。
- Backend provider-tool Bedrock toolUse slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k bedrock_tool_use_content`，当前 `1/1`。
- Backend provider-tool Gemini slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k gemini`，当前 `2/2`。
- Backend tool plan provider slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k tool_plan_provider`，当前 `45/45`。
- Backend production reliability slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k production_reliability`，当前 `35/35`。
- Backend queue slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k queue`，当前 `66/66`。
- Backend task slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k task`，当前 `361/361`。
- Backend settings slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k settings`，当前 `216/216`。
- Backend RAG slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag`，当前 `79/79`。
- Backend RAG route slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_route`，当前 `2/2`。
- Backend result summary slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k result_summary`，当前 `30/30`。
- Backend usage dashboard slice：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k usage_dashboard`，当前 `40/40`。
- Backend e2e main phase：baseline / main / export consistency / cancel-timeout 已通过。
- Backend e2e queue phase：`TASK_QUEUE_MAX_CONCURRENT=1` backend 上 queued cancel、queued SSE safe wait_position、settings diagnostics、typed queue governance checks 与 followup completion 通过。
- Frontend node tests：runtime debug modal utils / knowledge base governance modal utils / workbench utils / audit logs modal utils / task detail utils / stream store utils / model settings utils，当前 `121/121`。
- Frontend lint：`cd frontend && npm run lint` 通过。
- Frontend build：`cd frontend && npm run build` 通过。
- Frontend type contract：TaskQueueDiagnostics 基础运行态计数、governance 字段必填与 pressure_state/waiting_policy 枚举契约通过。
- Frontend targeted TS：本轮涉及的 runtime debug modal/rag results/utils、knowledge base governance modal/utils、i18n、workbench main path e2e 与 usage dashboard e2e 通过 targeted `tsc`。
- Frontend task center governance Chromium：`e2e/usage-dashboard.spec.ts:372`，`1/1` 通过，覆盖 Task Center registry profile/source 请求与列表可见性过滤。
- Frontend queue phase：低并发 backend/frontend 下 selected session 恢复 queued 任务、Inspector 排队位置与 queued cancel 通过；默认 full Chromium 下该专项显式 skip。
- Frontend running cancel Chromium：默认 backend/frontend 下 UI cancel 后服务端 terminal、Inspector phase 与 composer 恢复通过。
- Frontend multi-task Chromium：默认 backend/frontend 下 Task Center 当前会话与全局多任务隔离通过。
- Frontend reload isolation Chromium：默认 backend/frontend 下刷新后后台会话 stream 不误恢复、切回原会话恢复并可取消通过。
- Frontend reload recovery Chromium：默认 backend/frontend 下 running task reload 后恢复并可取消通过。
- Frontend Chromium e2e：最终本地 backend/frontend 服务下 full 基线 `51 passed / 1 skipped`；覆盖新增知识库版本明细展开，低并发 queued 专项在 full 阶段按预期 skip，已由 frontend queue phase 单独覆盖。
- Frontend knowledge governance Chromium：`e2e/usage-dashboard.spec.ts:1543`，`1/1` 通过，覆盖真实 RAG ingest 后展开版本明细、source/document 文档组摘要、文档组删除与状态归零。
- Frontend RAG Chromium：`e2e/workbench-main-path.spec.ts:352` 与 `e2e/workbench-main-path.spec.ts:443`，`2/2` 通过，覆盖真实 RAG ingest/query 后的查询级召回摘要、质量分布、召回使用建议、召回质量筛选、召回来源筛选、未知来源筛选、组合筛选空结果提示、命中来源摘要、召回质量标签与 distance 解释。
- Frontend task detail replay Chromium：`e2e/usage-dashboard.spec.ts:1329`，`3/3` 通过，覆盖 Task Center/任务详情语义统计、统计卡下钻与语义过滤计数一致性。
- Frontend remote error observability Chromium：`e2e/workbench-remote-errors.spec.ts:479`，`1/1` 通过，覆盖 Task Center audit failure hint 回放、失败来源诊断分组、诊断来源 chip 本地下钻、Failure URL 预设直达与可读失败说明、Needs attention / Failed status 观测筛选、Audit Logs 服务端 keyword 请求、任务详情 audit failure hint 恢复与失败轨迹快捷定位。
- Frontend usage/audit-to-detail Chromium：`e2e/usage-dashboard.spec.ts:774`，`1/1` 通过。
- Frontend diagnostics finalize：`scripts/ci_finalize_e2e_for_workflow.sh --scope frontend --summary-file /tmp/frontend-e2e-finalize-summary.md --event-name push --ref refs/heads/main` 在 main push strict `any` 下 error-context counters 为 0，通过。
- GitHub checks：`7550120 fix: 保留客户端断流运行任务` 已 `2/2` 通过。
- CI tooling：`bash scripts/test_ci_e2e_tooling.sh all` 通过。
- Diff hygiene：`git diff --check` 通过。

## 最近封板主线

- `registry-governance`：已封板；provider/source 脱敏、冲突 alias、settings/preflight/runtime/trace/export/audit/SSE 共享 alias map、模型输出层安全摘要与 settings runtime_artifacts diagnostics alias 已收口，不改变 settings/preflight/trace/export/audit/SSE 可见字段 shape。
- `rag-governance-hardening`：已封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口已完成治理收口。
- `production-reliability-hardening`：已封板；任务队列清理、owner/heartbeat、guarded terminal writes、reconnect/断流语义、race 防误复活与最终 GitHub checks 2/2 均已收口。
- `observability-experience`：已封板；失败线索、来源分类、跨视图 Failure 回放、Task Center 观测筛选、Audit Logs 服务端 keyword、Trace Failure 语义统计与过滤一致性均已收口。

## Pre-flight Cleanup

- 文档瘦身：四份活跃文档只保留当前状态、当前验证基线、下一主线、稳定契约与少量高信号能力摘要。
- 测试拆分：`backend/scripts/test_tool_runtime_slice.py` 已缩为兼容入口，测试主体拆到 `backend/scripts/tool_runtime_slice/` mixin 包并保持原入口命令不变；`registry_provider_source_aliases.py` 承接 provider source 冲突 alias 可回写测试，避免继续膨胀既有 settings/task usage 长文件。
- 主题包摘要：provider/source、planner、settings/registry、http_json request/response/mapping/error、task trace/export/session/usage、registry governance/file diagnostics/runtime models、runtime result/attempt/observation/rag execution。
- `tool_runtime.py` 拆分放在测试拆分之后分阶段推进，优先抽旁路模块并保留现有 import facade；planner 已抽到 `backend/app/services/tool_runtime_planning.py`，runtime context/result/attempt/trace/rag/plan-item execution 已抽到 `backend/app/services/tool_runtime_execution.py`，HTTP JSON/diagnostics 已抽到 `backend/app/services/tool_runtime_http_json.py`，registry/file-backed/provider-source 治理已抽到 `backend/app/services/tool_runtime_registry.py`；pre-flight 拆分到此收口。

## 后续维护线

- `production-reliability-hardening`、`observability-experience` 与 `rag-product-experience` 已 100% 封板；当前按先红测、再实现、再 targeted/full slice 的方式推进 `provider-tool-expansion`。
- 后续候选：`ci-release-engineering`。
- 新 provider/source 协议：按 `real-tool-execution` 已完成验收基线增量补红测和局部归一化，不扩大外部契约；下一步继续寻找真实 provider/tool 输出差异的小缺口。

## 维护约定

- 本计划文件是实时快照，不是历史日志仓库。
- 重要历史事实保留为摘要；旧失败过程、重复验证清单和按轮流水账不继续堆积。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 每个主线确认封板后，必须整理四份活跃文档的当前状态、验证基线、下一步计划/候选主线与稳定契约，收缩旧过程描述。
