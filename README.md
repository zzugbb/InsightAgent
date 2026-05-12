# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 → 任务执行 → 轨迹解释 → Memory/RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前开发进度（按完整计划对齐）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| W1 主链路 | 已完成 | 会话/任务/消息持久化、SSE 流、trace 回放与 delta、前端工作台闭环 |
| W2 可观测 + Memory 最小闭环 | 已完成（已收口） | 轨迹时间线+流程图、TraceStep 契约、Chroma 会话 memory 状态/写入/检索、`trace/delta` 流式阶段增量持久化（`seq` 递增） |
| W3 Tool + ReAct | 已完成（mock 范围） | mock 工具调用循环、可恢复重试/致命失败语义、SSE/Trace 对齐 |
| W4 RAG + 成本展示 | 已完成（已收口） | RAG ingest/query/status、执行链路 RAG 命中回填、Token/Cost 估算与 UI 展示、`compose.full.yml` |
| 阶段 5+ 产品化 | 进行中 | `full-data-auth` 首版已落地（JWT/多用户隔离/凭证加密/最小审计），运行时已收敛为 PostgreSQL，远端 OpenAI-compatible provider 已可配置，更完整治理待后续 |

当前默认策略：`mock` 模式仍作为低成本默认演示路径；`remote` 模式已支持 OpenAI-compatible `/chat/completions`，可按用户配置 `base_url + api_key + model` 接入真实厂商。

## 当前能力摘要

