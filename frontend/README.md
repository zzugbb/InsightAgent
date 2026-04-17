# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端服务 `node:24-alpine`、仓库根 `.nvmrc`）。本地可用 nvm/fnm 等按 `.nvmrc` 切换；`@types/node` 与运行时主版本对齐。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3：已完成（mock 范围）
- W4：已完成（RAG 面板 + Token/Cost 展示）
- 阶段 5 增量：已完成登录/注册入口页与 Auth Gate（token 持久化、401 自动回登录）
- 阶段 5 调整：已移除首次引导页，登录后直接进入工作台
- 阶段 5 收口：新增运行态提示条（mock/remote）与“去配置模型”快捷入口
- 阶段 5 收口：`remote` 未配置 `api_key` 时发送前前端直接阻断并引导配置
- 阶段 5 收口：登录页文案与白底可读性优化、退出按钮对齐优化、会话空标题默认展示回退为“新会话”
- 阶段 5 细化：登录区标题文案调整为“账号登录”、提交按钮禁用态可读性优化、退出入口迁移至左下角设置区并避让折叠控件
- 阶段 5 细化（继续）：移除“当前用户：未登录”提示、注册邮箱格式前置校验（替代 422 生硬报错）、登录输入 autofill/已填充态样式优化并适配浅色表单
- 阶段 5 文案收口：登录页左侧说明融合主页叙事（可观测智能体、对话到任务闭环），并补回 SSE/Trace、Memory/RAG、Token/Cost 等关键信息点
- 阶段 5 交互修复：登录密码框显隐图标恢复可见与可点击（支持显示/隐藏切换）
- 阶段 5 协同：后端 PostgreSQL 迁移主线已完成运行时收敛（前端请求统一通过鉴权 API 访问用户级数据）
- 阶段 5 联调排障（2026-04-14）：定位“发会话消息无响应”为后端 `POST /api/tasks` 返回 500（PostgreSQL SQL 类型兼容），后端修复后前端发送与流式恢复
- 阶段 5 国际化补齐：登录页（Auth Gate）接入 i18n，新增 `auth` 文案分组并覆盖中英文登录/注册全链路文案
- 阶段 5 体验补齐：登录页新增轻量设置模块（语言/主题/主题色），并完成登录页样式对深浅主题与主题色的联动适配
- 阶段 5 鉴权增强：接入 refresh token 持久化与自动刷新；401 优先尝试 `/api/auth/refresh` 轮换后重试，失败再回登录
- 阶段 5 账户可见性收口：当前登录用户展示已融合到左下角“设置”弹窗顶部，并采用与主题/主题色/语言一致的“图标 + 标题 + 值”行样式
- 阶段 5 聊天显示修复：发送后立即展示用户临时消息；assistant 流式卡片仅在生成中/失败态显示，避免切回会话前看到重复回复
- 阶段 5 增量：`remote-provider-hardening` 前端收口已完成首轮；流式 `error` 与设置校验失败已按 `error_code` 做本地化提示映射，并保留错误码用于排障
- 阶段 5 增量：`task-cancel-timeout` 前端首版已落地；Inspector「当前任务」支持取消运行中任务，流式状态接入 `cancelled/timeout` 事件提示
- 阶段 5 协同：后端已补齐 `task-cancel-timeout` e2e 脚本并接入后端 CI（baseline/main-path/cancel/timeout；CI 已升级 `checkout`/`setup-python` 以适配 GitHub Actions Node 24；后端 Python 与 compose/`.python-version` 统一为 3.14）；前端 Node 与 compose/`.nvmrc`/engines 统一为 **24.x**，可继续专注可视化回归与状态细化
- 阶段 5 增量：`running-task-recovery` 前端首版已落地；刷新页面或切回会话时会自动接管该会话下 `pending/running` 任务流，并展示恢复中/成功/失败提示
- 阶段 5 修复：会话切换时的任务串台已修复；流式状态按 `session_id` 绑定并按当前会话隔离渲染，避免短暂显示其他会话任务
- 阶段 5 修复：恢复提示误报已修复；任务结束瞬间若列表状态滞后，自动恢复不再错误提示“任务流恢复失败”
- 阶段 5 修复：聊天区滚动体验已修复；流式输出期间用户主动上滑阅读历史消息时，不再被强制拉回底部
- 阶段 5 修复：任务取消/超时后即使收到 `error(task_cancelled/task_timeout)`，也不再误判为失败态并显示“重试上次发送”
- 阶段 5 修复：流结束后的 `trace/delta` 自动补拉改为静默，不再覆盖底部状态为“暂无新的轨迹增量”
- 阶段 5 修复：待发送用户消息去重改为按 `task_id`，取消后再次发送相同文案会即时显示，不再被上一条同文案误隐藏
- 阶段 5 修复：发送后立即刷新 `tasks/messages`，并在任务列表回刷前用流式任务兜底展示“当前任务”取消按钮
- 阶段 5 修复：取消任务成功后会本地中断活动 SSE 流并立即退出“生成中”状态，发送按钮无需等待长延迟即可恢复
- 阶段 5 修复：remote 模式取消后加入短暂发送冷却，避免“取消后立刻重发”触发远端模型限流
- 阶段 5 交互升级：消息区“回到底部”按钮锚定在聊天区右下角（不随消息内容滚动）；上滑阅读期间若有新增输出，会显示数字徽标与轻脉冲提示
- 阶段 5 交互微调：回底按钮进一步上移+右移，减少对底部消息气泡与输入区的视觉遮挡

