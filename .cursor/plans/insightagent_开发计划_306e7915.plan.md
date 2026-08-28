---
name: InsightAgent 开发计划
overview: provider-tool-expansion 已 100% 封板；九条主线均已完成，后续候选为 ci-release-engineering。
current_focus:
  - 当前状态：provider-tool-expansion 已 100% 封板；已封板主线扩展到 real-tool-execution、队列/并发治理、registry/RAG 治理、生产可靠性、可观测体验与 RAG 产品体验。
  - Provider 收口：provider search 总量/命中归一化、provider planner 多协议工具调用解析、JSON 字符串参数解析与 reconnect 稳定错误码复原均已完成。
  - 结构治理：本轮拆分 `tool_runtime_registry.py` 与 `tool_runtime_http_json.py` 两个超大文件，新增 registry wrapper 安装器与 HTTP JSON response/diagnostics 主题模块，原导出路径保持兼容。
  - 稳定契约：默认 remote/mock、SSE、trace、export、display 与 e2e shape 保持稳定。
  - 当前验证：backend full slice 1983/1983，tool_registry 494/494，http_json 531/531，facade 4/4，frontend node 121/121，lint/build 通过；e2e/diff hygiene 保持基线。
  - 后续候选：ci-release-engineering。
constraints:
  - 永远不要修改 data/insightagent.plan.back.md
  - 保持先补 failing test 再改实现
  - 不主动破坏外部 SSE / trace / export / e2e 契约
  - 每轮结束同步 README.md、backend/README.md、frontend/README.md、.cursor/plans
  - 每个主线确认封板后整理四份活跃文档，只保留当前状态、验证基线、下一步计划/候选主线、稳定契约与少量高信号摘要
  - 测试/e2e/启动/提交先按 docs/development-runbook.md 使用固定依赖与提权边界，避免重复用失败探测环境
  - 控制单文件规模，新增测试/实现优先落到主题文件；主题文件明显膨胀时先拆新文件/新模块，沿用 test_tool_runtime_slice 与 tool_runtime facade 拆分经验
validation_baseline:
  backend_full_slice: backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py (1983/1983)
  backend_provider_tool: tool_registry 494/494; http_json 531/531; facade 4/4; provider_search 15/15; tool_plan_provider 57/57; failed_task_error_event_hint 1/1
  frontend_quality: node tests 121/121; npm run lint; npm run build
  e2e: backend main passed; frontend full Chromium 52 passed / 1 skipped
  hygiene: py_compile; git diff --check; git diff --cached --check; backup plan diff clean; ports 8000/3001 clean
latest_validation_note: provider-tool-expansion 已 100% 封板；本轮完成 runtime 大文件拆分，backend/frontend 新鲜回归通过，四份活跃文档继续保持压缩摘要。
todos:
  - id: docs-slimming
    status: completed
    content: 四份活跃文档只保留当前状态、验证基线、后续候选主线、稳定契约和少量高信号摘要；主线封板后必须整理文档的规则已同步到 AGENTS.md 与 docs/development-runbook.md。
  - id: test-runtime-slice-split
    status: completed
    content: backend/scripts/test_tool_runtime_slice.py 已缩为兼容入口，测试主体拆到 backend/scripts/tool_runtime_slice/ 主题 mixin；二次细分后入口 363 行、最大主题模块约 4.7k 行，原入口命令保持不变。
  - id: tool-runtime-facade-split
    status: completed
    content: tool_runtime facade 拆分已完成；planner、execution、HTTP JSON、registry 分别进入独立模块，外部 import 保持稳定。
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
    content: 已拆分 `tool_runtime_registry.py` 与 `tool_runtime_http_json.py` 两个超大文件；后续不把历史大文件作为默认追加点，测试/实现优先进入主题文件，必要时先拆新主题文件或新模块。
  - id: registry-governance
    status: completed
    content: 已封板；provider/source 脱敏、冲突 alias 与跨 settings/runtime/trace/export/audit/SSE 的安全摘要已收口。
  - id: rag-governance-hardening
    status: completed
    content: 已 100% 封板；RAG 来源/metadata、版本摘要、知识库标识、reserved alias、shared/private 边界、route/runtime trace/export/display、错误出口、前端治理表和 trace 搜索均已完成治理收口并通过完整复验。
  - id: next-mainline-candidates
    status: completed
    content: rag-product-experience 已封板；已选择 provider-tool-expansion 作为当前主线，ci-release-engineering 保留为后续候选。
  - id: production-reliability-hardening
    status: completed
    content: 已 100% 封板；队列清理、owner/heartbeat、terminal race、reconnect/断流语义与失败自愈均已收口。
  - id: observability-experience
    status: completed
    content: 已 100% 封板；失败线索、来源分类、Task Center/任务详情/Usage Dashboard/Audit Logs 回放与 Trace Failure 过滤均已收口。
  - id: rag-product-experience
    status: completed
    content: 已 100% 封板；知识库版本/文档组治理与 Runtime Debug RAG 召回解释、筛选、质量标签均已收口。
  - id: provider-tool-expansion
    status: completed
    content: 已 100% 封板；provider search 总量/命中归一化、provider planner 多协议工具调用解析、JSON 字符串参数与 reconnect 稳定错误码复原均已收口。
