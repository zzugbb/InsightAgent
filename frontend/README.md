# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand 的 Agent 工作台前端。

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
- 阶段 5 协同：后端 PostgreSQL 迁移主线已启动（本轮前端页面无新增），为后续 auth e2e 打基础
- 阶段 5 联调排障（2026-04-14）：定位“发会话消息无响应”为后端 `POST /api/tasks` 返回 500（PostgreSQL SQL 类型兼容），后端修复后前端发送与流式恢复
- 阶段 5 国际化补齐：登录页（Auth Gate）接入 i18n，新增 `auth` 文案分组并覆盖中英文登录/注册全链路文案
- 阶段 5 体验补齐：登录页新增轻量设置模块（语言/主题/主题色），并完成登录页样式对深浅主题与主题色的联动适配
- 阶段 5 鉴权增强：接入 refresh token 持久化与自动刷新；401 优先尝试 `/api/auth/refresh` 轮换后重试，失败再回登录

## 当前已有内容

- 三栏布局：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 自动失效处理；退出入口融合到侧栏左下角设置区
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
- 模型设置提示修复：改用 `App.useApp().message` 显示保存/校验结果，避免 Ant Design 静态 message 主题上下文告警
- 模型设置展示优化：元信息区 `base_url/database` 改为普通文本展示；切换到 `mock` 时清空当前编辑态并在保存后清空远端凭证
- 模型设置回显修复：若后端当前已保存为 `remote`，切换回 `remote` 时会回显已保存 `provider/model/base_url`
- 会话鉴权：登录返回 `access_token + refresh_token + session_id`；退出时调用后端 `/api/auth/logout` 撤销当前会话 refresh token
- 账号切换防串：退出/401/重新登录时会清空 React Query 与流式轨迹状态，避免跨账号显示残留
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
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/types/trace.ts`：前端 TraceStep 类型
- `lib/api-client.ts`：REST 请求封装
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
- 默认知识库：`default`（对应 collection：`kb_default`）
- 后端落库会按用户隔离：`kb_{user_hash}_{knowledge_base_id}`

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

## 后续阶段决策（前端与部署视角）

### 优先做

1. 用户登录态与权限感知 UI（与后端鉴权联动）。
   - 当前状态：`full-data-auth` 首版联动已完成（Auth Gate + token 注入 + 401 自动回登录），后续补权限细粒度 UI 与受限能力显隐策略。
2. 历史会话/任务回放与导出体验（突出可观测卖点）。
3. 成本治理可视化（按用户/会话统计，配额/告警提示）。
4. 关键 e2e（登录、任务流、Trace 回放、RAG 检索）。

### 暂不做

1. 大规模 UI 重构或炫技动效重写（当前可用性已满足演示）。
2. 过早做复杂多模型编排面板（先把稳定性与治理打牢）。

### 部署建议

1. 前端优先部署到 Vercel 免费版。
2. 后端/FastAPI 与数据服务独立部署，不与前端运行环境绑定。

## 下一步（W4+）

- 配合后端把当前 mock `tool_start/tool_end` 升级为真实工具执行与失败重试可视化
- 在真实工具接入阶段复用当前 `retry_count/error` 字段语义，减少前端重构
- 继续完善 usage/token/cost 的统计维度（跨会话/时间段聚合）
- 持续优化流式回放体验（参数级调优与性能提升）
- 继续做不阻塞主链路的可访问性与交互细化