## 当前已有内容

- 三栏布局：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试；刷新失败后自动回登录；退出入口融合到侧栏左下角设置区
- 登录后默认策略：直接进入 Workbench；运行模式由设置决定，`remote` 配置不完整会被前端阻断并提示
- 审计入口迁移到左下角设置菜单（独立子页）：查看 `login/logout/refresh/settings_update` 事件，支持事件类型/时间范围/`session_id`/`task_id` 筛选、详情展开与 JSON/CSV 导出（可选“当前页/全部筛选结果”）
- 审计页交互收口：改为分页表格主视图；筛选改为双行下拉+输入检索并统一控件尺寸（支持一键重置）；事件类型标签化；总数下置表格左下角、操作区右对齐；会话/任务恢复 ID 展示，并恢复行展开查看明细（无二次展开，分页默认每页 10 条）
- 弹窗状态收口：审计日志弹窗与模型设置弹窗在每次打开时重置筛选/分页/提示与临时输入状态
- 模型设置弹窗：打开时按后端配置回显当前 `mode/provider/model/base_url`，并通过 `autocomplete` 策略禁用浏览器自动填充
- 模型设置弹窗回显修复：解决打开弹窗时默认值覆盖后端配置导致显示 `mock` 的问题
- 模型设置弹窗优化：下方元信息表新增 `base_url` 行；`remote` 模式显示“仅支持 OpenAI-compatible 接口”提示
- 模型设置弹窗模式联动：切换 `mock/remote` 时，表单字段与下方元信息同步切换；`mock` 仅保留固定 `provider/model`，隐藏 `base_url/api_key`
- 模型设置反馈收口：保存/校验成功失败统一使用 message 浮层提示（不再在弹窗顶部堆叠可关闭提示）
- 模型设置密钥语义调整：`remote` 下 `api_key` 留空将沿用已存密钥；仅在首次 remote 配置时必填
- 模型设置表单校验补齐：`remote` 下 `provider/model/base_url` 必填；`api_key` 在无历史密钥时必填
- 模型设置校验反馈优化：当远端返回 `401/403` 时，后端会返回明确鉴权错误（`remote_api_key_unauthorized`），避免展示为网络连通错误
- 模型设置错误提示补充：`validate` 失败时会优先按 `error_code` 映射友好文案，并附带错误码（如 `remote_preflight_network_error`）便于联调
- 模型设置提示修复：改用 `App.useApp().message` 显示保存/校验结果，避免 Ant Design 静态 message 主题上下文告警
- 模型设置展示优化：元信息区 `base_url/database` 改为普通文本展示；切换到 `mock` 时清空当前编辑态并在保存后清空远端凭证
- 模型设置回显修复：若后端当前已保存为 `remote`，切换回 `remote` 时会回显已保存 `provider/model/base_url`
- 聊天消息显示修复：发送后立即显示用户临时消息；assistant 流式消息仅在生成中/失败态显示，避免与落库历史消息重复
- 会话鉴权：登录返回 `access_token + refresh_token + session_id`；退出时调用后端 `/api/auth/logout` 撤销当前会话 refresh token
- 账号切换防串：退出/401/重新登录时会清空 React Query 与流式轨迹状态，避免跨账号显示残留
- 侧栏账户展示收口：用户信息已融合到左下角“设置”弹窗顶部，并采用与“主题/主题色/语言”同款行样式（图标 + 标题 + 值）展示，便于确认当前登录身份
- running task 恢复：持久化当前会话 ID，刷新后自动回到上次会话；若该会话存在 `pending/running` 任务，会自动复用 `/api/tasks/{task_id}/stream` 重连流继续展示，并在聊天区显示恢复状态提示条
- 会话隔离增强：`sseTask/sseTrace/ssePhase/sseUsage` 在 UI 展示层按当前会话过滤；跨会话后台流不会污染当前会话面板
- 恢复链路增强：同任务不重复触发自动恢复；`/stream` 返回 409（已非 pending/running）时按无害收敛处理，不再触发失败提示
- 流式滚动增强：自动跟随输出仅在“当前已贴底”时生效；离底阅读状态下保留当前位置，可通过“回到底部”按钮恢复跟随
- 待发送消息增强：pending user 仅对同 `task_id` 做去重，连续同文案发送可正确展示多条用户消息
- 当前任务增强：当 `tasks` 查询尚未刷新到新任务时，Inspector 使用流式任务兜底，取消按钮可即时点击
- 流式中断增强：新增 `cancelActiveStreamLocal`，取消成功后立即中断活动流读取，避免输入区长时间停留在“正在生成”
- 回底交互增强：滚动按钮移出消息滚动内容并锚定右下角，离底时固定可见，并通过徽标提示累计未读增量（最多 99+）
- 发送冷却增强：`remote` 模式取消成功后进入短暂冷却期，输入区提示“稍后发送”，冷却结束自动恢复发送
- 回底位置微调：按钮定位参数更新为更靠右、更靠上，避让聊天底部高频交互区
- 会话命名体验：空会话在首条消息发送后会自动改名为消息前缀（后端规则驱动）
- 会话：创建、切换、分页加载、重命名、删除
- 轨迹：时间线与流程图双视图（thought/action/observation/tool/rag 区分）
- 流式：SSE 任务状态、token 追加、trace 实时更新
- 回放：`trace` 全量与 `trace/delta` 增量加载（支持流式进行中的 `seq` 递增刷新 + 自动静默轮询 + 失败退避重试）
- `trace/delta` 请求会携带 `limit`（当前 200）控制单次增量拉取规模
- 若接口返回 `has_more=true`，前端会短间隔连续拉取以快速追平积压步骤
- 调度：页面在后台时暂停自动 delta 同步，前台自动恢复
- 观测：Context 摘要展示 delta 自动同步状态、重试次数、最近成功时间、下次重试时间、最近错误与恢复提示（恢复提示短时展示后自动消退）；重试中显示秒级倒计时
- 告警：delta 连续失败时显示轻提示并持续自动重试
- 右侧 Inspector（Context）信息架构已优化为分区式布局：概览 KPI、同步诊断、用量统计、Memory、任务索引；便于后续追加更多运维/分析模块
- `full-trace-session-lite` 首个切片已落地：Context 新增「任务快照」分区，支持展示选中任务的 prompt、最终回答摘要、最终观察、RAG 命中、步骤数、状态/时间与失败提示，并接入快速跳转
- `trace-export-json-md` 首版已落地：任务快照分区新增“导出 JSON / 导出 Markdown”按钮，可一键导出当前任务（task-linked 消息、TraceStep、RAG chunks、usage、元信息）
- `session-export-lite` 首版已落地：Context 新增“会话导出”分区，支持导出当前会话 JSON / Markdown（消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage）
- 任务索引增强：支持状态筛选（全部/运行中/已完成/失败）、时间排序（最新/最早）与失败置顶
- 任务索引增强：支持按任务标题/ID 搜索，并在失败任务上展示失败摘要提示
- Trace 面板增强：支持步骤类型筛选（全部/思考/行动/观察/工具/RAG/其他）、关键词检索、类型计数统计，且在时间线与流程图视图一致生效
- 右侧面板（Inspector）完成一体化优化：Trace 支持舒适/紧凑密度切换；Context 支持分区快速跳转（概览/同步/用量/记忆/任务）；任务状态使用语义徽标统一展示
- 左侧/中栏优化：侧栏会话区强化激活层级；聊天头部改为统一 runtime strip；消息流与输入区补充克制动效并统一节奏
- 交互收敛：已移除会话状态胶囊与输入计数提示，模式/提供方/模型恢复为头部紧凑标签展示，减少纵向占用
- 后端任务接口已提供 `status_normalized/status_label/status_rank`，前端可继续按需切换到后端统一状态语义
- W3 增量：`tool_end` 与 `trace.meta.tool` 已接入 `retry_count/error`，Trace 元信息可展示工具重试次数与错误摘要（配合 `[mock-tool-error]` / `[mock-tool-fatal]` 触发）
- W3 优化：新增计算器工具链路展示（`[calc:1+2*3]` 或“计算 1+2*3”），沿用现有工具状态可视化
- W1 优化：模型设置弹窗新增“校验配置”按钮，先调用 `POST /api/settings/validate` 再决定是否保存
- W2 稳定性优化：SSE + `trace/delta` 合并后的步骤按 `seq` 稳定排序，降低轨迹偶发乱序
- W2 稳定性优化：`trace/delta` 增加任务隔离保护，切换任务时旧请求晚到不会串写当前轨迹
- W2 稳定性优化：SSE 事件增加 `task_id` 活动任务隔离，避免并发/延迟事件污染当前任务
- W2 收敛优化：SSE phase 统一归一（`completed→done`、`failed→error`），并集中流式文案常量，减少状态分支判断
- W2 稳态优化：有活动任务时，缺失 `task_id` 的非 `start` 事件会被忽略，进一步降低串台风险
- W2 性能优化：`trace` 事件处理移除重复 `upsert` 计算，降低高频流式更新开销
- W2 展示优化：phase 映射补齐 `thinking/tool_running/tool_retry`，统一运行态展示
- W1/W2 国际化优化：`chat-stream-store` 流式提示改为 i18n 文案（`stream` 分组），支持中英文动态切换并消除硬编码英文
- W2 稳态优化：`trace/delta` 更新 `traceCursor` 时强制单调递增，避免并发增量请求导致游标回退
- W2 性能优化：`token` 事件改为单次 store 写入（文本 + trace 同步更新），减少高频渲染抖动
- W1/W2 国际化收口：流式“空闲提示”纳入 i18n，语言切换时空闲提示可即时刷新
- W1/W2 国际化维护优化：store 默认流式文案直接复用 `en.stream`，避免与 i18n 文案表双份维护
- W3 稳定性优化：仅在 `error.fatal=true` 时将流状态置为 `error`，可重试工具错误不再误触发全局失败态
- W4+ 稳定性优化：流式 `error` 事件已读取 `code/detail/status_code`，优先展示按错误码映射后的本地化提示，并在消息中附带错误码
- W2 协同优化：后端 `running` 重连流的 `done/error` 事件已补齐关键字段（`session_id/step_id/resumed`），前端消费契约更稳定
- usage 展示：支持当前任务、任务列表摘要；汇总由后端 `GET /api/tasks/usage/summary` 驱动（全局/会话自动切换），并具备 loading/error/empty 状态与统计覆盖率展示
- Memory：状态展示 + add/query 调试（含 metadata）
- RAG：知识库状态展示 + 文本 ingest + 语义检索命中展示（`/api/rag/*`）
- RAG 交互优化：知识库 ID 采用“输入后应用”模式，避免输入期间频繁触发状态请求
- Trace 元信息：支持展示步骤级 `cost_estimate`
- 设置：主题、主题色、语言、模型与运行模式
- 工程校验：已配置 `.eslintrc.json`，`npm run lint` 可直接运行且当前告警已清零
- 鉴权联动：除 `/health` 与 `/api/auth/*` 外，其余请求统一自动注入 Bearer token

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/inspector.tsx`：任务快照导出入口（JSON/Markdown）
- `app/components/workbench/inspector.tsx`：会话导出入口（Session JSON/Markdown）
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、折叠侧栏与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：主题/主题色/语言、当前登录用户、模型设置与审计入口
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx`：审计日志筛选、分页、展开与导出
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/types/trace.ts`：前端 TraceStep 类型
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期与 401 失效广播
- `lib/preferences-context.tsx` / `lib/i18n/*`：主题、主题色、语言与中英文文案
- `app/components/auth/auth-gate.tsx`：登录/注册页与鉴权网关

## SSE 消费与契约对齐

当前前端按以下事件消费：
- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `done`
- `error`

`trace` 事件中的 `step` 与后端 REST `TraceStep` 同构，`dispatchSseEvent`（`lib/stores/chat-stream-store.ts`）为当前权威消费路径。
`tool_start/tool_end` 会先行驱动 action 节点状态，再由 `trace` 事件补齐持久化快照。
流式任务期间，Workbench 会定时静默拉取 `trace/delta`，失败时按退避策略重试，并在流结束后自动补拉一次，降低 SSE 与持久化快照的短暂偏差。
同步健康度会在 Inspector Context 区域实时展示，便于定位网络抖动或增量拉取异常。
当连续失败达到阈值时会显示非阻塞告警文案，不影响主任务流。
重试中的最近错误信息会直接显示在摘要区，便于快速定位失败原因。

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
- 实际 collection：`kb_{user_hash}_{knowledge_base_id}`；默认知识库在当前用户下对应 `kb_{user_hash}_default`

## PostgreSQL / Memory / RAG 怎么看（前端通俗版）

- 聊天记录来源（左侧会话 + 中栏消息 + 任务历史）：
  - 来自后端 `PostgreSQL` 的会话/消息/任务数据。
- Memory 面板（会话级）：
  - 面向当前 `session_id` 的语义记忆（`memory_{session_id}`）。
  - 适合查看“本次对话中需要记住的约束和结论”是否被写入/检索到。
- RAG 面板（知识库级）：
  - 面向 `knowledge_base_id` 的知识库（后端落库为 `kb_{user_hash}_{knowledge_base_id}`）。
  - 适合管理手册、FAQ、文档片段的 ingest 与检索命中。

可用一句话理解：

- `PostgreSQL` 管完整历史；
- `Memory` 管会话便签；
- `RAG` 管外部知识库。

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端（未设置时使用 `http://127.0.0.1:8000`）。

如需一键拉起依赖并启动前后端（推荐），可在仓库根目录执行：

```bash
./start_insightagent.command
```

脚本会先确保 `postgres/chroma` 就绪，再启动 backend/frontend，适合本地联调直接使用。
其中 Chroma 就绪检查已切换为 `v2` heartbeat，兼容新版镜像；并会在启动前清理旧 `next dev` 进程且等待前端可访问。

## 后续阶段决策（前端与部署视角）

### 优先做

1. `full-trace-session-lite`：任务详情抽屉/页面（任务快照 + 回放）已接入；后续补详情视图增强与导出 e2e。
2. `trace-export-json-md`：单任务 JSON/Markdown 导出入口已接入；后续补导出 e2e。
3. `session-export-lite`：当前会话 JSON/Markdown 导出入口已接入；后续补导出 e2e。
4. `remote-provider-hardening`：真实模型错误提示、重试建议与设置入口联动。
5. `e2e-main-path`：后端主链路 e2e 脚本已落地（登录、模型设置、发送消息、Trace 回放、RAG 检索、导出），前端后续接入 CI 与可视化回归。
6. `task-cancel-timeout`：首版已落地（取消按钮 + 状态提示）；后端 e2e/CI 已补齐，前端后续补更细粒度反馈与可视化回归。
7. `running-task-recovery`：前端首版与恢复状态提示已落地（刷新/切回会话自动恢复 running 任务流）；后续补失败快照与可观测指标。
7. `rag-kb-governance-lite`：知识库列表、清空/删除、来源展示。
8. `usage-dashboard-lite`：用户/会话/任务维度成本统计增强。

### 暂不做

1. 大规模 UI 重构或炫技动效重写（当前可用性已满足演示）。
2. 过早做复杂多模型编排面板（先把稳定性与治理打牢）。
3. PDF/视频/GIF 自动导出（先用 JSON/Markdown 导出服务回放与演示）。

### 部署建议

1. 前端优先部署到 Vercel 免费版。
2. 后端/FastAPI 与数据服务独立部署，不与前端运行环境绑定。

## 下一步（W4+）

- 历史任务详情/Trace 回放已进入开发：任务快照、单任务导出、会话导出已完成。
- 下一步聚焦前端可视化回归（CI）与运行态细粒度反馈（cancel/timeout）。
- P0 完成后再推进任务取消/超时、RAG 知识库治理与 usage 统计增强。