logging_rule: 本计划文件只保存当前作战地图和少量高信号里程碑，不再保存按天流水账。
---

# InsightAgent 实时计划

## 当前仓库状态

- 阶段 5 基础产品化已完成，`tool-runtime-productionization` 已归档。
- 已封板主线：real-tool、队列/并发、registry/RAG 治理、生产可靠性、可观测体验、RAG 产品体验、provider-tool-expansion。
- 当前主线 `provider-tool-expansion` 已 100% 封板；后续候选为 `ci-release-engineering`。
- 稳定契约：默认 remote/mock、SSE、trace、export、display 与 e2e shape 保持稳定。
- 运行/提交路径以 `docs/development-runbook.md` 为准。

## 已完成能力摘要

- 默认运行策略：provider/model/api_key 完整时走 `remote`，否则回退 canonical `mock`。
- Provider 工具：search 总量/命中归一化、planner 多协议工具调用解析、JSON 字符串参数与 reconnect 错误码复原已封板。
- Runtime 结构：`tool_runtime.py` 保留 facade；planner、execution、HTTP JSON、registry 分模块维护；registry wrapper 安装器与 HTTP JSON response/diagnostics 已继续拆分。
- Trace/export/display：result-summary、safe output、observation、settings diagnostics 与前端回放共享同一语义主干。

## 当前验证基线

- Backend：full slice `1983/1983`；tool_registry `494/494`；http_json `531/531`；facade `4/4`；provider_search `15/15`；tool_plan_provider `57/57`。
- Frontend：node tests `121/121`；lint/build 通过。
- E2E：backend main phase 通过；frontend full Chromium `52 passed / 1 skipped`。
- Hygiene：`py_compile`、diff checks、备份计划 diff 检查与端口清理通过。

## 最近封板主线

- `provider-tool-expansion`：已 100% 封板；provider search、provider planner 与 reconnect 错误码复原均已收口，旧 SSE/trace/export/display shape 不变。
- `registry-governance`：已封板；provider/source 脱敏、冲突 alias 与安全摘要已收口，外部可见字段 shape 不变。
- `rag-governance-hardening`：已封板；RAG 来源/metadata、版本摘要、知识库标识、shared/private 边界、route/runtime trace/export/display 与错误出口已完成治理收口。
- `production-reliability-hardening`：已封板；任务队列清理、owner/heartbeat、guarded terminal writes、reconnect/断流语义、race 防误复活与最终 GitHub checks 2/2 均已收口。
- `observability-experience`：已封板；失败线索、来源分类、跨视图 Failure 回放、Task Center 观测筛选、Audit Logs 服务端 keyword、Trace Failure 语义统计与过滤一致性均已收口。

## Pre-flight Cleanup

- 文档瘦身：四份活跃文档只保留当前状态、当前验证基线、下一主线、稳定契约与少量高信号能力摘要。
- 测试拆分：`backend/scripts/test_tool_runtime_slice.py` 已缩为兼容入口，测试主体拆到 `backend/scripts/tool_runtime_slice/`。
- 主题包摘要：provider/source、planner、settings/registry、http_json request/response/mapping/error、task trace/export/session/usage、registry governance/file diagnostics/runtime models、runtime result/attempt/observation/rag execution。
- `tool_runtime.py` 保留 facade；planner、execution、HTTP JSON、registry 已拆到独立模块，pre-flight 拆分到此收口。

## 后续维护线

- `production-reliability-hardening`、`observability-experience`、`rag-product-experience` 与 `provider-tool-expansion` 已 100% 封板；后续增量继续按先红测、再实现、再 targeted/full slice 的方式推进。
- 后续候选：`ci-release-engineering`。
- 新 provider/source 协议：按 `real-tool-execution` 与 `provider-tool-expansion` 封板基线增量补红测和局部归一化，不扩大外部契约，不再作为当前封板阻塞项。

## 维护约定

- 本计划文件是实时快照，不是历史日志仓库。
- 重要历史事实保留为摘要；旧失败过程、重复验证清单和按轮流水账不继续堆积。
- 每轮完成后同步 `README.md`、`backend/README.md`、`frontend/README.md` 与本计划文件。
- 每个主线确认封板后，必须整理四份活跃文档的当前状态、验证基线、下一步计划/候选主线与稳定契约，收缩旧过程描述。