- backend：
  - 后端数据库已收敛为 PostgreSQL（`INSIGHT_AGENT_DATABASE_URL`）
  - 2026-04-14 修复：`POST /api/tasks` 在 PostgreSQL 下的会话标题自动命名 SQL 类型兼容问题（`CASE WHEN` 布尔参数），消除“发会话消息无响应”根因（后端 500）
  - 保留 `backend/scripts/migrate_sqlite_to_postgres.py` 用于历史 SQLite 数据一次性平迁（幂等 upsert）
  - `POST /api/tasks`、`GET /api/tasks/{task_id}/stream`、`GET /api/tasks/{task_id}/trace`、`GET /api/tasks/{task_id}/trace/delta`
  - RAG：`GET /api/rag/status`、`POST /api/rag/ingest`、`POST /api/rag/query`
  - RAG 治理最小版：`GET /api/rag/knowledge-bases`、`POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`、`DELETE /api/rag/knowledge-bases/{knowledge_base_id}`
  - `rag-rbac-lite` 增量（2026-05-09）：知识库支持 `shared-*` 前缀共享命名空间；`admin` 可写共享库（ingest/clear/delete），普通用户对共享库只读（status/query/list），个人库维持用户隔离可读写
  - `trace/delta` 支持 `limit` 参数控制单次增量返回量（默认 200，最大 500）
  - 流式阶段会按批次持久化最终 `observation`（默认每 8 个 token chunk 一次，并在结束时兜底），`trace/delta?after_seq=` 可持续拉取增量
  - 前端在 `trace/delta` 返回 `has_more=true` 时会快速连续拉取，优先清空积压增量
  - `GET /api/tasks` 支持 `limit/offset` 与可选 `session_id` 过滤，响应含 `total/has_more`
  - 任务相关响应补充状态派生字段：`status_normalized`、`status_label`、`status_rank`（向后兼容）
  - `GET /api/tasks/usage/summary` 支持全局与按 `session_id` 的 usage 聚合
  - `GET /api/tasks/usage/dashboard`：返回最近窗口趋势、会话榜、任务榜（支持按 `session_id` 聚合）
  - `GET /api/tasks/usage/dashboard` 支持 `source_kind` 筛选（`all/provider/estimated/mixed/legacy`）
  - `GET /api/tasks/usage/dashboard` 的 `trend` 已补来源趋势字段：`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`
  - usage 从占位升级为可计算：`prompt_tokens/completion_tokens/cost_estimate`（并支持单价配置）
  - `provider-usage-alignment` 首版已落地：执行链路优先写入 provider 官方 usage（`prompt_tokens/completion_tokens`），缺失字段自动回退估算，并在 `done.usage` 标注 `prompt_tokens_source/completion_tokens_source/usage_source`
  - `e2e-main-path` 已补 usage 来源断言：校验 `done.usage` 的 token 数值与来源字段（`prompt_tokens_source/completion_tokens_source/usage_source`）
  - usage 汇总接口已补来源维度统计：`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`
  - 会话接口支持创建/列表/详情/消息/重命名/删除
  - 设置接口支持读取/保存/校验：`GET /api/settings`、`PUT /api/settings`、`POST /api/settings/validate`
  - `remote` 模式已接入 OpenAI-compatible Provider：基于 `base_url + api_key + model` 调用 `/chat/completions`（支持多家兼容厂商按配置接入）
  - `remote` 模式严格校验：缺少 `api_key` 或 `base_url` 时任务流返回明确错误码（不再静默回落 `mock`）
  - `remote-provider-hardening` 已完成首轮收口：Provider 运行时错误统一为结构化错误码（401/403、429、5xx、网络错误、无效 JSON、空响应、SSE 中断），并通过 SSE `error` 事件稳定透传 `code/fatal/retryable/detail/status_code`
  - `task-cancel-timeout` 首版已落地：新增 `POST /api/tasks/{task_id}/cancel`，任务执行链路支持用户取消与超时中断（`TASK_TIMEOUT_SEC`），并发出 `cancelled/timeout` SSE 事件
  - `task-cancel-timeout` e2e 覆盖已补齐：新增 `backend/scripts/e2e_task_cancel_timeout.py`（取消链路默认可跑，超时链路建议低 `TASK_TIMEOUT_SEC` 环境）
  - 后端 e2e CI 已扩展：GitHub Actions 工作流 [backend-e2e.yml] 现覆盖 `baseline/main-path/export-consistency/cancel/timeout`；工作流已升级 `actions/checkout@v6`、`actions/setup-python@v6` 以适配 GitHub Actions Node 24 运行时（消除 Node 20 action 弃用提示）；Python 运行时统一为 **3.14**（与 `compose.full.yml`、根目录 `.python-version` 一致）；前端 **Node.js 24.x** 已对齐（`compose.full.yml` 前端镜像、`frontend/package.json` engines、根目录 `.nvmrc`）；并新增后端 e2e 失败快照归档（e2e 日志 + health + 诊断 + backend 日志 artifact 上传）
  - e2e-main-path 增量（2026-05-09）：后端主链路脚本新增 `shared-*` 知识库权限断言（普通用户写共享库 `403`、共享库读能力稳定；若当前账号具备 admin 权限则追加 admin 写共享库成功断言）
  - 后端 e2e 可观测性增强：`backend-e2e` 现会在 CI Summary 输出 `export-consistency` 关键检查点快照（含步骤与 OK 项），并额外输出断言计数统计（steps/ok/pass/task-export/session-export/shared-rag/cross-user/not-found）与归档 `/tmp/e2e-export-consistency-summary.txt`；失败诊断新增导出一致性日志尾部片段，便于快速定位权限或导出结构回归
  - 后端 e2e 规则对齐（2026-05-09）：`backend-e2e` 的 export consistency 摘要阈值已对齐脚本 7 步输出（`steps/ok` 期望由 6 调整为 7），并新增 `shared_rag_semantics_ok` 计数，避免共享知识库权限回归被摘要漏报
  - 后端 e2e 规则增强（2026-05-09 补充）：`backend-e2e` 的 export consistency 步数阈值改为自动从日志首条 `[x/N]` 解析 `N`，不再硬编码固定步数，降低后续脚本步骤变更带来的 CI 维护成本
  - 后端 e2e 维护性补充（2026-05-09）：`backend-e2e` export consistency 摘要新增 `add_warning` 统一告警函数，收敛 `P0/P1` 计数与消息拼装逻辑，减少阈值规则扩展时的重复改动
  - 后端 e2e 告警增强（2026-05-08）：`backend-e2e` 的 export summary 新增阈值告警行（`Threshold alerts`），当计数偏离预期时会直接列出异常项（expected vs actual），便于在 PR Summary 快速分流回归类型
  - CI 告警分级（2026-05-08）：`backend-e2e` 与 `frontend-e2e` 的导出告警已统一增加严重级别标签（`[P0]/[P1]`）与级别计数（`severity: P0=..., P1=...`），便于快速判断处理优先级
  - CI 告警模板统一（2026-05-08）：`backend-e2e` 与 `frontend-e2e` 导出摘要已统一为同字段顺序（`total_alerts` → `severity` → 分级明细）与同类作用域标签格式（如 `[P1][backend-export-consistency]` / `[P1][workbench-main-path]`），提升跨工作流对比效率
  - CI 规则收口（2026-05-08）：`backend-e2e` 与 `frontend-e2e` 的导出诊断规则已提炼为 workflow 内变量块（关键计数 regex / key-lines regex），并统一 `total_alerts=0` 时输出 `severity: P0=0, P1=0`，降低后续规则扩展时的维护分叉
  - CI 告警分级补强（2026-05-08）：`frontend-e2e` 新增 `P0` 诊断失真判定（存在 `error-context` 但 `export_api_path_hints=0`，或 UI/响应头双计数同时为 0；edge-cases 另含 `export_404_semantic_hints=0`），用于快速识别“诊断信息缺失/异常分类失真”风险
  - 导出链路回归补齐：新增 `backend/scripts/e2e_export_consistency.py`，校验任务/会话导出 JSON 与 Markdown 字段一致性、`download=true` 附件头、跨用户导出隔离 404 与不存在资源 404 语义
  - 导出链路回归加固：`e2e_export_consistency` 新增导出 `Content-Type` 断言（JSON=`application/json`、Markdown=`text/markdown`，含 download 场景），防止 MIME 类型回归漏检
  - 导出链路回归补充（2026-05-09）：`e2e_export_consistency` 新增 `shared-*` 跨角色语义断言（普通用户写共享库 `403`；当当前账号为 admin 时补充“admin 写入后普通用户可读”断言），确保共享库权限演进不破坏导出主链路
  - 前端可视化回归 CI 首版已接入：新增 Playwright 用例（用量统计弹窗主路径 + 来源趋势区可见性）与 `.github/workflows/frontend-e2e.yml`（拉起 postgres/chroma/backend 后执行前端 e2e）
  - CI Node 24 对齐补充：`frontend-e2e` 工作流已将 `actions/setup-node` 升级到 `v5`、`actions/upload-artifact` 升级到 `v7`，并显式启用 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`，消除 Node 20 action 弃用告警
  - CI 修复补充：修正 `.github/workflows/frontend-e2e.yml` 的 YAML 缩进错误（`push` 触发器误嵌套到 `env`），恢复工作流可解析性
  - 前端回归稳定性修复：Playwright 登录态注入改为显式透传 storage key（避免浏览器上下文常量不可见导致的未登录误失败）
  - 前端回归稳定性修复（第二次）：`usage-dashboard` 用例新增 UI 登录兜底（若未命中 Workbench 则自动登录），避免 CI 冷启动/状态差异下找不到设置入口
  - 前端回归覆盖扩展（一次性补齐）：Playwright 新增“设置菜单治理入口”场景（审计日志/知识库治理弹窗可见性），并为设置菜单项补充稳定 `data-testid`（`settings-menu-audit/settings-menu-knowledge-base/settings-menu-model`）
  - 前端回归补齐（2026-05-09）：Playwright 新增“非 admin 用户在知识库治理中对 `shared-*` 行的清空/删除按钮禁用”断言，确保 UI 权限提示与后端 `403` 语义一致
  - 前端回归补齐（2026-05-09 补充）：上述 `shared-*` 权限断言已补入 `workbench-main-path` 主链路用例，确保主路径回归也覆盖“非 admin 共享库按钮禁用、私有库按钮可用”语义
  - 前端回归覆盖扩展（二次补齐）：Playwright 新增 `workbench-main-path` 场景，覆盖对话发送、Trace 可见、RAG ingest/query、任务/会话 JSON+Markdown 导出、运行中任务刷新恢复与取消后再次发送；并为 Composer/Inspector 导出与 RAG 控件补充稳定 `data-testid`
  - 前端回归覆盖扩展（三次补齐）：新增 `workbench-edge-cases` 场景，覆盖 RAG 空命中可见性与导出接口缺失资源 `404` 语义断言
  - 前端回归工程化补充：e2e 登录/鉴权预置与 Workbench 就绪逻辑已抽取到 `frontend/e2e/helpers/workbench.ts`，降低重复维护
  - 前端回归矩阵扩展：Playwright 已增加 `firefox/webkit` 项目；`frontend-e2e` 工作流改为“smoke 三浏览器 + chromium 全量”，并新增 remote 网络错误映射回归；当前本地回归已验证 chromium 全量 `25/25` 与 smoke 矩阵 `15/15`
  - 前端回归深化：usage/知识库治理/回底按钮已补稳定 `data-testid`，并新增细粒度断言（来源筛选请求参数、表头左对齐、治理动作无边框文本按钮、上滑阅读时回底按钮显隐交互）
  - 前端异常态覆盖深化：Playwright `workbench-remote-errors` 新增 `503` 映射与“remote 取消后发送冷却恢复”用例（含请求次数断言、冷却期阻断重发、冷却后恢复发送），避免“取消后立即重发触发上游限流”回归
  - 前端设置校验异常态覆盖：Playwright 新增模型设置弹窗 `settings/validate` 回归（`remote_api_key_unauthorized` 与 `remote_preflight_network_error`），并给模型设置关键控件补充稳定 `data-testid`，降低多语言与提示时序引发的误报
  - 前端流式异常态覆盖：Playwright 新增 `remote_provider_stream_invalid_json` 与 `remote_provider_stream_interrupted` 回归，并完成 Context tab helper 稳态修复（改为“重试点击直到 `#inspector-panel-context` 可见”）
  - 前端导出异常态覆盖补齐：`workbench-edge-cases` 新增“空会话导出”（JSON/Markdown）与“跨用户导出隔离（task/session 均返回 404）”回归，补全 `trace/session export` 的空数据与权限语义断言
  - 前端导出协议断言补齐：`workbench-edge-cases` 新增“download 响应 `Content-Type` 与附件扩展名一致性”回归，覆盖 task/session 的 JSON/Markdown 导出
  - 前端主链路导出校验增强：`workbench-main-path` 已升级为“UI 下载事件 + 同路径 API 响应头”双重断言，覆盖 task/session 的 JSON/Markdown 导出 `Content-Type` 与附件扩展名一致性
  - 前端导出错误提示一致性收口：Inspector 导出请求统一走 `ApiError` 映射（不再直接透出后端原始 detail），并新增 UI 回归“切换为其他用户 token 后触发导出 404，提示包含 404 且按钮可恢复”
  - 回归稳定性补丁：`mock` provider 新增仅测试触发的慢流标记（`[mock-slow]` / `[mock-slow-ms=30]`），用于稳定复现“刷新恢复 + 取消”路径，默认请求行为不变
  - 回归稳态补丁（恢复取消链路）：`workbench-main-path` 新增“先确认后端进入 running/pending 再刷新”的断言，并在等待取消按钮期间持续维持 Context 面板激活，规避自动恢复切回 Trace 的时序抖动
  - 回归覆盖一次性补齐（会话与取消交互）：`workbench-edge-cases` 新增 3 条回归（取消后同文案立即重发不丢消息、跨会话切换时流式状态严格会话隔离且切回可取消、mock 取消后不出现重试按钮且可快速恢复发送）；本地全量 e2e 最新为 chromium `25/25`
  - 回归覆盖六项一次性补齐：新增“恢复提示三态（恢复中/成功/失败）”“trace delta 重试 + 后台暂停/前台恢复”“auth refresh 自动续期 + logout-all 失效重登”“设置弹窗与治理子弹窗重开状态重置”回归；并补充稳定测试锚点（`chat-recovery-notice`、`inspector-trace-sync-*`、`audit-*`、`settings-section-trigger-*`）。
  - CI 稳定性增强：`frontend-e2e` 新增并发互斥（同分支取消旧运行）、失败后 `--last-failed` 诊断重跑、`error-context.md + trace.zip` 失败索引文件并随 artifact 上传（artifact 名含 `run_id/run_attempt`），便于快速定位失败快照。
  - CI 诊断增强（2026-05-08）：`frontend-e2e` 导出断言摘要已扩展覆盖 `workbench-main-path` + `workbench-edge-cases`（从 `error-context` 提取 UI 下载层/响应头层/API 路径/404 语义提示计数，并输出关键行），结果同步写入 `GITHUB_STEP_SUMMARY` 与 artifact（`/tmp/frontend-e2e-export-summary.md`）
  - CI 诊断增强（2026-05-09）：`frontend-e2e` 导出摘要新增 `workbench-main-path-shared-kb` 分区，仅在 shared 权限主链路用例失败上下文存在时统计 `shared_permission_semantic_ok` 并告警，降低主链路权限回归的定位成本
  - CI 告警汇总补齐（2026-05-09）：`frontend-e2e` 的 `threshold alerts` 新增 shared 分区汇总行（`shared_scope: workbench-main-path-shared-kb contexts=..., shared_permission_semantic_ok=...`），便于在无告警场景也快速确认 shared 诊断覆盖状态
  - CI 摘要语义收口（2026-05-09）：`frontend-e2e` 的 shared 分区补充 `expected` 文案（有 shared 失败上下文时期望 `>=1`，无上下文时期望 `0`），并在无上下文场景仍输出 shared 计数，减少诊断歧义
  - CI 稳态补充（2026-05-09）：`frontend-e2e` shared 分区的 error-context 匹配已从固定子串改为正则模式（`workbench-main-path.*shared.*kb`），降低测试标题微调导致诊断分区漏命中的风险
  - CI 稳态补充（2026-05-09 再补充）：shared 分区匹配已进一步收紧为变量化路径规则 `SHARED_CONTEXT_PATH_REGEX=workbench-main-path.*(shared-kb-actions-disabled|shared.*kb.*disabled)`，兼顾命名弹性与误匹配控制
  - CI 维护性优化（2026-05-09）：`frontend-e2e` 导出摘要对 `error-context.md` 的扫描已收敛为单次 `find` 后分组（main/shared/edge），减少重复 IO 并降低分区统计来源漂移风险
  - CI 维护性优化（2026-05-09 再补充）：`frontend-e2e` 导出摘要新增 `add_warning` 统一告警函数，收敛 `P0/P1` 计数与消息拼装逻辑，减少重复分支并降低阈值扩展时的改动面
  - CI 准确性补充（2026-05-09）：`frontend-e2e` 的 `workbench-main-path` 分区已排除 shared 专项上下文（通过 `SHARED_CONTEXT_PATH_REGEX` 反向过滤），避免 shared 用例失败时误触主链路导出提示告警
  - CI 规则收口补充（2026-05-09）：`frontend-e2e` 新增 `MAIN_CONTEXT_PATH_REGEX` 与 `EDGE_CONTEXT_PATH_REGEX`，main/edge/shared 三个分区匹配均改为变量化规则入口，降低手写字符串分叉风险
  - CI 维护性优化（2026-05-09 三次）：`frontend-e2e` 导出摘要新增 `print_matched_files` / `print_key_lines` 统一输出函数，收敛分区内重复循环，降低 main/shared/edge 三分区展示逻辑的维护成本
  - CI 诊断可见性补充（2026-05-09）：`frontend-e2e` 的 main/shared/edge 三个导出分区断言计数已补 `context_files_detected` 字段，便于直接核对当前分区统计是否来源于预期失败上下文样本
  - CI 工程化重构（2026-05-09）：`frontend-e2e` 的导出诊断逻辑已从 workflow 内联 Bash 抽离到 `frontend/scripts/ci_export_diagnostics.sh`（workflow 改为脚本调用），并补齐本地 Bash 3 兼容（移除 `mapfile` 依赖），实现“本地可复跑 + CI 可复用 + 规则单点维护”
  - CI 工程化重构（2026-05-09 补充）：`backend-e2e` 的 export consistency 摘要逻辑已抽离为 `backend/scripts/ci_export_consistency_summary.sh`，workflow 改为脚本调用并保持 Summary/artifact 输出路径不变，后续阈值规则维护可单点收敛
  - CI 回归护栏补齐（2026-05-09）：新增 `frontend/scripts/test_ci_export_diagnostics.sh` fixture 自测脚本并接入 `frontend-e2e` workflow（`Validate export diagnostics fixture tests`），用于在发布前校验导出诊断脚本的 counters/alerts 语义稳定性
  - CI 工程化扩展（2026-05-09）：前后端导出诊断脚本均已支持可选 JSON 摘要输出（`frontend: /tmp/frontend-e2e-export-summary.json`、`backend: /tmp/e2e-export-consistency-summary.json`）并纳入 workflow artifact，便于后续做趋势对比与机器消费
  - CI 回归护栏扩展（2026-05-09）：新增 `backend/scripts/test_ci_export_consistency_summary.sh` fixture 自测并接入 `backend-e2e`（`Validate export consistency summary fixture tests`），覆盖成功/缺陷/日志缺失三类诊断语义
  - CI 统一门禁（2026-05-09）：新增 `scripts/ci_diag_guard.sh`（配套 `scripts/test_ci_diag_guard.sh`）统一消费前后端 JSON 诊断摘要，支持 `strict-level=none|p0|any`；`frontend-e2e` 与 `backend-e2e` 均已接入 `Evaluate export diagnostics guard` 步骤并提供环境变量开关（默认 `none`）
  - CI 统一门禁（2026-05-09 补充）：前后端 workflow 的门禁默认级别已从 `none` 提升到 `p0`（仅拦截高优先级诊断），并将门禁判定结果（scope/strict/warnings/gate_result）写入 `GITHUB_STEP_SUMMARY` 与 guard artifact，降低排查上下文切换成本
  - CI 统一门禁（2026-05-09 策略化补充）：前后端 workflow 现按事件自动选择门禁级别：`push@main => any`、其余场景 `=> p0`；并在 summary 显式输出 `policy` 与 `selected_strict_level`，便于快速确认当前门禁生效策略
  - CI 统一门禁（2026-05-09 JSON 补充）：`ci_diag_guard` 新增 `--json-summary-file`，前后端 workflow 已产出 guard JSON（`/tmp/frontend-e2e-export-guard-summary.json`、`/tmp/backend-e2e-export-guard-summary.json`）并纳入 artifact，支持后续跨运行自动汇总
  - CI 统一门禁（2026-05-09 触发覆盖补充）：`frontend-e2e` 与 `backend-e2e` 的 `workflow_dispatch` 已新增 `export_diag_strict_level=auto/none/p0/any`，手动触发时可覆盖自动策略；summary 同步输出 `dispatch_override` 与 `policy_source`
  - CI 总览聚合（2026-05-09）：新增 `scripts/ci_export_diagnostics_overview.sh`（配套 `scripts/test_ci_export_diagnostics_overview.sh`），前后端 workflow 均新增 `Build export diagnostics overview`，产出 overview Markdown/JSON 并追加至 `GITHUB_STEP_SUMMARY` 与 artifact
  - CI 策略解析收口（2026-05-09）：新增 `scripts/ci_resolve_diag_strict_level.sh`（配套 `scripts/test_ci_resolve_diag_strict_level.sh`），前后端 workflow 的 strict-level 选择逻辑统一改为脚本解析（`event/ref/default/main_push/dispatch_override`），减少重复脚本分叉
  - CI fixture 入口收口（2026-05-09）：新增聚合脚本 `scripts/test_ci_e2e_tooling.sh`，前后端 workflow 分别以 `backend/frontend` scope 调用，统一执行 resolver/guard/overview 与端侧诊断脚本测试，减少 workflow 内重复测试步骤
  - CI 流水线收口（2026-05-09）：新增统一脚本 `scripts/ci_export_diag_pipeline.sh`（配套 `scripts/test_ci_export_diag_pipeline.sh`），将 strict-level 解析、guard 判定、overview 产物与 summary 追加合并为单入口；`frontend-e2e` 与 `backend-e2e` 已统一改为 `Run export diagnostics pipeline` 步骤
  - CI 输出降噪（2026-05-09）：`ci_diag_guard` 新增 `--quiet`，并在 `test_ci_diag_guard.sh` / `test_ci_resolve_diag_strict_level.sh` 中收敛预期失败分支输出，降低 fixture 步骤日志噪音
  - CI 启动与验活收口（2026-05-09）：新增 `scripts/ci_start_bg_process.sh` 与 `scripts/ci_wait_http_status.sh`（配套 `scripts/test_ci_service_bootstrap.sh`），统一后台进程启动与 HTTP 状态等待逻辑；`backend-e2e` / `frontend-e2e` 的后端启动与健康检查已切换到脚本调用
  - CI 诊断流程再收口（2026-05-09）：新增 `scripts/ci_export_diag_flow.sh`（配套 `scripts/test_ci_export_diag_flow.sh`），将“诊断摘要生成 + guard/overview pipeline”合并为单入口；前后端 workflow 对应步骤统一为 `Run export diagnostics flow`
  - CI artifact 收口（2026-05-09）：新增 artifact 清单文件 `scripts/ci_artifacts_backend.txt`、`scripts/ci_artifacts_frontend.txt` 与统一归集脚本 `scripts/ci_stage_artifacts.sh`（配套 `scripts/test_ci_stage_artifacts.sh`）；前后端 workflow 上传前新增 `Stage ... artifacts` 步骤，改为上传 staging 目录，降低 YAML 长列表维护成本
  - CI 失败诊断脚本化（2026-05-09）：新增 `scripts/ci_collect_backend_failure_diagnostics.sh` 与 `scripts/ci_build_frontend_failure_index.sh`（配套 `scripts/test_ci_collect_backend_failure_diagnostics.sh`、`scripts/test_ci_build_frontend_failure_index.sh`）；前后端 workflow 已改为脚本生成失败快照与 Playwright 失败索引，减少内联 shell 维护成本
  - CI 执行入口收口（2026-05-09）：新增 `scripts/ci_run_backend_e2e.sh` 与 `scripts/ci_run_frontend_e2e.sh`（配套 `scripts/test_ci_run_backend_e2e.sh`、`scripts/test_ci_run_frontend_e2e.sh`）；前后端 workflow 的 e2e 执行命令块已改为脚本调用，支持 `--dry-run` 语义校验与本地复跑
  - CI backend 启动收口（2026-05-09）：新增 `scripts/ci_boot_backend_instance.sh`（配套 `scripts/test_ci_boot_backend_instance.sh`），统一 backend 实例“启动 + 健康等待”流程；`backend-e2e` 与 `frontend-e2e` 的 backend 拉起步骤已改为单入口脚本调用
  - CI finalize 编排收口（2026-05-09）：新增 `scripts/ci_finalize_e2e_scope.sh`（配套 `scripts/test_ci_finalize_e2e_scope.sh`），统一执行“export diagnostics flow + artifact stage”两段收尾动作；前后端 workflow 已将两步合并为单步 finalize 调用
  - CI 失败日志展示收口（2026-05-09）：新增 `scripts/ci_print_log_files.sh`（配套 `scripts/test_ci_print_log_files.sh`），前后端 workflow 的失败日志展示步骤已统一为脚本调用；并将 `/tmp/frontend-e2e-backend.log` 纳入 frontend artifact 清单，避免仅控制台可见
  - CI upload 路径解耦（2026-05-09）：`ci_finalize_e2e_scope.sh` 新增 `--github-output-file` 输出能力，前后端 workflow upload 步骤已改为读取 finalize step output 的 `artifacts_stage_dir`，避免在 YAML 中硬编码 stage 路径
  - CI upload 命名解耦（2026-05-09）：`ci_finalize_e2e_scope.sh` 新增 `artifact_name` 输出，前后端 workflow upload 步骤的 `name` 字段已改为读取 finalize step output，命名策略集中在 finalize 调用参数
  - CI finalize workflow 入口收口（2026-05-11）：新增 `scripts/ci_finalize_e2e_for_workflow.sh`（配套 `scripts/test_ci_finalize_e2e_for_workflow.sh`），统一封装 workflow 侧 strict-level 默认值、事件上下文解析与 artifact 命名策略；前后端 workflow 的 finalize 步骤已改为调用该脚本，减少 YAML 参数拼装重复
  - CI artifact stage 指标补齐（2026-05-11）：`ci_finalize_e2e_scope.sh` 现会回传 `artifact_included_count/artifact_missing_count/artifact_manifest`，并将 artifact stage 统计追加到 step summary；`ci_finalize_e2e_scope` fixture 已补对应断言，方便快速定位“上传物为空/缺失”的根因
  - CI artifact stage 门禁补齐（2026-05-11）：新增 `scripts/ci_assert_artifact_stage_health.sh`（配套 `scripts/test_ci_assert_artifact_stage_health.sh`），前后端 workflow 新增 artifact stage guard 步骤并写入 summary/json；支持 `strict-level=none|warn|fail-on-empty|fail-on-missing`（当前默认 `warn`）
  - CI artifact stage 策略解析收口（2026-05-11）：新增 `scripts/ci_resolve_artifact_stage_strict_level.sh`（配套 `scripts/test_ci_resolve_artifact_stage_strict_level.sh`），前后端 workflow 的 artifact guard strict-level 改为脚本按 `event/ref/default/main_push/dispatch_override` 自动决策；并新增 `workflow_dispatch.artifact_stage_strict_level=auto|none|warn|fail-on-empty|fail-on-missing` 覆盖入口（当前策略：`push@main=warn`、其余 `warn`）
  - CI artifact stage 防误伤补丁（2026-05-11）：artifact guard 步骤改为“仅在 finalize 成功时执行”；若 finalize 失败则在 summary 记录 `skipped` 原因并不追加二次门禁失败，避免掩盖首个真实失败点
  - CI artifact stage PR 门禁扩展（2026-05-12）：`fail-on-empty` 现已扩展到 PR 场景，并支持通过 `min_included_count` 设定最小产物数阈值；当前前后端 workflow 已为 PR/关键分支场景启用 `fail-on-empty + min_included_count=2`，默认 `push@main` 仍维持 `warn` 以避免误伤现有单产物路径
  - CI artifact stage workflow 透传补丁（2026-05-12）：修复 `ci_finalize_e2e_for_workflow.sh` 未透传 `min_included_count` 到 `ci_finalize_e2e_scope.sh` 的回归，避免 PR 门禁配置在 finalize 包装层丢失
  - CI artifact upload 防二次报错补丁（2026-05-12）：前后端 workflow 的 artifact upload 步骤改为仅在 `finalize_*` 成功时执行，避免 finalize 失败后继续触发 `actions/upload-artifact` 的空 path 报错；新增 `scripts/test_ci_workflow_guards.sh` 静态校验 upload guard 条件与 finalize outputs 路径引用
  - CI artifact PR 路径感知扩展（2026-05-12）：新增 `scripts/ci_resolve_artifact_stage_path_level.sh`、`scripts/ci_collect_changed_files.sh`、`scripts/ci_resolve_artifact_stage_scope_config.sh`（配套 `scripts/test_ci_collect_changed_files.sh`、`scripts/test_ci_resolve_artifact_stage_scope_config.sh`、`scripts/test_ci_artifact_stage_scope_integration.sh`），将 artifact guard 的 PR 升级条件从“仅看 PR”收紧为“PR 且命中关键目录/文件”；backend/frontend workflow 现统一通过 scope 配置脚本解析 changed-files 路径、fallback paths、path-regex、`pr_ref_regex` 与 guard 摘要元信息，再生成变更文件清单，`actions/checkout` 同步切到 `fetch-depth: 0`。同时修正 path-regex 语义，使其既能命中真实目录前缀改动（如 `backend/...`、`frontend/...`），也能命中 `compose.full.yml` / workflow 文件本身，避免浅克隆、缺失 base SHA 或旧正则过窄带来的 guard 误判
  - CI fixture 稳定性修复（2026-05-11）：`scripts/test_ci_finalize_e2e_for_workflow.sh` 的“缺失事件上下文应失败”断言改为显式 `unset GITHUB_EVENT_NAME/GITHUB_REF` 后执行，避免在 GitHub Actions 默认环境变量存在时出现假阳性（expected fail but passed）
  - CI 告警增强（2026-05-08）：`frontend-e2e` 导出摘要新增阈值告警（`threshold alerts`），当 `main-path` 或 `edge-cases` 的关键计数低于预期时会直接输出 `expected vs actual`，便于第一时间判断是下载层、响应头层还是 404 语义层回归
  - 回归稳态收口（2026-04-22）：修复 `workbench-edge-cases` 在并发回归下的偶发抖动（Context tab 定位收敛到 Inspector 顶部导航，取消后同文案重发场景改为“API cancel + UI 去重可见性断言”）；最新本地全量回归再次验证为 chromium `30/30`。
  - 回归稳态补充（2026-04-22）：修复 `workbench-edge-cases` “切换 token 后导出 404 提示”用例竞态（切 token 前先等待任务详情导出按钮可用）；本地回归复测：chromium 串行（`--workers=1`，与 CI 对齐）`30/30` 通过。
  - 鉴权接口：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`
  - `full-data-auth` 增量（2026-05-09）：用户模型新增 `role`（`admin/user`），首个注册用户自动授予 `admin`，并新增 admin-only 用户列表接口 `GET /api/auth/users`
  - 会话鉴权治理（最小版）：`POST /api/auth/refresh`、`POST /api/auth/logout`、`POST /api/auth/logout-all`、`GET /api/auth/sessions`、`DELETE /api/auth/sessions/{session_id}`
  - 审计扩展已落地：记录 `login/logout/refresh/settings_update/settings_validate/task_create/task_cancel/task_timeout/task_failed/rag_ingest/rag_kb_clear/rag_kb_delete` 到 `audit_logs`
  - 审计查询接口：`GET /api/audit/logs`（支持 `event_type/session_id/task_id/start_at/end_at` 与分页）
  - 除 `GET /health` 与 `/api/auth/*` 外，其余业务 API 均要求 `Authorization: Bearer <token>`
  - `settings/validate` 远端预检支持 `HEAD` 失败自动回退 `GET`，降低网关不支持 HEAD 导致的误判
  - `settings/validate` 预检请求会携带 `Authorization`；当远端返回 `401/403` 时，明确返回 `remote_api_key_unauthorized`，避免误报为网络错误
  - `GET /api/sessions/{session_id}/usage/summary` 兼容保留（会话聚合）
  - Memory：`GET .../memory/status`、`POST .../memory/add`、`POST .../memory/query`
  - 删除会话时会 best-effort 清理 `memory_{session_id}` collection，降低孤儿向量残留
  - `/health` 含 Chroma 可达性
- frontend：
  - `rag-rbac-lite` 前端收口（2026-05-09）：知识库治理弹窗已接入 `currentUser.role`，普通用户对 `shared-*` 知识库的清空/删除按钮禁用，并提示权限受限；与后端共享库写权限规则一致
  - Ant Design 6 兼容性修复（2026-05-08）：`Workbench` 任务中心抽屉已将 `Drawer width` 替换为 `size`，消除控制台废弃警告（`[antd: Drawer] width is deprecated`）
  - `full-trace-session` 收口补充（2026-05-08）：任务详情页与会话导出入口的下载逻辑已抽取为共享工具（`frontend/lib/export-download.ts`），统一 `content-disposition` 文件名解析、鉴权下载与 `ApiError` 语义，降低后续导出链路维护分叉风险
  - 新增 Auth Gate：登录/注册入口页、token 本地持久化、401 过期自动回登录
  - Auth 页面可读性收口：移除面试导向文案、白底区域表单与 Tab 对比度提升、退出按钮垂直居中优化
  - Auth 交互细化：登录区标题文案改为“账号登录”；提交按钮禁用态提升对比度；退出入口迁移至左下角设置模块并避免与折叠控件冲突
  - Auth 交互细化（继续）：移除“当前用户：未登录”提示；注册邮箱格式前置校验并给出友好错误；登录表单 autofill/已填充态样式优化，浅色背景下可读性更稳定
  - 登录页品牌文案收口：左侧标题与说明融合主页主叙事（可观测智能体、对话到任务闭环），并补回 SSE/Trace、Memory/RAG、Token/Cost 关键信息点
  - 登录交互修复：密码框显隐图标恢复可见并支持显示/隐藏切换
  - 登录页国际化：Auth Gate 新增 `auth` 文案分组并接入中英文词条，覆盖登录页标题/说明/表单标签/占位符/按钮与鉴权反馈提示
  - 登录页设置增强：新增轻量设置模块（语言/主题/主题色）并接入 `Preferences`；登录页视觉样式改为跟随深浅主题与主色实时切换
  - 账号切换收口：退出/401/重新登录时清空 Query 缓存与流式轨迹状态，避免跨账号残留
  - 登录态增强：本地持久化 `refresh_token`，401 时自动调用 `/api/auth/refresh` 轮换 token 并重试请求；刷新失败再回登录
  - 侧栏账户展示收口：当前登录用户已融合到左下角“设置”弹窗顶部，并采用与“主题/主题色/语言”一致的行样式（图标 + 标题 + 值）
  - 首次引导页已移除：注册/登录后直接进入工作台
  - 新增运行态提示条：显示当前 `mock/remote` 状态，并可一键打开模型设置
  - 发送前校验补强：`remote` 且未配置 `api_key` 时前端阻断发送并引导去设置
  - 审计入口迁移到左下角设置菜单（方案 A）：独立审计子页支持事件类型/时间范围/`session_id`/`task_id` 过滤，详情展开，以及 JSON/CSV 导出（可选“当前页/全部筛选结果”）
  - 设置菜单新增“知识库治理”入口：在设置弹窗内查看当前账号知识库列表、来源采样与文档条数，并支持清空/删除
  - 设置菜单新增“用量统计”入口：在设置弹窗内查看用量仪表盘，支持全局/当前会话切换、趋势查看、会话榜与任务榜
  - 知识库治理交互优化：列表表头统一左对齐（末列明确“操作”）、刷新改为图标按钮、清空/删除按钮风格统一；来源标签支持悬浮查看完整值并补充“采样统计”说明
  - 知识库治理信息增强：新增“样本片段”预览列（悬浮查看完整文本），避免只看到来源标签而无法判断真实内容
  - 审计页可读性优化：主视图改为分页表格展示，筛选区升级为双行下拉+输入框检索并统一控件尺寸，事件类型标签化；总条数下置表格左下角，操作区右对齐，并恢复行展开明细（展开内不再二次展开，主表保留会话/任务 ID，分页默认每页 10 条）
  - 弹窗状态收口：审计日志弹窗与模型设置弹窗在每次打开时都会重置筛选/分页/提示状态，避免沿用上次操作痕迹
  - 模型设置弹窗交互调整：打开时按后端配置回显当前 `mode/provider/model/base_url`，并显式关闭浏览器自动填充（避免凭证误填）
  - 修复模型设置回显异常：解决弹窗打开时被默认值覆盖导致显示 `mock` 的问题
  - 模型设置弹窗优化：底部元信息新增 `base_url` 展示；`remote` 模式新增“仅支持 OpenAI-compatible 接口”提示
  - 模型设置弹窗模式收口：切换 `mock/remote` 时表单区与下方元信息区实时联动；`mock` 固定回显 `provider=mock`、`model=mock-gpt` 并隐藏 `base_url/api_key`
  - 模型设置表单校验收口：`remote` 模式下 `provider/model/base_url` 必填；`api_key` 在“首次 remote 配置”时必填，后续留空将沿用已存密钥
  - 模型设置提示兼容性修复：弹窗结果提示改为 `App.useApp().message` 上下文调用，避免 Ant Design 主题上下文警告
  - 模型设置交互补充：`基础地址/数据库` 在元信息区改为普通文本展示；切换到 `mock` 并保存时会清空远端配置（含 `api_key/base_url`）
  - 模型设置回显修复：当已保存为 `remote` 配置时，切换回 `remote` 会正确回显后端已存的 `provider/model/base_url`
  - 聊天体验修复：发送后立即显示用户临时消息；assistant 流式消息仅在生成中/失败态显示，避免与已落库历史回复重复
  - `remote-provider-hardening` 前端收口：流式错误与设置校验结果已按 `error_code` 做本地化映射，并在提示中保留错误码，降低真实厂商联调排障成本
  - `task-cancel-timeout` 前端首版：Inspector「当前任务」支持取消运行中任务，流式状态支持 `cancelled/timeout` 事件与提示
  - `running-task-recovery` 前端首版：持久化当前会话，在刷新页面或切回会话时自动探测并接管该会话下 `pending/running` 任务流（复用后端 running reconnect + delta）
  - `running-task-recovery` 可视化补充：聊天区新增自动恢复提示条，展示恢复中/恢复成功/恢复失败状态（自动消退，可手动关闭）
  - 会话切换串台修复：流式状态新增 `session_id` 绑定并按当前会话隔离展示；切换会话时不再短暂显示其他会话任务
  - 恢复误报修复：任务实际完成后若任务列表短暂滞后为 `running`，自动恢复不会再误报“任务流恢复失败”（同任务去重恢复 + 409 视为无害收敛）
  - 聊天滚动修复：流式输出时若用户主动上滑阅读历史消息，不再被强制拉回底部；仅在贴底状态自动跟随新输出
  - 取消态提示修复：任务取消/超时后即使后端追加 `error(task_cancelled/task_timeout)`，前端也不再误判为失败态，不再出现“重试上次发送”
  - 结束补拉提示修复：流结束后的 `trace/delta` 自动补拉改为静默，不再把底部状态覆盖成“暂无新的轨迹增量”
  - 同文案重发修复：待发送用户消息去重改为按 `task_id` 判定，取消后再次发送相同内容也会立即显示，不再被上一条同文案误去重
  - 取消按钮即时可用修复：发送后会立即刷新 `tasks/messages`，并在任务列表尚未回刷时用流式任务兜底展示“当前任务”与取消按钮
  - 取消后卡住修复：取消任务成功后前端会本地中断活动 SSE 流并立即退出“生成中”，发送按钮无需长时间等待即可恢复可用
  - 远端取消防抖：`remote` 模式取消后增加短暂发送冷却，避免“刚取消立刻重发”触发上游限流
  - 滚动交互升级：消息区“回到底部”按钮锚定在聊天区右下角（非滚动内容内）；上滑阅读时若有新输出会显示动态徽标与轻脉冲提示，点击可快速回到底部
  - 回底按钮避让微调：按钮位置进一步右移并上移，减少对底部消息与输入区域的遮挡
  - 会话命名收口：空会话在首条消息发送时自动以消息前缀命名（仅占位标题且无历史消息时触发）
  - 三栏工作台（会话 / 消息 / 轨迹与上下文）
  - 右侧 Inspector（Context）完成运行态信息架构收口：概览 KPI + 同步诊断 + 当前任务 + 最近任务分区，弱化堆叠卡片并保留扩展位
  - `full-trace-session` 首步收口：新增任务详情独立页 `GET /tasks/{task_id}`（前端路由 `/tasks/[taskId]`），集中展示任务快照、Trace 时间线/流程图回放与任务导出
  - `full-trace-session` 重排收口：主工作台恢复为中栏聊天主视图；任务中心改为右侧抽屉承载任务索引筛选/排序/搜索，避免替换聊天上下文；任务级分析统一下沉到 `/tasks/[taskId]`
  - `full-trace-session` 清理收口：右侧 Inspector 旧任务块已从代码中物理删除（不再以样式隐藏保留），主入口以“任务中心 + 任务详情页”作为唯一任务分析路径
  - `full-trace-session` 交互细化：运行调试弹窗视觉样式与主站统一；任务中心“任务详情”按钮提升可见性；右侧“当前任务”卡片仅保留取消动作
  - `full-trace-session` 交互细化补充：任务中心头部已移除模式/模型信息，保留单一“关闭”操作并固定到右侧，降低头部视觉噪音
  - `full-trace-session` 样式微调：运行调试弹窗改为上下单列并移除分区高亮底色，保持与主界面统一底色体系
  - `full-trace-session` 回归对齐：前端 Playwright 用例已切换到“聊天头部任务中心入口 -> 任务中心抽屉 -> 新标签任务详情导出”主链路，不再依赖已移除的 Inspector 任务导出选择器
  - `trace-export-json-md` 首版已落地：支持单任务导出 JSON 与 Markdown（含任务元信息、task-linked 消息、TraceStep、RAG chunks 与 usage），并在任务快照区提供一键导出入口
  - `session-export-lite` 首版已落地：支持当前会话导出 JSON 与 Markdown（会话消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage 汇总），入口已统一迁移到左侧会话行“...”菜单（方案 1，按会话行触发）
  - 任务索引支持前端本地筛选与排序（状态筛选、时间顺序、失败任务优先），便于运行态排障
  - 任务中心样式收口：任务列表改为审计日志同款表格风格（筛选/搜索工具栏 + 表格 + 分页）；顶部筛选区采用审计日志同款双行布局与控件尺寸体系，并保留任务详情快捷入口
  - 任务中心细化修复：全局任务范围改为自动拉取完整分页后再本地筛选，避免出现“全局条数少于当前会话”的首屏截断错觉；同时移除“用量来源”列并下调“任务详情”按钮为轻量操作样式
  - 任务索引支持关键词快速定位（标题/ID）与失败摘要提示，便于快速定位异常任务
  - Trace 面板支持步骤类型筛选、关键词检索与类型计数（时间线/流程图一致生效），提升长轨迹排障效率
  - 右侧面板完成一体化收口优化：Trace 密度切换、Context 快速跳转、状态徽标与分区说明统一，兼顾当前能力与后续扩展
  - 左侧与中栏完成统一风格优化：会话导航强化激活层级、聊天头部运行态信息条收敛、消息与输入区交互节奏统一
  - 根据最新交互收敛要求，已移除会话状态胶囊与输入计数提示，头部恢复紧凑模式标签展示
  - 轨迹支持「时间线 / 流程图」双视图（thought/action/observation/tool/rag 区分）
  - 会话支持分页加载、重命名、删除
  - 设置弹窗新增“运行调试”子页：承接 Memory 状态/add/query 与 RAG 状态/ingest/query
  - RAG 知识库 ID 改为“输入后应用”模式，避免输入过程频繁触发状态请求
  - 设置弹窗新增知识库治理子页：按账号列出知识库、显示来源采样，并支持行级清空/删除
  - Trace 元信息支持展示每步 cost（`meta.cost_estimate`）
  - usage 展示增强：支持全局/会话自动切换汇总，含加载/错误/空状态与覆盖率（with_usage/total）
  - usage 来源可视化：当前任务与任务中心/任务详情已展示 usage 来源（provider/estimated）
  - 用量统计弹窗补充来源分布：展示 provider/estimated/mixed/legacy 四类任务数，并对历史无来源字段任务标记为“旧数据”
  - 用量统计弹窗支持来源筛选（全部/官方/估算/混合/旧数据），便于按来源排查成本与 token 分布
  - `trace/delta` 支持流式期间自动轮询同步（静默）+ 失败退避重试，并在流结束后自动补拉一次
  - 任务 SSE 支持运行中重连：`GET /api/tasks/{task_id}/stream` 在 `running` 状态下可重连并回补增量
  - Inspector 上下文摘要新增 delta 同步健康度（状态/重试次数/最近成功时间/下次重试/最近错误/恢复提示），恢复提示为短时展示并自动消退；重试中展示秒级倒计时
  - 页面处于后台（不可见）时暂停 delta 自动同步，回到前台自动恢复
  - Inspector 在 delta 连续失败时提供轻量告警提示（不阻塞主链路）
  - 前端 ESLint 基线已落地，`npm run lint` 可直接执行且当前告警已清零
  - W3 增量：mock 工具链路支持可复现错误语义（`[mock-tool-error]` 可恢复重试、`[mock-tool-fatal]` 致命失败），`tool_end` / `error` / `trace.meta.tool` 已携带 `retry_count/error`
  - W3 优化：新增本地计算器工具（`[calc:1+2*3]` 或“计算 1+2*3”），统一走 `tool_start/tool_end/trace` 生命周期
  - W1 优化：设置弹窗支持“校验配置”按钮（调用 `POST /api/settings/validate`，校验通过后再保存）
  - W1 设置语义收口：`remote` 模式下 `api_key` 留空将沿用已存密钥（首次配置仍必填）；保存/校验反馈统一使用 message 浮层提示（不再使用顶部可关闭提示条）
  - W2 稳定性优化：前端合并 SSE/`trace/delta` 步骤后按 `seq` 稳定排序，降低时间线/流程图在高频增量场景下的乱序概率
  - W2 稳定性优化：`trace/delta` 增加任务隔离保护，旧任务延迟返回不再污染当前任务轨迹
  - W3 稳定性优化：前端仅在 `error.fatal=true` 时将全局 phase 置为 `error`；可重试工具错误不再误伤主任务状态
  - W1/W2 稳定性优化：SSE 流式期间改为周期 heartbeat，且后端 trace 持久化增加节流，降低连接误判与数据库写放大
  - W2 重连流优化：`running` 任务重连时 `done/error` 事件补齐 `session_id/step_id` 并标记 `resumed=true`，契约更一致
  - W2 重连轮询优化：重连流改为“有增量快轮询、无增量退避慢轮询”，降低 DB 压力与事件噪声
  - W2 后端性能优化：重连流复用当前 task 快照做 delta 计算，减少循环内重复 DB 查询
  - W1/W2 可调优优化：trace 节流与 running 重连流轮询/heartbeat 参数均支持环境变量配置
  - W1 usage 语义优化：`completion_tokens` 改为基于最终输出文本估算（覆盖流式与 fallback），不再按 chunk 数近似
  - W2 前端稳态优化：SSE 事件按 `task_id` 做活动任务隔离，避免并发/延迟事件串台
  - W2 前端收敛优化：SSE phase 统一归一（`completed→done`、`failed→error`）并集中化流式文案，减少分支判断
  - W2 前端稳态优化：当存在活动任务时，缺失 `task_id` 的非 `start` 事件将被忽略，进一步降低串台风险
  - W2 前端性能优化：`trace` 事件合并步骤时移除重复 `upsert` 计算，降低高频流式阶段状态更新开销
  - W2 前端展示优化：phase 映射补齐 `thinking/tool_running/tool_retry`，统一显示为运行态标签
  - W1/W2 前端国际化优化：流式状态与错误提示（start/delta/tool/error/close 等）改为 i18n 文案驱动，不再依赖硬编码英文
  - W2 收口优化：`trace/delta` 的 `traceCursor` 改为单调递增（避免并发请求导致游标回退），token 事件合并为单次 store 更新；空闲提示纳入 i18n 并随语言切换
  - W1/W2 国际化维护优化：store 默认流式文案改为复用 `en.stream` 单一来源，避免与 i18n 文案表双份维护导致漂移
  - W2 后端语义优化：`GET /api/tasks/{task_id}/trace/delta` 的 `lag_seq` 改为基于任务快照真实尾游标计算，避免无信息量的恒零值

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
- `done`
- `error`

对齐规则：
- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 作为工具生命周期事件，与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中先空内容，再由 `token.delta` 拼接；REST 中是完整内容。
- REST 返回步骤由后端 `TraceStep`（Pydantic）校验，前端按 `lib/types/trace.ts` 对齐消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 知识库级 collection：`kb_{user_hash}_{knowledge_base_id}`（用户隔离）
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 嵌入策略：当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- 错误语义：
  - Chroma 不可达时，`memory/add` 与 `memory/query` 返回 503
  - Chroma 不可达时，`rag/ingest` 与 `rag/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

### 通俗理解：为什么有 RAG 还需要 Memory

- `PostgreSQL`：系统“完整账本”。保存会话、消息、任务、trace、usage 的原始记录。
- `Chroma Memory`：当前会话“便签本”（`memory_{session_id}`）。保存可语义召回的会话记忆片段（含任务完成后的自动摘要）。
- `Chroma RAG`：项目“知识库”（`kb_{user_hash}_{knowledge_base_id}`）。保存导入文档的分块内容，并按用户隔离用于知识检索增强。

三者是互补，不是重复：

- 只用 `RAG` 不够：RAG 主要是外部知识，不包含你在本次对话里刚确认的偏好和约束。
- 只用 `PostgreSQL` 不够：结构化存储适合完整留档，但直接每轮全量喂给模型成本高；Memory 用向量检索可只取最相关片段。
- 所以实际分工是：`PostgreSQL` 管“真实历史”，`Memory` 管“会话记忆”，`RAG` 管“外部知识”。

一个直观例子：

- 你说“后续都用中文、回答不超过 5 行” -> 这类临时约束更适合进 Memory。
- 你导入产品手册/API 文档 -> 这类长期资料进 RAG。
- 你完整的对话与任务执行记录 -> 始终落 PostgreSQL。

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

如需一键启动（会自动拉起 `postgres/chroma`，再启动 backend/frontend），可直接执行仓库根目录脚本：

```bash
./start_insightagent.command
```

macOS 下也可在 Finder 中双击 `start_insightagent.command` 直接启动。
该脚本已修复 PostgreSQL 就绪检查（不再依赖 `docker compose exec`，避免 `backend/.env` 缺失导致误判未就绪），并改用 Chroma `v2` heartbeat 检测，兼容新版本镜像；启动前会额外清理旧 `uvicorn/next dev` 进程，并采用轮询方式等待服务健康。

## 后续阶段最终决策（定位 / 面试 / 单 Mac / 部署）

### 后续开发总路线（建议按优先级）

1. P0：历史任务详情与 Trace 回放、Trace/任务 JSON + Markdown 导出、会话级导出、remote provider 错误体验收口、最小 e2e 主链路。
2. P1：任务取消与超时、运行中任务恢复、RAG 知识库最小治理、usage 统计增强、审计事件补充。
3. P2：轻量 RBAC、实验性 Trace step 重跑、生产部署 Runbook、Playwright e2e（provider 官方 usage 对齐首版已完成，后续补 e2e 与前端来源展示）。

### 当前明确暂缓

1. Redis/Kafka/Celery 分布式队列（当前规模用进程内取消/超时/并发上限即可）。
2. Kubernetes、微服务拆分、服务网格（复杂度明显高于收益）。
3. 企业级 SSO/RBAC 全套（保留扩展位，先做轻量 RBAC）。
4. 复杂多模型编排面板、复杂多跳 RAG、大规模重排体系（先完成稳定性与治理闭环）。
5. 大规模 UI 重构、PDF/视频/GIF 自动导出（先用当前 UI + JSON/Markdown 导出满足演示与复盘）。

### 部署策略（结合单 Mac 开发 + 后续正式部署）

1. 本机开发：继续使用 `docker-compose.yml`（Chroma）/ `compose.full.yml`（backend + frontend + Chroma + PostgreSQL）。
2. 前端：优先部署到 Vercel 免费版（静态资源 + Next.js 站点）。
3. 后端与状态服务：独立部署 FastAPI + PostgreSQL + Chroma（不要与前端同进程耦合）。
4. 面试演示：准备“一键演示脚本”（导入知识库 -> 发起任务 -> 查看 Trace/成本）。

## 下一步（W4+）

- `full-trace-session-lite` 与导出链路持续推进中：任务快照、单任务导出、会话导出、remote 错误体验与主链路 e2e 首版脚本均已落地；导出稳定性回归脚本已补齐，下一步补失败快照归档与导出异常可观测字段。
- `task-cancel-timeout` 后端 e2e（cancel + timeout）与 CI 首版已落地，`running-task-recovery` 前端首版与可视化提示已落地，`rag-kb-governance-lite`、`usage-dashboard-lite`、`audit-event-expansion` 与 `provider-usage-alignment` 已完成首版并补齐来源趋势联动；前端可视化回归 CI 已扩展到主链路导出/取消恢复/边界异常场景并接入 smoke 跨浏览器矩阵，本地最新回归为 chromium `30/30`、smoke `15/15`，下一步继续补异常态覆盖深度与跨会话切换下 UI 态断言。

### 最新同步（2026-04-23）

- 任务中心表格头部计数文案（如 `17 / 17`）已移除，分页不再显示该类汇总计数。
- 任务中心“失败置顶”开关已移除，任务顺序仅由时间排序控制（最新/最早）。
- 任务中心筛选行与表格样式完成统一化优化：更轻量的筛选区、清晰表头层级、统一操作按钮视觉。
- 任务中心表格视觉继续收口：去除偏蓝底色，恢复中性底色；“重置筛选”按钮已对齐审计日志默认样式。
