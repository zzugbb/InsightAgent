# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 → 任务执行 → 轨迹解释 → Memory/RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前开发进度（按完整计划对齐）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| W1 主链路 | 已完成 | 会话/任务/消息持久化、SSE 流、trace 回放与 delta、前端工作台闭环 |
| W2 可观测 + Memory 最小闭环 | 已完成（已收口） | 轨迹时间线+流程图、TraceStep 契约、Chroma 会话 memory 状态/写入/检索、`trace/delta` 流式阶段增量持久化（`seq` 递增） |
| W3 Tool + ReAct | 已完成（mock 范围） | mock 工具调用循环、可恢复重试/致命失败语义、SSE/Trace 对齐 |
| W4 RAG + 成本展示 | 已完成（已收口） | RAG ingest/query/status、执行链路 RAG 命中回填、Token/Cost 估算与 UI 展示、`compose.full.yml` |
| 阶段 5+ 产品化 | 进行中 | 除 `full-data-auth` 与 PostgreSQL 运行时收敛外，`RBAC-lite`、`rag-rbac-lite`、任务取消/超时、running task 恢复、任务/会话导出、主链路 e2e 与 CI 诊断护栏均已落地；当前主缺口转向真实工具运行时、治理深化与队列化可靠性 |

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
  - CI artifact PR 路径感知扩展（2026-05-12）：新增 `scripts/ci_resolve_artifact_stage_path_level.sh`、`scripts/ci_collect_changed_files.sh`、`scripts/ci_resolve_artifact_stage_scope_config.sh`、`scripts/ci_load_artifact_stage_scope_config.sh`、`scripts/ci_run_artifact_stage_guard.sh`、`scripts/ci_write_skipped_artifact_guard_summary.sh`（配套 `scripts/test_ci_collect_changed_files.sh`、`scripts/test_ci_resolve_artifact_stage_scope_config.sh`、`scripts/test_ci_artifact_stage_scope_integration.sh`、`scripts/test_ci_load_artifact_stage_scope_config.sh`、`scripts/test_ci_run_artifact_stage_guard.sh`、`scripts/test_ci_write_skipped_artifact_guard_summary.sh`），将 artifact guard 的 PR 升级条件从“仅看 PR”收紧为“PR 且命中关键目录/文件”；backend/frontend workflow 现已把 artifact guard 主逻辑与 finalize 失败时的 skipped summary 都下沉到脚本：先由 scope 配置脚本生成规则，再通过 load helper 落地为 shell 变量，供 changed-files、path-regex、`pr_ref_regex` 与 guard 摘要元信息复用，`actions/checkout` 同步切到 `fetch-depth: 0`。同时修正 path-regex 语义，使其既能命中真实目录前缀改动（如 `backend/...`、`frontend/...`），也能命中 `compose.full.yml` / workflow 文件本身，避免浅克隆、缺失 base SHA 或旧正则过窄带来的 guard 误判
  - CI workflow guard 收口（2026-05-13）：`backend-e2e` 与 `frontend-e2e` 已移除对 `--guard-markdown-out/--guard-json-out` 的显式传参，guard 输出路径统一由 finalize/scope 脚本解析；`scripts/test_ci_workflow_guards.sh` 也已切换为验证“workflow 继续调用统一 guard 脚本，但不再硬编码 guard 输出路径”
  - `tool-runtime-productionization` 后端切片持续推进（2026-05-13）：已将 mock tool plan 构建与单 tool 执行逻辑从 `backend/app/services/chat_execution_service.py` 抽离到新的 `backend/app/services/tool_runtime.py`，并补出统一入口 `execute_tool_spec`；当前进一步收口为最小 registry 结构（`mock_plan` / `mock_retrieve` / `calc_eval`）、显式 `ToolInvocation` 归一化边界，以及带最小 runtime 元信息的 `ToolRegistration(name, kind, label, retryable_by_default, default_timeout_ms, requires_user_context, supports_result_preview, runner)` 注册项结构；同时已新增并接线多个内部 helper：`build_tool_result_preview()`、`tool_requires_user_context()`、`is_tool_retryable_by_default()`、`get_tool_default_timeout_ms()`、`ensure_tool_registration()`、`maybe_raise_mock_tool_execution_error()`、`ToolRuntimeContext / build_tool_runtime_context()`、`compute_tool_retry_decision()`、`build_tool_end_payload()`、`build_tool_success_meta()`、`build_tool_error_meta()`、`build_tool_start_payload()`、`build_tool_error_payload()`、`build_tool_phase()`、`build_tool_execution_policy()`、`build_action_step_initial_meta()`、`build_action_step_initial_step()`。本轮又继续补齐更高层的 attempt 生命周期与编排收尾 helper：`build_tool_attempt_start_events()`、`build_tool_attempt_bundle()`、`build_tool_attempt_execution()`、`build_tool_attempt_loop_result()`、`build_tool_attempt_loop_terminal_result()`、`build_tool_plan_item_retry_loop_result()`、`build_tool_attempt_success_events()`、`build_tool_attempt_error_events()`、`build_tool_step_success_update()`、`build_tool_step_error_update()`、`build_tool_attempt_success_transition()`、`build_tool_attempt_error_transition()`、`build_tool_attempt_result()`、`build_tool_attempt_outcome()`、`build_tool_iteration_context()`、`build_tool_iteration_execution()`、`build_tool_iteration_success_artifacts()`、`build_tool_plan_item_success_bundle()`、`build_tool_plan_item_result()`、`build_tool_plan_item_execution_result()`、`build_tool_plan_item_execution()`、`build_tool_plan_item_postprocess()`、`build_tool_plan_item_success_effects()`、`build_tool_plan_item_terminal_effects()`、`build_tool_rag_followup()`、`build_tool_step_output()`、`build_tool_observation_entry()`、`build_tool_trace_event()`、`build_tool_terminal_failure_transition()`、`build_tool_rag_step()`、`build_tool_prompt_with_observations()`；`chat_execution_service.py` 现又继续减少手工编排，改为直接消费 attempt bundle、attempt execution、attempt loop result、attempt loop terminal result、retry loop 最终结果、plan-item 顶层 `tool_end/error/retryable/postprocess` 结果，以及 success/fatal 两条路径的 effects 结果。期间发现一个 CI 回归：`build_tool_plan_item_execution()` 在新抽象后未透出 `iteration_execution`，导致成功流在编排层读取 `plan_item_execution["iteration_execution"]` 时抛 `KeyError`，任务流只发 `error` 不发 `done`，从而同时击穿后端 baseline 与前端 smoke；现已补回该字段并新增 focused 回归覆盖，并继续补了 attempt bundle、attempt execution、attempt loop result、attempt loop terminal result、retry loop 最终结果、plan-item 顶层事件访问、success/fatal effects、以及顶层 effects 透出契约测试，当前 SSE/trace/e2e 契约恢复稳定。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 61 条兼容测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-13，retry loop helper）：本轮继续坚持“先补 failing test 再改实现”，新增 `execute_tool_plan_item_retry_loop()`，将单个 tool plan item 的完整 retry loop 控制从 `chat_execution_service.py` 下沉到 `backend/app/services/tool_runtime.py`，并保持 `tool_start/state` 仍先于实际执行发出、`tool_end/error` 顺序不变、success path 的 `trace/observation/rag_followup` 与 terminal failure path 的 `state/error` 收尾语义不变。`chat_execution_service.py` 现改为消费该 helper 的事件流与终态对象，外部 SSE/trace/e2e 契约保持稳定。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 64 条兼容测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，loop result flattening）：在不改外部 SSE/trace/e2e 契约的前提下，继续补 focused failing tests，并新增 `build_tool_plan_item_retry_loop_execution_result()`，让 runtime 直接为单个 tool loop 暴露更扁平的终态字段 `trace_event/success_effects/terminal_effects/should_return`，同时保留旧的嵌套结果对象；`chat_execution_service.py` 因此进一步减少对 `loop_result/retry_loop_result/loop_terminal_result` 的穿透访问，成功流与 terminal failure 流都只消费更高层结果。最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，stream effects helper）：继续坚持先补 failing tests，再新增 `build_tool_plan_item_stream_effects()`，把单个 tool loop 结束后 service 真正要消费的后处理效果进一步收口为 `trace_steps/trace_events/observation/terminal_effects/should_return`；`chat_execution_service.py` 已切到逐个消费这组 effects，保持 trace append 与 trace SSE/persist 的原有节奏不变，同时减少 success path 的 rag follow-up 分支胶水。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 66 条兼容测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，terminal return helper）：继续先补 failing tests，再新增 `build_tool_plan_item_terminal_return_effects()`，把 terminal failure 分支里 service 还在手工拼的任务状态、失败审计事件和 `state(error)` payload 收口到 runtime helper；`chat_execution_service.py` 已切到消费该 helper，terminal 收尾逻辑继续缩短，外部错误语义和 SSE 契约保持不变。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 67 条兼容测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，success seq increment）：继续在不改外部契约的前提下压薄 success path，将 `build_tool_plan_item_stream_effects()` 继续扩展为直接暴露 `seq_increment`，让 `chat_execution_service.py` 不再回头依赖 `loop_execution_result["success_effects"]["rag_followup"]` 来维护 `seq_cursor`；当前 service 成功分支已进一步收敛为“消费 stream effects 并执行副作用”。focused 回归脚本保持 67 条兼容测试，`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，observation delta）：继续压薄 success path，将 `build_tool_plan_item_stream_effects()` 扩展为直接暴露 `tool_observations` 增量列表，统一表达本次 tool 成功后需要追加到 provider prompt 的 observation 文本；`chat_execution_service.py` 已切到通过 `extend(...)` 消费该 delta，不再手工 `append(str(stream_effects["observation"]))`。focused 回归脚本保持 67 条兼容测试，`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，service-effects helper）：继续把 `chat_execution_service.py` 的单个 tool 分支压缩为“消费更高层 effects 并执行副作用”，新增 `build_tool_plan_item_service_effects()`，统一归并 `trace_steps/trace_events/tool_observations/seq_increment/should_return/terminal_return_effects`；`chat_execution_service.py` 已切到优先消费这层更高层结果。focused 回归脚本已扩展到 69 条兼容测试；同时已更新 [tool-runtime-productionization handoff](</Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md>) 以反映最新真实状态。最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，service-effects follow-up）：继续先补 failing tests，再把 `build_tool_plan_item_service_effects()` 进一步抬高到更接近 service 最终消费形态，新增 `trace_writes` 与 `continue_update`，分别统一表达 trace append/SSE/persist 指令，以及 success path 的 `tool_observations + seq_increment` 增量；`chat_execution_service.py` 已切到消费这两组更高层结果，同时保留旧的顶层兼容字段，外部 SSE/trace/e2e 契约保持不变。focused 回归脚本仍为 69 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，next-action helper）：继续先补 failing tests，再把单个 tool 的“继续流转 / 终止返回”分支选择也上提到 runtime，新增 `build_tool_plan_item_next_action()`，让 `build_tool_plan_item_service_effects()` 直接暴露 `next_action(kind=continue|return)`；`chat_execution_service.py` 已切到通过该对象统一消费 `continue_update` 与 `terminal_return_effects`，同时保留既有兼容字段，外部 SSE/trace/e2e 契约保持不变。focused 回归脚本仍为 69 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，return-action helper）：继续先补 failing tests，再把 terminal path 里 `complete_task / record_failure_event / state(error)` 这组三连调用的参数拼装收口到 `build_tool_plan_item_return_action()`；`chat_execution_service.py` 已切到通过该 helper 执行 terminal return 副作用，不再直接拆 `terminal_return_effects` 字段，同时保留外部 SSE/trace/e2e 契约不变。focused 回归脚本已扩展到 70 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，trace-write-action helper）：继续先补 failing tests，再把 `trace_writes` 的执行输入抬高到更明确的 runtime helper，新增 `build_tool_plan_item_trace_write_action()`，并让 `build_tool_plan_item_service_effects()` 直接暴露 `trace_write_actions`；`chat_execution_service.py` 已切到通过这层更高层输入执行 trace append/SSE/persist，同时保留旧的 `trace_writes` 兼容字段，外部 SSE/trace/e2e 契约保持不变。focused 回归脚本已扩展到 71 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，next-action-execution helper）：继续先补 failing tests，再把 `next_action` 的 continue/return 执行输入收口到 `build_tool_plan_item_next_action_execution()`；`chat_execution_service.py` 已切到通过该 helper 统一消费 `continue_update` 与 `return_action`，不再直接同时依赖 `next_action` 和 `build_tool_plan_item_return_action()`，外部 SSE/trace/e2e 契约保持不变。focused 回归脚本已扩展到 73 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，service-effects-execution helper）：继续先补 failing tests，再把 service 最终消费的执行输入再聚合一层，新增 `build_tool_plan_item_service_effects_execution()`，统一承接 `trace_write_actions + next_action_execution`；`chat_execution_service.py` 已切到通过该 helper 获取单个 tool 的最终执行结果，进一步减少对多层 helper 的串联拼装。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 75 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，service-execution helper）：继续先补 failing tests，再把 `loop_execution_result` 到 service 最终消费输入的整条链收口到 `build_tool_plan_item_service_execution()`；`chat_execution_service.py` 已切到通过这个单入口 helper 直接获取单个 tool 的最终执行结果，不再显式串联 `build_tool_plan_item_service_effects()` 与 `build_tool_plan_item_service_effects_execution()`。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 77 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-14，continue-action helper）：继续先补 failing tests，再把 success path 的 `continue_update` 对称化为显式 `build_tool_plan_item_continue_action()`；`build_tool_plan_item_next_action_execution()` 现在在 continue/return 两侧都直接暴露动作对象，`chat_execution_service.py` 也已切到通过 `continue_action` 更新 `tool_observations` 与 `seq_cursor`，同时保留 `continue_update` 兼容字段。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 78 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，service-actions helper）：继续先补 failing tests，再把单个 tool 的 service 副作用执行顺序显式化为 `build_tool_plan_item_service_actions()`；`build_tool_plan_item_service_effects_execution()` 现会直接暴露 `service_actions`，`chat_execution_service.py` 已切到按统一 action 序列顺序消费 `trace_write / continue / complete_task / record_failure_event / emit_state / return`，同时保留既有 `trace_write_actions` 与 `next_action_execution` 兼容字段。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 80 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，service-action builders）：继续先补 failing tests，再把 `service_actions` 内部几类动作也对称化为显式 helper：`build_tool_plan_item_trace_write_service_action()`、`build_tool_plan_item_continue_service_action()`、`build_tool_plan_item_return_service_actions()`；`build_tool_plan_item_service_actions()` 现在不再手拼匿名 dict，而是消费这些 builder，同时保持 `chat_execution_service.py` 和外部 SSE/trace/e2e 契约不变。focused 回归脚本已扩展到 83 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，service-execution generator）：继续先补 failing tests，再新增 `execute_tool_plan_item_service_execution()`，把“retry loop 结束后再组装 `service_execution`”这一步也前推到 runtime；`chat_execution_service.py` 现已直接消费这个更高层 generator 返回的 `service_actions`，不再显式再调一次 `build_tool_plan_item_service_execution()`。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 85 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，service-actions executor）：继续先补 failing tests，再新增 `execute_tool_plan_item_service_actions()`，把 `service_actions` 的实际执行壳子也前推到 runtime；`chat_execution_service.py` 现已只负责把 runtime 产出的 `event` 包装成 SSE 字符串，并消费最终 `seq_cursor/should_return` 结果，不再手写 action kind 分发。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 87 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，registry injection seam）：继续先补 failing tests，再让 `run_tool()`、`execute_tool_spec()`、`build_tool_runtime_context()` 以及底层 registration helpers 支持可选 `registry` 注入；默认 mock registry 行为保持不变，但 runtime seam 已具备接入真实 registry 的前置扩展位。focused 回归脚本已扩展到 90 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，registry builder seam）：继续先补 failing tests，再新增 `get_default_tool_registry()` 与 `build_tool_registry()`，并让 `get_registered_tool_names()` 也支持可选 `registry`；默认 mock registry 行为保持不变，但现在已经有显式的默认快照、merge builder 和自定义枚举入口，便于后续真实 registry 分阶段接线。focused 回归脚本已扩展到 92 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，high-level registry threading）：继续先补 failing tests，再让 `execute_tool_plan_item_retry_loop()` 与 `execute_tool_plan_item_service_execution()` 也支持可选 `registry` 透传；这样 custom registry 不再只停留在 `run_tool()` 这一层，而是已经能够贯穿到高层 runtime 入口。focused 回归脚本已扩展到 94 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，registry loader seam）：继续先补 failing tests，再新增 `load_tool_registry()`，并让默认的 registry 枚举/解析路径实际经过这个 loader；这样 runtime 不只是“可注入 registry”，默认路径本身也已经收敛到显式 loader 边界，后面接真实 registry loader 时更容易渐进替换。focused 回归脚本已扩展到 96 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，pluggable registry loader）：继续先补 failing tests，再让 `load_tool_registry()` 接受可插拔 `loader`，并把 `registry_loader` 参数线程化到 `run_tool()`、`execute_tool_spec()` 与高层 runtime 入口；这样 runtime 现在已经不只是“可注入 registry dict”，而是可以接真正的 loader/provider 空壳。focused 回归脚本已扩展到 99 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，registry provider object）：继续先补 failing tests，再新增 `ToolRegistryProvider` / `StaticToolRegistryProvider`，并让 `load_tool_registry()` 接受可选 `provider`；同时把 `registry_provider` 参数线程化到 `get_registered_tool_names()`、`resolve/ensure registration`、`build_tool_runtime_context()`、`run_tool()`、`execute_tool_spec()` 以及高层 runtime 入口。默认 mock 行为与外部 SSE/trace/e2e 契约保持不变，但 runtime 现已能直接接 provider object，而不必先手拼 registry dict。focused 回归脚本已扩展到 102 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，default provider path）：继续先补 failing tests，再新增 `get_default_tool_registry_provider()`，并让默认 `load_tool_registry()` 路径也显式经过 provider object；这样 `StaticToolRegistryProvider` 不再只停留在测试 seam，默认生产路径本身也开始消费 provider object，同时保持外部 SSE/trace/e2e 契约不变。focused 回归脚本已扩展到 104 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端切片续推（2026-05-15，named default provider）：继续先补 failing tests，再新增具名 `DefaultToolRegistryProvider`，并让 `get_default_tool_registry_provider()` 返回该实现；默认 provider 不再只是匿名静态包装，而是具备清晰的生产语义，同时继续保持默认路径走 provider object、外部 SSE/trace/e2e 契约不变。focused 回归脚本已扩展到 106 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，configured provider stack）：继续先补 failing tests，再新增 `ConfiguredToolRegistryProvider` 与 `build_tool_registry_provider()`，把 `provider / loader / overrides` 组合逻辑收口成可复用 provider 组合层；同时 `load_tool_registry()` 改为统一委托给 builder，`chat_execution_service.py` 也开始在 tool loop 外显式预构建并复用 `tool_registry_provider`，不再每次隐式零散取默认 provider。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 110 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，configured provider resolution stack）：继续先补 failing tests，再新增 `get_configured_tool_registry_provider()` 与 `resolve_tool_registry_provider()`，把 `registry / registry_provider / registry_loader` 的优先级解析收口成统一 provider resolution stack；`get_registered_tool_names()` 与 `resolve_tool_registration()` 已切到复用这层入口，`chat_execution_service.py` 也改为显式通过 `get_configured_tool_registry_provider()` 预构建默认 provider。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 113 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，settings-backed registry overrides）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_OVERRIDES_JSON`、`build_tool_registry_overrides_from_settings()`，并让 `get_configured_tool_registry_provider()` 开始真实消费 settings 中的 tool metadata 覆盖；当前默认 configured provider 已不再只是 seam，而是具备正式的配置来源链。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 116 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，settings-backed tool disable path）：继续先补 failing tests，再新增 `build_tool_registry_settings_config()` 与 `get_disabled_tool_names_from_settings()`，让 `INSIGHT_AGENT_TOOL_REGISTRY_OVERRIDES_JSON` 除 metadata override 外还能通过 `enabled=false` 禁用已注册 tool；`ConfiguredToolRegistryProvider` 与 `build_tool_registry()` 现已原生支持 disabled tool 过滤，默认 configured provider 的配置来源链又前进了一层。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 119 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，settings-backed registry profiles）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROFILE`、`get_tool_registry_profile_name_from_settings()` 与 `build_tool_registry_profile_settings_config()`，让默认 configured provider 支持按内建 profile（如 `planning_only`）切换一组 tool 启停，并允许 JSON overrides 局部 re-enable。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 123 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-15，settings-backed extra tool aliases）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON` 与 `build_tool_registry_extra_tools_from_settings()`，让默认 configured provider 能基于已有 template tool 生成额外 alias registrations，并参与 profile / disable / override 组合链。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 126 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，settings-backed provider sources）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCE`、`INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCES_JSON`、`get_tool_registry_provider_source_name_from_settings()` 与 `build_tool_registry_provider_sources_from_settings()`，让默认 configured provider 能从 settings 选择命名基础 registry source，再叠加 profile / disable / override / extra alias 组合链。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 130 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，provider source adapters）：继续先补 failing tests，再把 `build_tool_registry_provider_sources_from_settings()` 从“source -> extra tools”升级成真正的 adapter 形态：命名 source 现在可声明 `provider/profile/disabled_tool_names/overrides/extra_tools`，并作为默认 configured provider 的基础 registry source。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 133 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，named providers + loader adapters）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROVIDERS_JSON`、`build_tool_registry_providers_from_settings()`、`resolve_named_tool_registry_loader()` 与 `build_tool_registry_provider_adapter()`，把 provider/source 组合链从“只能引用 default 或前置 source”推进成“可复用命名 provider + loader-backed adapter”形态。命名 source 现在既能引用命名 provider，也能直接声明 `loader/profile/disabled_tool_names/overrides/extra_tools`。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 137 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，provider factories）：继续先补 failing tests，再新增 `resolve_named_tool_registry_provider_factory()` 与 `build_profile_tool_registry_provider()`，把 provider/source adapter 再往前推进成代码级 `provider_factory` 入口。命名 provider 与命名 source 现在都能直接声明 `provider_factory`，复用内建 profile provider，并允许在其基础上继续 `enabled=true` 重开 tool、叠加 overrides 与 extra tools。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 141 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，named loaders）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_LOADERS_JSON`、`build_tool_registry_loaders_from_settings()` 与 `build_tool_registry_loader_adapter()`，让 settings-backed named loader 也成为一等入口。命名 provider 与命名 source 现在都能引用配置里的 loader 名，而不再只认内建 `default` loader。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 145 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，loader factories）：继续先补 failing tests，再新增 `resolve_named_tool_registry_loader_factory()` 与 `build_profile_tool_registry_loader()`，把 loader 这条链也补成代码级 `loader_factory` 入口。现在 named loader 可以直接声明 `loader_factory`，而且通过该 loader 构建的 named provider / source 也会保留内建 profile 的禁用集合，并允许继续 `enabled=true` 重开 tool、叠加 overrides 与 extra tools。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 149 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，settings-backed factory aliases）：继续先补 failing tests，再新增 `INSIGHT_AGENT_TOOL_REGISTRY_LOADER_FACTORIES_JSON`、`INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_FACTORIES_JSON`、`build_tool_registry_loader_factories_from_settings()` 与 `build_tool_registry_provider_factories_from_settings()`，把 `loader_factory` / `provider_factory` 也推进成 settings-backed 的命名别名入口。命名 loader / provider 现在既能直接引用内建 factory，也能引用配置里的 factory alias，并保留 profile 语义下传。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 155 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，cycle-safe file manifests）：继续先补 failing tests，再为 `build_tool_registry_from_file()` 增加 `_visited_files / _visited_dirs / _visited_sources` 防护，让 `registry_sources / registry_files / registry_dirs` 三条装配链在遇到自循环、重复文件、重复目录和重复 source 时统一“安全忽略已访问项”，不再递归炸栈。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 176 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，file-registry diagnostics artifacts）：继续先补 failing tests，再新增 `build_tool_registry_from_file_artifacts()`，把 file-backed registry 装配过程统一收口为 `registry + diagnostics`。当前已覆盖 `skipped/missing registry_sources`、`registry_files`、`registry_dirs` 三类观测结果，便于后续 trace / audit 接线复用；`build_tool_registry_from_file()` 继续只返回 registry，因此外部 SSE/trace/e2e 契约保持不变。focused 回归脚本已扩展到 178 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，diagnostics artifact chain）：继续先补 failing tests，再把 diagnostics seam 从底层 file helper 上提到高层 loader/provider/settings source 路径：新增 `build_tool_registry_loader_from_file_artifacts()`、`build_tool_registry_provider_from_file_artifacts()`、`build_tool_registry_loaders_from_settings_artifacts()`、`build_tool_registry_providers_from_settings_artifacts()`、`build_tool_registry_provider_sources_from_settings_artifacts()` 与 `get_configured_tool_registry_provider_artifacts()`。现有无 artifacts 入口继续保留原返回形状，但内部已委托新的 artifacts builders，因此外部 SSE/trace/e2e 契约保持不变。focused 回归脚本已扩展到 183 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，diagnostics runtime artifacts chain）：继续先补 failing tests，再新增 `build_tool_registry_diagnostics_summary()`、`build_tool_registry_diagnostics_runtime_artifacts()` 与 `build_configured_tool_registry_provider_runtime_artifacts()`，把 diagnostics 从“高层 artifacts 可取到”推进到“runtime 可直接消费的 summary / trace-candidate / audit-candidate”；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:271) 也已切到通过这个更高层入口拿 `provider`，但当前仍不额外对外发 SSE/trace 事件，因此外部契约保持不变。focused 回归脚本已扩展到 187 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，diagnostics audit wiring）：继续先补 failing tests，再新增 `build_tool_registry_diagnostics_audit_event()`，把 `diagnostics_runtime.audit_detail` 收口成内部 audit event 候选物；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:129) 同时抽出通用 `record_audit_event` 路径，并在 provider 预构建阶段把 `tool_registry_diagnostics` 写入内部 audit，但不额外对外发 SSE/trace 事件，因此外部契约保持不变。focused 回归脚本已扩展到 189 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，diagnostics audit action chain）：继续先补 failing tests，再新增 `build_tool_registry_diagnostics_audit_service_action()`、`build_configured_tool_registry_provider_runtime_service_actions()` 与 `execute_configured_tool_registry_provider_runtime_service_actions()`，把 `audit_event -> service_action -> apply` 这条内部 side-effect 链也收口到 runtime；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:274) 现在只负责调用这条链，不再手工拆 `audit_event` 字段。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 192 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-18，diagnostics internal trace action chain）：继续先补 failing tests，再新增 `build_tool_registry_diagnostics_trace_service_action()`，并扩展 `build_configured_tool_registry_provider_runtime_service_actions()` 与 `execute_configured_tool_registry_provider_runtime_service_actions()`，把 provider 预构建阶段的 diagnostics `trace_step/trace_event` 也收口成内部 `internal_trace_write -> persist` 动作链；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:288) 现在通过 runtime 动作链同时处理 internal trace 与 audit，但仍不额外对外发 SSE 事件，因此外部 SSE/trace/e2e 契约保持不变。focused 回归脚本已扩展到 193 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，provider preflight service execution chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_service_execution()` 与 `execute_configured_tool_registry_provider_service_execution()`，把 provider 预构建阶段的 `runtime_artifacts -> service_actions -> apply` 三段式收口成更高层的 `service_execution` 入口；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:288) 现在直接消费这层入口拿 `provider`，进一步减少了 service 侧手工胶水。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 195 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，provider preflight single-entry chain）：继续先补 failing tests，再新增 `execute_configured_tool_registry_provider_preflight()`，把 provider 预构建阶段进一步压成“单入口执行并返回 provider/result”的 helper；[chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py:288) 现在直接消费这一层单入口，不再手工串联 build/execute 两步。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 196 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，provider preflight structured result chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_preflight_result()` 与 `build_configured_tool_registry_provider_preflight_summary()`，把 provider preflight 的返回结果进一步结构化成统一 `result + summary` 形状；`execute_configured_tool_registry_provider_preflight()` 现已通过这组 helper 产出结构化结果，便于后续复用或观测扩展。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 198 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，provider preflight enriched summary chain）：继续先补 failing tests，再扩展 `build_configured_tool_registry_provider_preflight_summary()`，让 provider preflight 的 summary 不只包含 source 和 side-effect 计数，还统一携带 `tool_count`、`tool_names`、`service_action_count`、`service_action_kinds`、`diagnostics_total`、`skipped_total`、`missing_total` 等结构化指标；`execute_configured_tool_registry_provider_preflight()` 现已自动产出这组更实用的内部摘要，便于后续非 chat 复用和观测扩展。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已保持 198 条兼容测试全绿，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，provider preflight typed model chain）：继续先补 failing tests，再新增 `ConfiguredToolRegistryProviderPreflightSummaryModel`、`ConfiguredToolRegistryProviderPreflightResultModel` 以及对应的 `build_configured_tool_registry_provider_preflight_summary_model()` / `build_configured_tool_registry_provider_preflight_result_model()`，把 preflight 这层内部承载真正 typed 化，同时保留现有 dict outward 形状不变。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 200 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，diagnostics typed model chain）：继续先补 failing tests，再新增 `ToolRegistryDiagnosticsSummaryModel`、`ToolRegistryDiagnosticsRuntimeArtifactsModel` 以及对应的 `build_tool_registry_diagnostics_summary_model()` / `build_tool_registry_diagnostics_runtime_artifacts_model()`，把 diagnostics summary/runtime 这侧也补成 typed internal + dict outward 的一致分层。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 202 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，configured runtime artifacts typed model chain）：继续先补 failing tests，再新增 `ConfiguredToolRegistryProviderRuntimeArtifactsModel` 与 `build_configured_tool_registry_provider_runtime_artifacts_model()`，把 configured provider runtime artifacts 这层也补成 typed internal + dict outward 的一致分层，并让它直接持有 typed diagnostics runtime model。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 203 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，service execution typed model chain）：继续先补 failing tests，再新增 `ConfiguredToolRegistryProviderServiceExecutionModel`、`ConfiguredToolRegistryProviderServiceExecutionResultModel` 以及对应的 `build_configured_tool_registry_provider_service_execution_model()` / `build_configured_tool_registry_provider_service_execution_result_model()`，把 configured provider 的 service execution 这层也补成 typed internal + dict outward 的一致分层，并为旧 shape 的 `runtime_artifacts` 缺省值保留兼容兜底。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 205 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，runtime service actions typed model chain）：继续先补 failing tests，再新增 `ConfiguredToolRegistryProviderRuntimeServiceActionModel`、`ConfiguredToolRegistryProviderRuntimeServiceActionsModel`、`ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel`，并补齐 `build_tool_registry_diagnostics_trace_service_action_model()`、`build_tool_registry_diagnostics_audit_service_action_model()`、`build_configured_tool_registry_provider_runtime_service_actions_model()`、`build_configured_tool_registry_provider_runtime_service_actions_result_model()`，把 provider preflight 的 trace/audit service actions 这层也补成 typed internal + dict outward 的一致分层，同时清理了 README 中重复的 service execution 记录。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 209 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，typed preflight result chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()`、`build_configured_tool_registry_provider_preflight_result_model_from_models()` 与 `execute_configured_tool_registry_provider_preflight_model()`，把 `service_execution_result -> preflight_result` 这段内部链路也改成 typed model 直连，同时为旧的最小 `runtime_artifacts` shape 保留兼容合并。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 211 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，typed service_execution execution chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_service_execution_result_model_from_models()` 与 `execute_configured_tool_registry_provider_service_execution_model()`，把 `runtime_service_actions_result -> service_execution_result` 这段内部链路也改成 typed model 直连，并让 dict outward 的 `execute_configured_tool_registry_provider_service_execution()` 复用这条新链。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 213 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，typed runtime_service_actions execution chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_runtime_service_action_model_from_dict()`、`build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts()` 与 `execute_configured_tool_registry_provider_runtime_service_actions_model()`，把最底层 `runtime_service_actions` 执行器输入也改成 typed model 直连，并让 dict outward 的 `execute_configured_tool_registry_provider_runtime_service_actions()` / `execute_configured_tool_registry_provider_runtime_service_actions_result_model()` 退化为薄包装。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 215 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，shared hydration helper chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_runtime_artifacts_model_from_dict()` 与 `build_configured_tool_registry_provider_service_execution_model_from_dict()`，把 `runtime_artifacts/service_execution` 的共享 hydration 收口成统一 helper，并替换 `service_execution_result`、`preflight_result` 与 dict outward `execute` 路径中的重复手工组装。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 217 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，preflight_result shared bridge chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_preflight_result_model_from_dict()`，并让 `build_configured_tool_registry_provider_preflight_summary_model()` 与 `build_configured_tool_registry_provider_preflight_result_model()` 统一复用这层共享 bridge；同时补上缺省 `provider` 的兼容回退，保持旧最小 `preflight_result` shape 可用。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 218 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-19，typed preflight summary builder chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_preflight_summary_model_from_models()`，并让 `build_configured_tool_registry_provider_preflight_result_model_from_models()` 直接走真实 typed summary builder，不再先构造 placeholder summary 再覆盖。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本维持 218 条兼容测试全绿，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 后端整组续推（2026-05-20，shared preflight summary builder chain）：继续先补 failing tests，再新增 `build_configured_tool_registry_provider_preflight_summary_model_from_parts()`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()` 与 `build_configured_tool_registry_provider_preflight_summary_model_from_models()` 统一复用这层共享 builder，进一步收掉 preflight summary 的重复逻辑。外部 SSE/trace/e2e 契约保持不变，focused 回归脚本已扩展到 219 条兼容测试，最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `tool-runtime-productionization` 文档终稿同步（2026-05-14，design checkpoint）：已把 [design 文档](</Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-design.md>) 更新为当前真实架构说明，并将 [handoff 文档](</Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md>) 的建议改为“当前 helper 分层已到达阶段性合理停止点，除非新需求触发再继续抽象”。当前最新基线已推进到 focused 回归 `192` 条、`compileall` 通过、`bash scripts/test_ci_e2e_tooling.sh common` 通过
  - 新会话交接文档（2026-05-13）：已补充 [docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md)，汇总当前 `tool-runtime-productionization` 的真实状态、已验证基线、CI 风险教训、关键文件入口，以及下一步建议继续收口“单个 tool plan item retry loop 整体 helper”的开发方向，供后续会话直接接手
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

- e2e 收口已完成：主链路、导出稳定性、取消/超时、shared 知识库权限、artifact/export guard、frontend/backend scope 对称性与 common tooling 聚合回归均已跑通；当前可把重心切回开发主线。
- 下一阶段优先转向真实工具运行时、单机队列与并发治理、知识库治理深化；CI/e2e 保持“小步补洞、随改随回归”的维护节奏即可。

### 最新同步（2026-04-23）

- 任务中心表格头部计数文案（如 `17 / 17`）已移除，分页不再显示该类汇总计数。
- 任务中心“失败置顶”开关已移除，任务顺序仅由时间排序控制（最新/最早）。
- 任务中心筛选行与表格样式完成统一化优化：更轻量的筛选区、清晰表头层级、统一操作按钮视觉。
- 任务中心表格视觉继续收口：去除偏蓝底色，恢复中性底色；“重置筛选”按钮已对齐审计日志默认样式。

### 最新同步（2026-05-20）

- `tool-runtime-productionization` 本轮继续沿 typed internal 收口：`build_configured_tool_registry_provider_preflight_result_model()` 不再依赖顶层 dict `provider_source_name/provider/runtime_artifacts`，而是先 hydration `service_execution` 与计数结果再走 `from_models()`。
- `execute_configured_tool_registry_provider_preflight_model()` 已改为直接调用 typed `execute_configured_tool_registry_provider_service_execution_model()`，移除一层 `model -> dict -> model` 往返，同时保持外部 SSE / trace / e2e 契约不变。
- focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 `220` 条测试，并新增“`preflight_result` 从 `service_execution` 继承默认 provider/provider_source_name”兼容覆盖。

### 最新同步（2026-05-21）

- `tool-runtime-productionization` 本轮继续坚持“先补 failing test 再改实现”，新增 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 的最小 dict bridge 回归，锁定当顶层只保留计数时，`provider/provider_source_name/runtime_artifacts` 仍可从 `service_execution` 继承。
- `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 已改为只负责兼容归一化，并直接复用 `build_configured_tool_registry_provider_preflight_result_model()`；`ConfiguredToolRegistryProviderPreflightResult` 的 dict outward bridge 因而进一步收薄，同时保持外部 SSE / trace / e2e 契约不变。
- focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 `221` 条测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过。
- `tool-runtime-productionization` 本轮继续沿相邻 typed internal seam 收口：新增共享 helper `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，并让 `build_configured_tool_registry_provider_service_execution_result_model()` 与 `build_configured_tool_registry_provider_preflight_result_model()` 统一复用这层计数 hydration；同时补上 `service_execution_result` 在最小 `execution_result={}` 场景下的 `trace_write_count/audit_event_count -> 0` 兼容回退。focused 回归脚本已扩展到 `222` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续沿相邻 summary seam 收口：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()`，并让 `build_configured_tool_registry_provider_preflight_summary_model()` 直接复用这层 dict bridge；同时补上最小顶层 `preflight_result` 仍可从 `service_execution` 继承 `provider/provider_source_name/runtime_artifacts` 的 focused 兼容覆盖。focused 回归脚本已扩展到 `223` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_summary` / `preflight_result` 之间共享的 `service_execution` 归一化真正收成单点 helper：新增 `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`，并让两条 dict bridge 统一复用这层 provider/provider_source_name/runtime_artifacts merge 逻辑。focused 回归脚本已扩展到 `224` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续沿相邻 typed internal seam 收口：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，把 `preflight_result` 顶层计数 + 共享 `service_execution` 归一化进一步收成单点 helper，并让 `preflight_summary` / `preflight_result` 两条链统一复用。focused 回归脚本已扩展到 `225` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_summary` / `preflight_result` 共同依赖的 typed pair 收成单点 helper：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，统一返回 `service_execution_model + execution_result_model`，并让两条 dict bridge 直接复用；`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 也因此去掉了一层 `model -> dict -> model` 往返。focused 回归脚本已扩展到 `226` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续沿相邻 typed helper 细化复用：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，让 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 不再重复计算 `service_execution_model`，而是基于已归一化的 typed model 直接补齐 execution-result。focused 回归脚本已扩展到 `227` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把相邻 `service_execution_result` 的 typed 入口统一下来：新增 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，并让通用 `service_execution_result` 与 preflight 那条 `...from_service_execution_model()` 统一复用这层 helper。focused 回归脚本已扩展到 `228` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_result` 的 typed 入口也统一下来：新增 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，让 `build_configured_tool_registry_provider_preflight_result_model()` 不再自己手工拼装 typed execution-result，而是直接复用统一 helper。focused 回归脚本已扩展到 `229` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_summary` 的 typed 入口也补齐成对称 helper：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 直接复用这层 typed 入口，不再先展开共享 typed pair。focused 回归脚本已扩展到 `230` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_result` 的 dict outward bridge 也压到对称 typed 入口：`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现已直接复用 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，不再经过 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 这层共享 pair helper。focused 回归脚本已扩展到 `231` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_execution_models_from_dict()` 自身也压成更薄的组合壳：它现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，不再自己显式串联 `...preflight_service_execution_result_model_from_service_execution_model()`。focused 回归脚本已扩展到 `232` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_execution_models` 这层补齐对称 typed 入口：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 直接复用它，去掉 `service_execution_model` 的重复 hydration。focused 回归脚本已扩展到 `233` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_summary/result` 两个 typed 入口也统一到 execution-model pair helper：`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 现已直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，不再各自重复补 execution-result。focused 回归脚本已扩展到 `234` 条测试；最新校验同上通过。

### 最新同步（2026-05-25）

- `tool-runtime-productionization` 本轮继续把 `preflight_service_execution_result_model_from_dict()` 这层 outward bridge 也压到 shared pair helper：它现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，不再自己先 hydration `service_execution_model` 再补 execution-result。focused 回归脚本已扩展到 `235` 条测试；最新校验：`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_service_execution_result_model_from_service_execution_model()` 这层 typed wrapper 也统一到 shared pair helper：它现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，不再自己单独走通用 `service_execution_result` helper。focused 回归脚本已扩展到 `236` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_summary_model_from_service_execution_model()` 这层 typed 入口也统一到对称 result helper：它现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，不再自己展开 shared pair helper。focused 回归脚本已扩展到 `237` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_result_model_from_service_execution_model()` 这层 typed 入口也统一到对称 result helper：它现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，不再自己展开 shared pair helper。focused 回归脚本维持 `237` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_execution_models_from_service_execution_model()` 这层 shared pair helper 收回为更薄的组合壳：它现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，同时 `preflight_service_execution_result_model_from_service_execution_model()` 改为直接走通用 `service_execution_result` helper。focused 回归脚本已扩展到 `238` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 dict 侧也收成同样的组合壳：`preflight_service_execution_result_model_from_dict()` 现在会直接走通用 `service_execution_result` helper，而 `preflight_execution_models_from_dict()` 则直接复用 `preflight_service_execution_result_model_from_dict()`。focused 回归脚本维持 `238` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 dict outward 的 `preflight_summary/result` 两个入口也统一回 `preflight_execution_models_from_dict()`：它们现在都会直接消费这层组合壳返回的 typed pair，不再各自重复做 `service_execution` hydration。focused 回归脚本已扩展到 `239` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 的 payload normalization 单独收成 helper：新增 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，并让 `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_execution_models_from_dict()` 统一复用它，去掉 dict 侧重复的 `service_execution` hydration。focused 回归脚本已扩展到 `240` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 payload-normalization 之上的 typed pair seam 也收成单点：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()`，并让 `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_execution_models_from_dict()` 三条 dict 入口统一复用它。focused 回归脚本维持 `240` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_service_execution_model_from_dict()` 和 `preflight_service_execution_result_model_from_dict()` 这两个壳层再往外退一步：它们现在都直接从 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 取第一/第二个 model，不再自己单独触碰 payload-to-pair helper。focused 回归脚本维持 `240` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 的 dict/typed outward 入口一起收成 total-model 单点：新增 `build_configured_tool_registry_provider_preflight_models_from_dict()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()`，统一产出 `service_execution_model + execution_result_model + summary_model + result_model`。
- `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_summary_model_from_dict()`、`preflight_result_model_from_dict()` 以及 typed 侧的 `preflight_summary/result_model_from_service_execution_model()` 现在都直接从这两层 total-model helper 取各自结果，不再平行展开 pair/result 链路。focused 回归脚本已扩展到 `244` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 的 pair-to-total 总装也收成单点：新增 `build_configured_tool_registry_provider_preflight_models_from_models()`，统一负责 `service_execution_model + execution_result_model -> summary_model + result_model`。
- `preflight_execution_models_from_dict()` 现已退回为 total-model 兼容壳，直接从 `build_configured_tool_registry_provider_preflight_models_from_dict()` 取前两个 model；`preflight_result_model_from_models()` 也改为直接复用 `preflight_models_from_models()`。focused 回归脚本已扩展到 `246` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 dict 侧的 `payload -> total models` 也收成单点：新增 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()`，统一负责 normalized payload 直接派生 `service_execution_model + execution_result_model + summary_model + result_model`。
- `preflight_models_from_dict()` 现已直接复用这层 payload-total helper；typed 侧 `preflight_execution_models_from_service_execution_model()` 也退回为 total-model 兼容壳，直接从 `preflight_models_from_service_execution_model()` 取前两个 model。focused 回归脚本已扩展到 `247` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 payload 侧 pair helper 也彻底退成 total-model 兼容壳：`preflight_execution_models_from_service_execution_payload()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 取前两个 model。
- 同时 `preflight_models_from_service_execution_payload()` 自己改为直接完成 `service_execution_model` hydration、`execution_result_model` 派生和 total-model 组装，不再经过 payload pair helper。focused 回归脚本已扩展到 `249` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 typed 侧的 `preflight_service_execution_result_model_from_service_execution_model()` 也退成 total-model 兼容壳：它现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 取第二个 model。
- 同时 `preflight_models_from_service_execution_model()` 自己改为直接走通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()` 完成 execution-result 派生，避免再绕回 typed preflight result helper。focused 回归脚本维持 `249` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `summary` 这条基础 seam 也退回 total-model 兼容壳：`preflight_summary_model_from_models()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_models()` 取第三个 model，`preflight_summary_model_from_result_model()` 也直接返回已有 `result.summary`。
- 同时 `preflight_models_from_models()` 自己改为直接走 `preflight_summary_model_from_parts()` 完成 summary 组装，再组合 result model，不再反向依赖 `summary_model_from_models()`。focused 回归脚本已扩展到 `251` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把高层 raw-input / execute 入口也退回 total-model helper：新增 `build_configured_tool_registry_provider_preflight_models()` 与 `execute_configured_tool_registry_provider_preflight_models()`。
- `build_preflight_result_model()` 和 `execute_preflight_model()` 现在都会直接从这两层 helper 取第四个 `result_model`，不再各自重复做 `service_execution_model` hydration 或 `execution_result_model` 执行后组装。focused 回归脚本已扩展到 `253` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把最外层 outward dict seam 也收成单点：新增 `build_configured_tool_registry_provider_preflight_dicts_from_models()`、`build_configured_tool_registry_provider_preflight_dicts()` 与 `execute_configured_tool_registry_provider_preflight_dicts()`。
- `build_preflight_summary()`、`build_preflight_result()` 与 `execute_preflight()` 现在都退回为只取 summary/result dict 的兼容壳，不再各自重复做 typed hydration、result 组装或执行后 dict 转换。focused 回归脚本已扩展到 `256` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把高层 outward `models + dicts` 也统一到 total-output seam：新增 `build_configured_tool_registry_provider_preflight_outputs_from_models()`、`build_configured_tool_registry_provider_preflight_outputs()` 与 `execute_configured_tool_registry_provider_preflight_outputs()`。
- `build_preflight_models()`、`build_preflight_result_model()`、`build_preflight_result()`、`execute_preflight_models()`、`execute_preflight_model()` 与 `execute_preflight()` 现在都退回为从这层 `outputs` helper 取对应 model/dict 的兼容壳；focused 回归脚本已扩展到 `257` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把单参 `preflight_result` 的 dict 兼容链也统一到 total-output seam：新增 `build_configured_tool_registry_provider_preflight_outputs_from_dict()`。
- `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_models_from_dict()`、`preflight_summary_model_from_dict()`、`preflight_result_model_from_dict()`、`preflight_dicts()` 与 `preflight_summary()` 现在都退回为从这层 `outputs_from_dict()` 取对应结果的兼容壳；focused 回归脚本维持 `257` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution_payload + preflight_result` 这条 payload typed 链也统一到 total-output seam。
- `preflight_execution_models_from_service_execution_payload()` 与 `preflight_models_from_service_execution_payload()` 现在都退回为从 `build_configured_tool_registry_provider_preflight_outputs()` 取对应 typed 结果的兼容壳，不再各自重复做 payload -> typed hydration / summary/result 组装；focused 回归脚本维持 `257` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution_payload + execution_result` 这条 payload total-output seam 本身也明确收成单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()`。
- `build_preflight_outputs()` 现在退回为从这层 payload helper 取结果的兼容壳，而 `preflight_execution_models_from_service_execution_payload()` 与 `preflight_models_from_service_execution_payload()` 也一起锁到这层新 helper；focused 回归脚本已扩展到 `258` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 typed `service_execution_model + preflight_result` 这条链也统一到 total-output seam。
- `preflight_service_execution_result_model_from_service_execution_model()`、`preflight_execution_models_from_service_execution_model()` 与 `preflight_models_from_service_execution_model()` 现在都退回为从 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 取对应 typed 结果的兼容壳；focused 回归脚本已扩展到 `259` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把单参 dict total-output 总出口也并回更高层 `build_configured_tool_registry_provider_preflight_outputs()`。
- `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 现在退回为从 `build_configured_tool_registry_provider_preflight_outputs(service_execution, execution_result)` 取总装结果的兼容壳；focused 回归脚本已扩展到 `261` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution_payload + execution_result` 这条 total-output 入口也并回高层 `build_configured_tool_registry_provider_preflight_outputs()`。
- `build_configured_tool_registry_provider_preflight_outputs()` 现在自己承担 `service_execution` hydration，再直接复用 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`；`build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 则退回为从高层 `outputs()` 取总装结果的兼容壳；focused 回归脚本已扩展到 `263` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute 侧也补成对称的 typed total-output seam：新增 `execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`。
- `execute_configured_tool_registry_provider_preflight_outputs()` 现在退回为只负责构造 `service_execution_model`，再直接复用这层 typed execute helper；focused 回归脚本已扩展到 `265` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把最外层 summary/result wrapper 这批 outward 入口退回到最近邻 helper。
- `build_preflight_summary()` 现在直接复用 `build_preflight_dicts()`；`build_preflight_summary_model_from_dict()` / `...from_service_execution_model()` 与 `build_preflight_result_model()` / `...from_dict()` / `...from_service_execution_model()` 现在都退回为从对应 `models()` helper 取结果；`build_preflight_result()`、`execute_preflight_model()`、`execute_preflight()` 也分别退回为复用 `result_model()`、`execute_preflight_models()`、`execute_preflight_dicts()` 的兼容壳；focused 回归脚本维持 `265` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution/execution_models` 这组 wrapper 也退回到最近邻 helper。
- `build_preflight_service_execution_model_from_dict()` 与 `build_preflight_service_execution_result_model_from_dict()` 现在直接复用 `build_preflight_execution_models_from_dict()`；typed `...service_execution_result_model_from_service_execution_model()` 退回为复用 `...execution_models_from_service_execution_model()`；而 `execution_models_from_service_execution_payload()` / `...from_service_execution_model()` 也都退回为从对应 `models()` helper 取前两个结果。进一步地，`build_preflight_models()`、`...models_from_service_execution_payload()`、`...models_from_dict()` 与 typed `...models_from_service_execution_model()` 现在也都直接走 `models_from_models()` 主链，不再先经过 `outputs()`；focused 回归脚本已扩展到 `267` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `dicts` 这一层 outward wrapper 也并回 `models` 主链。
- `build_preflight_dicts_from_models()` 现在直接复用 `build_preflight_models_from_models()` 再做 `to_dict()`；`build_preflight_dicts()` 现在直接复用 `build_preflight_models_from_dict()`；`execute_preflight_dicts()` 现在直接复用 `execute_preflight_models()` 后再统一走 `dicts_from_models()`，不再平行依赖更深的 `outputs()` seam；focused 回归脚本已扩展到 `270` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `outputs` 这一组 build/execute wrapper 也退回到 `models + dict projection` 主链。
- build 侧 `build_preflight_outputs()` / `...from_service_execution_payload()` / `...from_service_execution_model()` / `...from_dict()` 现在都先走各自最近邻的 `models` helper，再统一通过共享的 resolved-model output assembler 产出 dict；execute 侧补齐了对称的 `execute_preflight_models_from_service_execution_model()`，并让 `execute_preflight_outputs()` / `...outputs_from_service_execution_model()` 也都回到 `execute_models` 主链；focused 回归脚本已扩展到 `272` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution` 内核层的两处 model/dict 往返拿掉。
- `build_service_execution_model()` 现在直接复用新的 typed `runtime_artifacts_model -> runtime_service_actions_model` helper，不再先 `runtime_artifacts.to_dict()`；`execute_service_execution_model()` 现在直接把 `service_execution.service_actions` 组装成 typed actions model 再执行，不再先 `[action.to_dict()]` 再绕一层 dict result helper；focused 回归脚本已扩展到 `274` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮开始把相邻的 `service_execution result + dict` 这一层也补成 `outputs` 单点。
- 新增 `build_service_execution_outputs()` / `...outputs_from_service_execution_model()` / `...outputs_from_models()` 与 `execute_service_execution_outputs()` / `...outputs_from_service_execution_model()`；`build_service_execution_result_model()`、`...result_model_from_service_execution_model()`、`execute_service_execution()` 现在都退回为从这条 `outputs` seam 取 typed model 或 dict；focused 回归脚本已扩展到 `277` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把更内层的 `runtime_service_actions` build/execute wrapper 也补成 `outputs` 单点。
- 新增 `build_runtime_service_actions_outputs()` / `...outputs_from_runtime_artifacts_model()` / `...outputs_from_models()` 与 `execute_runtime_service_actions_outputs()` / `...outputs_from_models()`；`build_runtime_service_actions()`、`build_runtime_service_actions_model()`、`execute_runtime_service_actions()`、`execute_runtime_service_actions_result_model()` 现在都退回为从这条 `outputs` seam 取 typed model 或 dict，`build_service_execution_model()` 与 `execute_service_execution_model()` 也同步退回到这层最近邻 helper。focused 回归脚本已扩展到 `284` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `runtime_service_actions` 的 typed-from-artifacts 和 dict-from-dicts 两条入口也并回到最近邻 `outputs` seam。
- 新增 `build_runtime_service_actions_outputs_from_dicts()`；`build_runtime_service_actions_model_from_runtime_artifacts_model()`、`build_runtime_service_actions_model_from_dicts()`、`build_service_execution_model_from_dict()`、`execute_runtime_service_actions_outputs()` 现在都退回为从 `...outputs_from_runtime_artifacts_model()` / `...outputs_from_dicts()` 取 typed model 或 dict，不再平行保留额外的组装路径。focused 回归脚本已扩展到 `288` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `runtime_service_actions result` 也补成了对称 `outputs` seam。
- 新增 `build_runtime_service_actions_result_outputs_from_models()` 与 `...outputs_from_dict()`；`build_runtime_service_actions_result_model_from_dict()` 现在退回为从这层 `result outputs` seam 取 typed result model，而 `build_service_execution_outputs_from_service_execution_model()` 也同步退回为先走这层 seam，再统一组装 `service_execution` result。focused 回归脚本已扩展到 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 这边两条 build-side `service_execution_result` wrapper 也并回了 `service_execution outputs` 主链。
- `build_preflight_service_execution_result_model_from_dict()` 现在退回为先走 `build_preflight_service_execution_payload_from_dict()`，再直接复用 `build_service_execution_outputs()`；`build_preflight_service_execution_result_model_from_service_execution_model()` 则退回为直接复用 `build_service_execution_outputs_from_service_execution_model()`。focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `preflight models / execution_models` 三条入口一起并回 `service_execution outputs` 主链。
- `build_preflight_execution_models_from_dict()` / `...from_service_execution_payload()` / `...from_service_execution_model()` 现在都会先复用 `service_execution outputs` 产出 typed `execution_result_model`，再只保留一层最薄的 `service_execution_model` hydration 或透传；`build_preflight_models_from_dict()` / `...from_service_execution_payload()` / `...from_service_execution_model()` 也统一退回为“单次 `service_execution_model` hydration + `service_execution outputs` + `preflight_models_from_models()`”的总装路径。focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把最外层 raw `service_execution + execution_result` build wrapper 也退回到了 payload seam。
- `build_preflight_models()`、`build_preflight_outputs()` 和 `build_preflight_result_model()` 现在都直接复用 `...from_service_execution_payload()` 这一层，不再自己在 raw 输入层重复选路或做平行总装；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build/execute 的 dict outward wrapper 也统一退回 `outputs` seam。
- `build_preflight_dicts()`、`build_preflight_result()`、`execute_preflight_dicts()`、`execute_preflight()` 现在都直接从对应 `outputs` helper 取 summary/result dict，不再先走 `models` 再做二次 dict 投影；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把剩余的 preflight model outward wrapper 也统一退回 `outputs` seam。
- `build_preflight_summary_model_from_dict()`、`build_preflight_result_model_from_dict()`、`build_preflight_summary_model_from_service_execution_model()`、`build_preflight_result_model_from_service_execution_model()` 与 `execute_preflight_model()` 现在都直接从对应 `outputs` helper 取 typed model，不再平行复用旧的 `models` / `execute_models` seam；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight outputs` 这组 wrapper 本身也往最近邻 seam 收了一层。
- `build_preflight_outputs()` 现在直接构造 typed `service_execution_model` 后复用 `build_preflight_outputs_from_service_execution_model()`；`build_preflight_outputs_from_service_execution_payload()` 与 `build_preflight_outputs_from_dict()` 都退回为只负责参数兼容再复用高层 `outputs()`；`build_preflight_outputs_from_service_execution_model()` 与 `execute_preflight_outputs_from_service_execution_model()` 则统一退回为从 `build_preflight_outputs_from_models()` 取总装结果，`execute_preflight_outputs()` 也直接复用 typed execute helper；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight ...from_models()` 这组 outward wrapper 也并回 `outputs_from_models` 主链。
- `build_preflight_dicts_from_models()`、`build_preflight_summary_model_from_models()`、`build_preflight_result_model_from_models()` 现在都直接从 `build_preflight_outputs_from_models()` 取 dict / typed model；`build_preflight_result_model()` 也直接复用 `build_preflight_outputs_from_service_execution_payload()` 取 result model，不再平行依赖 `models_from_models` / `models_from_service_execution_payload`；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight models_from_dict / ...payload / ...service_execution_model` 三条 typed 总装入口也统一并回 `preflight_execution_models_*` 主链。
- `build_preflight_models_from_dict()`、`build_preflight_models_from_service_execution_payload()`、`build_preflight_models_from_service_execution_model()` 现在都先复用对应的 `preflight_execution_models_*` helper，再统一进入 `build_preflight_models_from_models()`，不再各自重复打一遍 `service_execution outputs`；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 dict/typed `service_execution_model/result_model` wrapper 也统一并回 `preflight_execution_models_*` 主链。
- `build_preflight_service_execution_model_from_dict()`、`build_preflight_service_execution_result_model_from_dict()`、`build_preflight_service_execution_result_model_from_service_execution_model()`，以及 `build_preflight_execution_models_from_dict()` 现在都直接复用 `preflight_execution_models_from_service_execution_payload()` / `...from_service_execution_model()`，dict path 的 typed pair 装配边界进一步收敛到单点 payload seam；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight_execution_models_from_service_execution_payload()` 也退回到 typed helper。
- `build_preflight_execution_models_from_service_execution_payload()` 现在先构造 typed `service_execution_model`，再直接复用 `build_preflight_execution_models_from_service_execution_model()`，这样 dict/payload 两层都会统一先落到 typed `service_execution_model` 再派生 `execution_result_model`；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 typed `preflight_execution_models_from_service_execution_model()` 也退回到通用 `service_execution_result_model` helper。
- `build_preflight_execution_models_from_service_execution_model()` 和 `build_preflight_service_execution_result_model_from_service_execution_model()` 现在都直接复用 `build_service_execution_result_model_from_service_execution_model()`，typed path 不再平行保留一条单独的 `service_execution_outputs_from_service_execution_model()` 委托链；focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 剩余的 dict/payload/typed wrapper 成片并回 `outputs_from_*` seam。
- `build_preflight_service_execution_model_from_dict()`、`build_preflight_service_execution_result_model_from_dict()`、`build_preflight_execution_models_from_dict()`、`build_preflight_models_from_dict()` 现在都直接从 `build_preflight_outputs_from_dict()` 取对应 typed 结果；`...from_service_execution_payload()` 与 `...from_service_execution_model()` 两组 `execution_models/models/result_model` wrapper 也同步退回为从最近邻 `outputs_from_service_execution_payload()` / `...outputs_from_service_execution_model()` 取值，不再分散依赖旧的 `execution_models` / generic typed seam。focused 回归脚本维持 `292` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute-side 的 `preflight models` 平行总装链也并回 `execute_preflight_outputs*` seam。
- `execute_preflight_models_from_service_execution_model()` 现在直接从 `execute_preflight_outputs_from_service_execution_model()` 取前四个 typed 结果，`execute_preflight_models()` 也同步退回为直接复用 `execute_preflight_outputs()`；execute 侧不再重复做一遍 `execute_service_execution_model() + preflight_models_from_models()` 的平行总装。focused 回归脚本现已扩展到 `294` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution` execute 侧也补成了和 build 侧对称的共享总装 seam。
- `execute_service_execution_outputs_from_service_execution_model()` 现在先执行 typed `runtime_service_actions_outputs_from_models()`，再统一复用 `build_service_execution_outputs_from_models()` 组装 typed result+dict；`execute_service_execution_model()` 则同步退回为直接从这层 `outputs_from_service_execution_model()` 取 result model。focused 回归脚本现已扩展到 `296` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute-side 的 `preflight outputs_from_service_execution_model()` 也并回 `service_execution outputs` seam。
- `execute_preflight_outputs_from_service_execution_model()` 现在直接复用 `execute_service_execution_outputs_from_service_execution_model()` 取 typed `execution_result_model`，不再平行直连 `execute_service_execution_model()`；这条 execute-side preflight 总装链现在和 build-side `preflight_outputs_from_service_execution_model()` 的最近邻 seam 也更对称了。focused 回归脚本维持 `296` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把三条还直接切 `outputs()[0]` 的 `runtime_service_actions / service_execution` wrapper 一起退回到最近邻 `*_model_*` helper。
- `build_service_execution_model_from_dict()` 现在直接复用 `build_runtime_service_actions_model_from_dicts()`，`build_service_execution_model()` 直接复用 `build_runtime_service_actions_model_from_runtime_artifacts_model()`，`execute_runtime_service_actions_outputs()` 也直接复用 `build_runtime_service_actions_model_from_dicts()`；这三条链不再自己切 `outputs_*()[0]` 拿 model。focused 回归脚本现已扩展到 `297` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把一条 raw build 链和两条 `service_execution` result 链一起退回到了最近邻 typed model helper。
- `build_runtime_service_actions_outputs()` 现在先把 raw `runtime_artifacts` hydrate 成 typed `runtime_artifacts_model`，再统一复用 `build_runtime_service_actions_outputs_from_runtime_artifacts_model()`；`build_service_execution_outputs_from_service_execution_model()` 改为直接复用 `build_runtime_service_actions_result_model_from_dict()`，`execute_service_execution_outputs_from_service_execution_model()` 改为直接复用 `execute_runtime_service_actions_model()`。这样三条链都不再为“只需要 typed model”绕经更外层 `outputs` helper。focused 回归脚本现已扩展到 `299` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `*_result_model` 这组 wrapper 成片退回到 typed result seam。
- `build_runtime_service_actions_result_model_from_dict()` 现在直接复用 `build_runtime_service_actions_result_model()`；`build_service_execution_result_model()` 改为先 hydrate typed `service_execution_model` 再复用 `build_service_execution_result_model_from_service_execution_model()`，后者直接组合 `build_runtime_service_actions_result_model_from_dict()` + `build_service_execution_result_model_from_models()`；`execute_service_execution_model()` 也直接组合 `execute_runtime_service_actions_model()` + `build_service_execution_result_model_from_models()`。这样这组 wrapper 不再为了只拿 model 先绕 `outputs` 再拆回来。focused 回归脚本维持 `299` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 raw dict `outputs` wrapper 这一批也并回了最近邻 `result_model` seam。
- `build_runtime_service_actions_result_outputs_from_dict()` 现在直接复用 `build_runtime_service_actions_result_model_from_dict()`，`execute_runtime_service_actions()` 直接复用 `execute_runtime_service_actions_result_model()`；`build_service_execution_outputs()` 直接复用 `build_service_execution_result_model()`，`execute_service_execution()` 与 `execute_service_execution_outputs()` 则都直接复用 `execute_service_execution_model()`。这样这批 raw wrapper 现在只负责 typed hydration 和 `to_dict()`，不再平行保留额外总装链。focused 回归脚本现已扩展到 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 最外层 raw wrapper 也并回了 `summary/result model` seam。
- `build_preflight_summary()` 现在直接复用 `build_preflight_summary_model_from_dict()`，`build_preflight_result()` 直接复用 `build_preflight_result_model()`；`build_preflight_dicts()` 改为直接从 `build_preflight_result_model_from_dict()` 取 `summary/result` dict，`execute_preflight()` 与 `execute_preflight_dicts()` 则都直接复用 `execute_preflight_model()`。这样这批最外层入口现在只负责 `to_dict()` 投影，不再平行保留额外 `outputs` 总装链。focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `preflight` 剩下的 typed `summary/result model` wrapper 成片并回了 `result_model/models` 主链。
- `build_preflight_summary_model_from_dict()`、`...from_service_execution_model()`、`...from_models()` 现在都直接复用对应 `result_model` helper 再取 `summary`；`build_preflight_result_model_from_service_execution_model()` 改为先复用通用 `build_service_execution_result_model_from_service_execution_model()`，再统一进入 `build_preflight_result_model_from_models()`；`build_preflight_result_model_from_models()` 与 `...from_dict()` 也分别退回到 `build_preflight_models_from_models()` 和 `build_preflight_result_model_from_service_execution_model()`。这样这批 typed wrapper 不再为了只拿 `summary/result model` 绕经 `outputs` seam，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute-side 的 `preflight models/model` wrapper 成片并回了 `service_execution outputs + models_from_models` 主链。
- `execute_preflight_models_from_service_execution_model()` 现在先复用 `execute_service_execution_outputs_from_service_execution_model()` 取 typed `execution_result_model`，再统一进入 `build_preflight_models_from_models()`；`execute_preflight_outputs_from_service_execution_model()` 改为从这条 `models` helper 取 resolved models 再做 dict 投影；`execute_preflight_models()` 与 `execute_preflight_model()` 也分别退回到 `...models_from_service_execution_model()` 和 `...models()`。这样 execute 侧不再继续从 `outputs` seam 反向拆 typed 结果，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `preflight service_execution_model/result_model/execution_models/models` wrapper 成片收回到了更直接的 typed seam。
- `build_preflight_service_execution_model_from_dict()` 现在先复用 `build_preflight_service_execution_payload_from_dict()`；`build_preflight_service_execution_result_model_from_dict()` 与 typed `...from_service_execution_model()` 统一退回到通用 `build_service_execution_result_model_from_service_execution_model()`；`build_preflight_execution_models_from_dict()/...from_service_execution_payload()/...from_service_execution_model()` 与三条 `build_preflight_models_from_*()` 也都统一改成“先拿 typed execution-model pair，再进入 `build_preflight_models_from_models()`”。这样 build-side `preflight` 这段不再继续从 `outputs` seam 反向拆 typed 结果，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `preflight summary/result/dicts` wrapper 成片收回到了 `preflight_models_*` 主链。
- `build_preflight_summary_model_from_dict()/...from_service_execution_model()/...from_models()` 现在都直接从对应 `preflight_models_*` helper 取第三个 `summary_model`；`build_preflight_result_model()`、`...result_model_from_service_execution_model()`、`...result_model_from_dict()` 与 `build_preflight_dicts()` 也都统一改成从 `preflight_models_*` helper 取第四个 `result_model` 或最后两个 dict。这样 build-side `preflight` 这段的 outward wrapper 不再平行绕 `outputs` 或 `service_execution_result` seam，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `preflight outputs*` wrapper 成片收回到了 `preflight_models_* + outputs_from_resolved_models()` 主链。
- `build_preflight_outputs()`、`...outputs_from_service_execution_payload()`、`...outputs_from_service_execution_model()` 与 `...outputs_from_dict()` 现在都先复用对应 `preflight_models_*` helper 拿到 typed `service_execution/execution_result/summary/result`，再统一进入 `build_preflight_outputs_from_resolved_models()` 做 dict 投影。这样 build-side `outputs*` 真正只负责 outward dict 组装，不再平行绕 `service_execution_outputs` 或更高层 `outputs` seam，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute-side 的 `preflight outputs/dicts` wrapper 成片收回到了 `execute_preflight_models*` 主链。
- `execute_preflight_outputs()` 现在先复用 `execute_preflight_models()` 拿到 typed `service_execution/execution_result/summary/result`，再统一进入 `build_preflight_outputs_from_resolved_models()`；`execute_preflight_dicts()` 也改成直接从 `execute_preflight_models()` 取 `summary_model/result_model` 再做 `to_dict()`。这样 execute-side 的 outward wrapper 不再平行绕 `outputs_from_service_execution_model()` 或 `execute_preflight_model()`，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 execute-side 的 `service_execution/preflight` typed wrapper 再拉直一层。
- `execute_service_execution_outputs_from_service_execution_model()` 现在直接复用 `execute_service_execution_model()`；`execute_preflight_models_from_service_execution_model()` 也直接复用同一条 typed `service_execution_result_model` seam，再统一进入 `build_preflight_models_from_models()`。这样 execute 侧不再为拿 typed `execution_result_model` 中间绕一层 `service_execution outputs`，focused 回归脚本维持 `302` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `runtime_service_actions` 的 raw build/execute wrapper 退回到更直接的 `model/result_model` seam。
- `build_runtime_service_actions()` 现在直接复用 `build_runtime_service_actions_model()`；`build_runtime_service_actions_model()` 统一先 hydrate typed `runtime_artifacts_model` 再进入 `...model_from_runtime_artifacts_model()`；`build_runtime_service_actions_outputs_from_runtime_artifacts_model()` 与 `...outputs_from_dicts()` 也同步退回成“model helper + to_dict()”的 outward 壳；`execute_runtime_service_actions_outputs()` 则直接复用 `execute_runtime_service_actions_result_model()`，而 `execute_runtime_service_actions_model()` 直接复用 `...result_model_from_models()`。这样这组 wrapper 不再为拿 typed model 或 result 额外绕 `outputs`，focused 回归脚本现在是 `303` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 的 `service_execution/preflight` 最近邻 helper 再拉直一层。
- `build_service_execution_outputs_from_service_execution_model()` 现在直接复用 `build_service_execution_result_model_from_service_execution_model()`；`build_preflight_result_model_from_service_execution_model()` 也退回为“先拿 typed `service_execution_result_model`，再进入 `build_preflight_result_model_from_models()`”；`build_preflight_summary_model_from_service_execution_model()` 则直接复用 `build_preflight_result_model_from_service_execution_model()` 再取 `summary`。这样 build 侧不再为拿 typed result 中间绕 `models` 或更低一层 runtime-result seam，focused 回归脚本维持 `303` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build-side 两参 `preflight` raw wrapper 成片收回到了单参 `preflight_result dict` seam。
- 新增 `build_configured_tool_registry_provider_preflight_result_payload()` 之后，`build_preflight_models()`、`build_preflight_outputs()`、`build_preflight_outputs_from_service_execution_payload()`、`build_preflight_result_model()` 与 `build_preflight_result()` 现在都统一先合成 outward `preflight_result` payload，再直接复用对应的 `...from_dict()` helper。这样 build-side raw 入口不再平行保留一组“`service_execution + execution_result` 自己再拆 typed result”的链路，focused 回归脚本维持 `303` 条测试；`backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 继续通过。
- `tool-runtime-productionization` 本轮继续把 build/execute 最外层 dict outward wrapper 收回到了 `dicts` / `outputs_from_dict` seam。
- `build_preflight_summary()` 现在直接复用 `build_preflight_dicts()` 取 summary dict，`build_preflight_result()` 也直接复用同一层取 result dict；同时 `build_preflight_dicts()` 本身改成直接从 `build_preflight_outputs_from_dict()` 取最后两个 dict。execute 侧的 `execute_preflight_dicts()` 现在直接复用 `execute_preflight_outputs()`，而 `execute_preflight()` 直接复用 `execute_preflight_dicts()`。这样最外层 dict outward wrapper 不再各自平行绕 `model/models` seam，focused 回归脚本维持 `303` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution` 最外层 raw wrapper 收回到了 `outputs_from_service_execution_model()` / `outputs()` seam。
- `build_service_execution_outputs()` 现在直接复用 `build_service_execution_outputs_from_service_execution_model()`；`execute_service_execution_outputs()` 也直接复用 `execute_service_execution_outputs_from_service_execution_model()`；而 `execute_service_execution()` 则直接复用 `execute_service_execution_outputs()` 取最终 dict。这样 `service_execution` build/execute 两侧的 raw outward wrapper 不再各自平行做一次 typed hydration 或 result `to_dict()`，focused 回归脚本维持 `303` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 `service_execution_result` 与 `preflight_service_execution_result` 这批 wrapper 收回到了最近邻 `service_execution outputs` seam。
- `build_service_execution_result_model()`、`...result_model_from_service_execution_model()` 与 `execute_service_execution_model()` 现在都统一退回为从各自最近邻 `service_execution outputs` helper 取 typed result；同时 `build_preflight_service_execution_result_model_from_dict()` 与 `...from_service_execution_model()` 也统一复用同一条 `service_execution outputs` 主链。这样这批 helper 不再平行保留“result_model 自己组装一遍、outputs 再组装一遍”的重复入口，focused 回归脚本维持 `303` 条测试；最新校验同上通过。
- `tool-runtime-productionization` 本轮继续把 build/execute 最外层 `preflight` dict outward wrapper 收回到了 `summary_model/result_model` seam。
- `build_preflight_summary()` 现在直接复用 `build_preflight_summary_model_from_dict()` 并做 `to_dict()`；`build_preflight_dicts()` 改成直接从 `build_preflight_result_model_from_dict()` 取 `summary/result` dict；`build_preflight_result()` 直接复用 `build_preflight_result_model()`。execute 侧的 `execute_preflight_dicts()` 与 `execute_preflight()` 也统一直接复用 `execute_preflight_model()`。这样这批最外层 dict wrapper 不再平行绕 `dicts/outputs` seam，focused 回归脚本维持 `303` 条测试；最新校验同上通过。
- CI / e2e 修复（2026-05-28）：前端 workflow 的 Playwright 安装阶段已补浏览器缓存，并去掉最重的 `--with-deps` 三浏览器安装；同时把 `frontend-e2e` job 超时从 `35` 分钟放宽到 `45` 分钟，降低冷启动浏览器下载把整条 e2e job 拖死的概率。对应 workflow guard 已补红灯并转绿，`bash scripts/test_ci_e2e_tooling.sh common` 继续通过。
- CI / e2e 跟进修复（2026-05-28）：在上面的缓存优化之后，前端 smoke matrix 仍暴露出 Playwright 系统依赖缺失问题，因此 workflow 进一步调整为“恢复 `~/.cache/ms-playwright` 缓存 + 单独执行 `npx playwright install-deps chromium firefox webkit` + 再执行 `npx playwright install chromium firefox webkit`”。这样既保留浏览器缓存收益，也补齐 Ubuntu runner 上 `webkit/firefox` 的系统依赖，`bash scripts/test_ci_workflow_guards.sh` 与 `bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
