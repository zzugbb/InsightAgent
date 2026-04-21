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
  - 后端 e2e CI 首版已接入：新增 GitHub Actions 工作流 [backend-e2e.yml]，覆盖 baseline/main-path/cancel/timeout；工作流已升级 `actions/checkout@v6`、`actions/setup-python@v6` 以适配 GitHub Actions Node 24 运行时（消除 Node 20 action 弃用提示）；Python 运行时统一为 **3.14**（与 `compose.full.yml`、根目录 `.python-version` 一致）；前端 **Node.js 24.x** 已对齐（`compose.full.yml` 前端镜像、`frontend/package.json` engines、根目录 `.nvmrc`）；本地已验证 `compileall`、`frontend npm run lint` / `npm run build` 通过
  - 前端可视化回归 CI 首版已接入：新增 Playwright 用例（用量统计弹窗主路径 + 来源趋势区可见性）与 `.github/workflows/frontend-e2e.yml`（拉起 postgres/chroma/backend 后执行前端 e2e）
  - CI Node 24 对齐补充：`frontend-e2e` 工作流已将 `actions/setup-node` 升级到 `v5`、`actions/upload-artifact` 升级到 `v5`，并显式启用 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`，消除 Node 20 action 弃用告警
  - CI 修复补充：修正 `.github/workflows/frontend-e2e.yml` 的 YAML 缩进错误（`push` 触发器误嵌套到 `env`），恢复工作流可解析性
  - 前端回归稳定性修复：Playwright 登录态注入改为显式透传 storage key（避免浏览器上下文常量不可见导致的未登录误失败）
  - 前端回归稳定性修复（第二次）：`usage-dashboard` 用例新增 UI 登录兜底（若未命中 Workbench 则自动登录），避免 CI 冷启动/状态差异下找不到设置入口
  - 鉴权接口：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`
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
  - 右侧 Inspector（Context）完成信息架构优化：概览 KPI + 同步诊断 + 用量统计 + Memory + 任务索引分区，弱化堆叠卡片并保留扩展位
  - `full-trace-session-lite` 首个切片已落地：Context 新增「任务快照」分区，可基于选中任务展示输入 prompt、最终回答摘要、最终观察、RAG 命中统计、步骤数、任务状态/时间与失败提示，并支持快速跳转
  - `trace-export-json-md` 首版已落地：支持单任务导出 JSON 与 Markdown（含任务元信息、task-linked 消息、TraceStep、RAG chunks 与 usage），并在任务快照区提供一键导出入口
  - `session-export-lite` 首版已落地：支持当前会话导出 JSON 与 Markdown（会话消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage 汇总），并在 Context 新增“会话导出”分区
  - 任务索引支持前端本地筛选与排序（状态筛选、时间顺序、失败任务优先），便于运行态排障
  - 任务索引支持关键词快速定位（标题/ID）与失败摘要提示，便于快速定位异常任务
  - Trace 面板支持步骤类型筛选、关键词检索与类型计数（时间线/流程图一致生效），提升长轨迹排障效率
  - 右侧面板完成一体化收口优化：Trace 密度切换、Context 快速跳转、状态徽标与分区说明统一，兼顾当前能力与后续扩展
  - 左侧与中栏完成统一风格优化：会话导航强化激活层级、聊天头部运行态信息条收敛、消息与输入区交互节奏统一
  - 根据最新交互收敛要求，已移除会话状态胶囊与输入计数提示，头部恢复紧凑模式标签展示
  - 轨迹支持「时间线 / 流程图」双视图（thought/action/observation/tool/rag 区分）
  - 会话支持分页加载、重命名、删除
  - Context 面板支持 Memory 状态展示、add/query 调试
  - Context 面板新增 RAG 管理区：知识库状态、文本 ingest、语义检索命中展示
  - RAG 知识库 ID 改为“输入后应用”模式，避免输入过程频繁触发状态请求
  - 设置弹窗新增知识库治理子页：按账号列出知识库、显示来源采样，并支持行级清空/删除
  - Trace 元信息支持展示每步 cost（`meta.cost_estimate`）
  - usage 展示增强：支持全局/会话自动切换汇总，含加载/错误/空状态与覆盖率（with_usage/total）
  - usage 来源可视化：Inspector 当前任务/任务快照/任务索引已展示 usage 来源（provider/estimated）
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

- `full-trace-session-lite` 与导出链路持续推进中：任务快照、单任务导出、会话导出、remote 错误体验与主链路 e2e 首版脚本均已落地；下一步补导出稳定性校验与失败快照归档。
- `task-cancel-timeout` 后端 e2e（cancel + timeout）与 CI 首版已落地，`running-task-recovery` 前端首版与可视化提示已落地，`rag-kb-governance-lite`、`usage-dashboard-lite`、`audit-event-expansion` 与 `provider-usage-alignment` 已完成首版并补齐来源趋势联动；前端可视化回归 CI 首版也已接入，下一步推进导出稳定性回归。
