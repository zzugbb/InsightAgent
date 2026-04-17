# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3：已完成（mock 范围）
- W4：已完成（RAG + Token/Cost + compose.full）
- 阶段 5 增量：`full-data-auth` 首版已落地（JWT、用户隔离、用户级设置与密钥加密存储）
- 阶段 5 增量：最小会话管理已落地（refresh token 轮换、会话查询/撤销、退出当前/全部会话）
- 阶段 5 增量：最小审计已落地（`login/logout/refresh/settings_update` 事件写入 `audit_logs`）
- 阶段 5 增量：PostgreSQL 迁移主线已完成运行时收敛（后端运行时使用 PostgreSQL + 保留平迁脚本）
- 阶段 5 排查修复（2026-04-14）：修复 PostgreSQL 下 `POST /api/tasks` 的 `CASE WHEN` 参数类型错误（smallint -> boolean），恢复消息发送链路
- 阶段 5 排查补充：已复核 `sessions/tasks/messages/settings/rag` 查询与写入路径，核心数据均按 `user_id` 隔离
- 会话命名补充：空会话在首条消息发送时，若仍为占位标题则自动改为首条消息前缀
- 会话命名规则补充：仅在“无历史消息 + 占位标题”条件下自动命名，不覆盖用户手动重命名
- 协同进展（前端侧）：已完成登录表单填充态样式优化、密码显隐图标可见性与切换修复、登录页左侧文案（主页叙事 + 关键信息）收口、退出入口并入左下角设置模块
- 协同进展（前端侧）：已完成登录页国际化接入（Auth Gate 新增 `auth` 文案分组并覆盖中英文）
- 协同进展（前端侧）：已完成登录页设置模块（语言/主题/主题色）与主题/主题色联动适配
- 协同进展（前端侧）：已移除首次引导页；新用户登录后直接进入工作台，未配置模型时沿用用户默认设置（通常 `mock`）
- 工程协作：前端 `npm run lint` 已可直接执行，且当前告警已清零
- 协同进展：前端已切换到后端 usage 聚合接口（全局/会话双范围），并显示覆盖率与状态反馈（loading/error/empty）
- 协同进展：前端审计页已升级为分页表格可读视图（双行下拉+输入检索且控件尺寸统一、操作区右对齐、表格下方总数展示、事件标签区分、会话/任务 ID 展示、行展开明细，分页默认每页 10 条），继续复用现有 `GET /api/audit/logs` 契约
- 协同进展：前端已收口弹窗状态管理（审计日志/模型设置每次打开重置状态），避免旧筛选与旧提示跨次污染
- 协同进展：模型设置弹窗已改为“打开按后端配置回显 + 禁用浏览器自动填充”，避免浏览器凭证误填并保留可读回显
- 协同进展：前端右侧 Inspector（Context）已按可观测运维场景完成分区重排（概览/同步诊断/用量/Memory/任务索引），后端现有字段可直接支撑后续模块扩展
- 协同进展：前端任务索引已支持本地状态筛选/时间排序/失败置顶，不新增后端接口负担
- 协同进展：前端任务索引已支持标题/ID 快速检索与失败摘要提示（由现有任务字段推导），无需新增后端接口
- 协同进展：前端 Trace 面板已支持步骤类型筛选/关键词检索/类型计数，复用现有 TraceStep 字段，无需新增后端接口
- 协同进展：前端右侧 Inspector 已完成一体化收口（Trace 密度、Context 快速跳转、状态徽标），均基于现有字段推导，无需新增后端接口
- 协同进展：`full-trace-session-lite` 首个前端切片已接入（任务快照：prompt/最终回答摘要/最终观察/RAG 命中/状态与失败提示），复用现有 `GET /api/tasks` + `GET /api/tasks/{task_id}/trace` 契约，无需新增后端接口
- 协同进展：`trace-export-json-md` 首版已接入；新增 `GET /api/tasks/{task_id}/export/json` 与 `GET /api/tasks/{task_id}/export/markdown`，导出包含任务元信息、task-linked 消息、TraceStep、RAG chunks、usage
- 协同进展：`session-export-lite` 首版已接入；新增 `GET /api/sessions/{session_id}/export/json` 与 `GET /api/sessions/{session_id}/export/markdown`，导出包含会话消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage 汇总
- 阶段 5 增量：`remote-provider-hardening` 首轮已完成；Provider 运行时统一输出结构化错误码（401/403、429、5xx、网络、无效 JSON、空响应、SSE 中断），任务流 SSE `error` 事件透传 `code/fatal/retryable/detail/status_code`
- 阶段 5 增量：`task-cancel-timeout` 首版已落地；新增取消接口与超时中断，任务流支持 `cancelled/timeout` 事件
- 阶段 5 增量：`task-cancel-timeout` e2e 已补齐；新增 `scripts/e2e_task_cancel_timeout.py`，覆盖取消链路与超时链路（低 `TASK_TIMEOUT_SEC` 环境）
- 工程化增量：后端 e2e CI 首版已接入（`.github/workflows/backend-e2e.yml`，已升级 `checkout`/`setup-python` 主版本以适配 GitHub Actions Node 24 运行时；Python **3.14** 与 `compose.full.yml`、根目录 `.python-version` 对齐）
- 协同进展：前端已接入 `running-task-recovery` 首版（刷新/切回会话自动接管 running/pending 任务流），并补齐恢复中/成功/失败可视化提示，复用现有 running reconnect SSE 能力
- 协同修复：前端流式展示已按 `session_id` 做会话隔离，切换会话时不再短暂串出其他会话任务
- 协同修复：针对任务完成瞬间的状态滞后场景，前端恢复链路已避免误报“恢复失败”（同任务去重 + stream 409 无害收敛）
- 协同修复：前端聊天区流式自动滚动已改为“仅贴底跟随”，用户上滑查看历史时不再被强制拉回底部
- 协同修复：任务取消/超时后即使后端追加 `error(task_cancelled/task_timeout)`，前端也不会误判为 fatal 失败态并展示“重试上次发送”
- 协同修复：流结束后的 `trace/delta` 自动补拉已改为静默，避免底部状态提示被“暂无新的轨迹增量”覆盖
- 协同修复：待发送用户消息去重改为按 `task_id`，取消后再次发送相同文案可即时显示，不再被上一条同文案误隐藏
- 协同修复：发送后前端会立即刷新 `tasks/messages`，并在任务列表回刷前用流式任务兜底展示“当前任务”取消按钮
- 协同进展：前端左侧与中栏已完成风格收口（导航层级、runtime strip、输入区动效与密度），继续复用现有接口与字段
- 协同进展：前端已按最新交互要求收敛头部占位（移除会话状态胶囊与输入计数提示），继续复用现有接口与字段
- 协同进展：前端侧栏账户展示已收口到左下角“设置”弹窗顶部，并采用与主题/主题色/语言一致的设置行风格（图标 + 标题 + 值）
- 协同进展：前端流式状态提示已完成 i18n 化（去除硬编码英文，按语言动态切换），后端接口契约无需调整
- 协同进展：前端 store 默认流式文案改为复用 `en.stream`，减少文案漂移风险，后端契约保持不变
- 协同进展：模型设置弹窗元信息补充 `base_url` 展示，并在 `remote` 模式下增加 OpenAI-compatible 协议提示，前后端设置契约保持不变
- 协同进展：模型设置弹窗按模式联动展示；`mock` 固定 `provider/model` 且隐藏 `base_url/api_key`，切换模式时回显逻辑与后端设置保持一致
- 协同进展：模型设置弹窗提示改为 antd 上下文 `message`（通过 `App.useApp()`），消除动态主题下静态 message 警告
- 协同进展：模型设置切换到 `mock` 后保存会显式清空 `api_key/base_url`，避免历史 remote 凭证残留
- 协同进展：当已保存 `remote` 配置时，前端切换回 `remote` 会回显后端已存 `provider/model/base_url`
- 协同进展：前端聊天区已修复“发送消息不即时显示 + assistant 重复显示”问题（用户消息乐观显示，流式回复仅在生成中/失败态展示）
- 状态增强：`/api/tasks*` 响应已补充 `status_normalized`、`status_label`、`status_rank`，统一状态语义并保持向后兼容
- W3 增量：mock 工具链路支持可复现错误语义（`[mock-tool-error]` 可恢复重试，`[mock-tool-fatal]` 致命失败），`tool_end/error/trace.meta.tool` 已输出 `retry_count/error`
- W3 优化：新增本地计算器工具 `calc_eval`（支持 `[calc:1+2*3]` 与“计算 1+2*3”触发），纳入统一工具生命周期事件
- W1 优化：新增 `POST /api/settings/validate`，用于设置保存前的结构/连通性预校验（不落库）
- W1 优化补强：`settings/validate` 在 `HEAD` 失败时自动回退 `GET`，减少远端网关不支持 HEAD 时的误判
- W1 预检修复：`settings/validate` 的远端探测请求补充 `Authorization` 头；`401/403` 返回 `remote_api_key_unauthorized`（不再归类为 network error）
- W1 设置语义收口：`remote` 模式下 `api_key` 留空沿用历史密钥（首次配置仍必填）
- W1 能力补齐：`remote` 模式已接入 OpenAI-compatible provider（`base_url + api_key + model`）
- W1 接口校验补齐：`remote` 模式 `provider/model/base_url` 必填；`api_key` 在未配置历史密钥时必填，已配置时可留空沿用
- W1 接口收口：`POST /api/settings/validate` 新增 `error_code`，并补充 `remote_base_url_required`
- W1/W2 稳定性优化：SSE 流式输出增加周期 heartbeat（长输出保活更稳定）+ trace 持久化写入节流（降低数据库写放大）
- W2 优化：`GET /api/tasks/{task_id}/stream` 支持 `running` 状态重连（回补增量，不重复执行任务）
- W2 重连流优化：`running` 重连返回的 `done/error` 事件补齐 `session_id/step_id` 并标记 `resumed=true`
- W2 重连轮询优化：重连流按“有增量快轮询、无增量退避慢轮询”策略拉取 delta，降低 DB 轮询压力
- W2 后端性能优化：新增 task 快照级 delta 计算，重连流循环复用单次 `get_task` 结果，减少重复查询
- W2 语义优化：`GET /api/tasks/{task_id}/trace/delta` 的 `lag_seq` 改为基于任务快照真实尾游标计算，避免恒零
- W2 重连兼容优化：`GET /api/tasks/{task_id}/stream`（running）支持 `after_seq` 与 `Last-Event-ID` 双游标恢复
- W1 可调优优化：trace 写入节流间隔支持环境变量 `TRACE_PERSIST_MIN_INTERVAL_SEC`
- W1/W2 可调优优化：running 重连流轮询与 heartbeat 参数支持环境变量（`STREAM_RECONNECT_POLL_FAST_SEC` / `STREAM_RECONNECT_POLL_MAX_SEC` / `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`）
- W1 usage 语义优化：`completion_tokens` 改为基于最终输出文本估算（覆盖流式与 fallback 场景）

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- 新增 `auth_sessions` 表：refresh token 哈希持久化、会话过期/撤销管理
- 新增 `audit_logs` 表：最小审计事件持久化（`event_type` + `event_detail_json`）
- `app/providers/`：Provider 抽象 + mock 实现 + OpenAI-compatible provider
- `app/services/chat_execution_service.py`：SSE 任务流（mock 四步 trace）
- 流式阶段已支持最终 `observation` 的批次增量持久化（`seq` 递增，默认每 8 个 chunk 落库一次 + 结束兜底）
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/chroma_rag_service.py`：用户级 RAG collection 命名、ingest/query/status
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 `done.usage`（前端可用于任务列表摘要展示）

## HTTP 接口（摘要）

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- 最小审计事件：`login`、`logout`、`refresh`、`settings_update`
- 审计查询：`GET /api/audit/logs?event_type=&session_id=&task_id=&start_at=&end_at=&limit=&offset=`（前端可按当前页/全量筛选结果导出）
- `GET /api/auth/me`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`（含 `total/has_more`）
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
- `GET /api/tasks?limit=&offset=&session_id=`（含 `total/has_more`）
- `GET /api/tasks*` 相关响应包含状态派生字段：`status_normalized`、`status_label`、`status_rank`
- `GET /api/tasks/usage/summary`（可选 `session_id`）
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/query`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`（`pending/running`；running 为重连回补流）
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`（`limit` 默认 200，最大 500；`has_more` 反映剩余分页或任务仍在运行）
- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`

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

其中 `event: trace` 的 `data.step` 与 REST TraceStep 同构（`id/type/content/meta/seq?`）。
`tool_start/tool_end` 使用与 action 节点一致的 `step_id`，可与 trace 节点一一对齐。
当输入包含 `[mock-tool-error]` 时，会先触发一次工具错误并发出 `error(fatal=false,retryCount=1)`，随后自动重试并完成；
当输入包含 `[mock-tool-fatal]` 时，会触发工具致命失败并直接结束任务（`status=failed`）。
当输入包含 `[calc:表达式]`（如 `[calc:1+2*3]`）或文本“计算 1+2*3”时，会触发本地计算器工具并在 Trace 中记录 `input/output/status`。
`trace/delta?after_seq=` 现可在任务流式进行中拉取到最终 `observation` 的阶段性刷新内容。
前端已接入流式期间定时拉取、失败退避重试与流结束补拉，后端接口保持幂等增量语义。
前端 Context 摘要会展示 delta 同步状态/重试次数/最近成功时间，便于联调与问题定位。
当前在连续失败场景下也会显示轻提示，后端接口无需额外状态字段。
并会展示下次重试时间、最近错误内容与恢复提示（短时自动消退），重试中还有秒级倒计时，便于确认故障是否恢复。
页面后台时前端会暂停自动 delta 拉取，返回前台后恢复，不影响接口幂等语义。
远端 Provider 异常会由 `ProviderCallError` 归一并在 SSE `error` 中透传稳定 `code`，便于前端做提示映射与排障定位。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- RAG collection 命名：`kb_{user_hash}_{knowledge_base_id}`（按用户隔离）
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 流式 trace 写入节流：`TRACE_PERSIST_MIN_INTERVAL_SEC`（默认 `0.35` 秒）
- running 重连流参数：
  - `STREAM_RECONNECT_POLL_FAST_SEC`（默认 `0.3`）
  - `STREAM_RECONNECT_POLL_MAX_SEC`（默认 `2.0`）
  - `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`（默认 `2.0`）
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：`memory/add`、`memory/query`、`rag/ingest`、`rag/query` 返回 503；任务后的摘要写入为 best-effort

### 通俗分工（后端视角）

- `PostgreSQL`（业务主存储）：
  - 存 `sessions / tasks / messages`，以及任务 `trace_json / usage_json`。
  - 用于会话列表、消息历史、任务状态回放与统计聚合。
- `Chroma Memory`（会话记忆）：
  - collection：`memory_{session_id}`。
  - 存当前会话的可检索记忆片段（含任务完成后的摘要追加）。
  - 目标是低成本召回“这次会话刚刚说过的重要信息”。
- `Chroma RAG`（知识库检索）：
  - collection：`kb_{user_hash}_{knowledge_base_id}`。
  - 存 ingest 后的文档分块与 metadata，用于跨会话复用知识检索。

为什么不合并成一个库：

- `RAG` 主要解决“系统知道什么文档”，不等于“当前会话刚约定了什么”。
- `Memory` 主要解决“当前会话记住什么”，不适合承载大规模知识文档治理。
- `PostgreSQL` 是权威历史账本；Chroma 两类 collection 是检索层索引，不替代业务主数据。

当前实现注意点：

- 删除会话时会级联删除 PostgreSQL 的 tasks/messages，并会 best-effort 删除 Chroma `memory_{session_id}` collection（清理失败不阻塞主删除流程）。

## W4 新增说明

- 执行链路 `mock_retrieve` 已接入真实知识库检索（默认 `kb_{user_hash}_default`，可通过 `[kb:xxx]` 指定）
- `TraceStep.meta.rag` 会记录命中 `chunks` 与 `knowledge_base_id`
- usage 升级为可计算字段：
  - `prompt_tokens`、`completion_tokens`
  - `cost_estimate`（可通过环境变量配置单价）
- 新增环境变量：
  - `RAG_DEFAULT_KNOWLEDGE_BASE_ID`
  - `RAG_DEFAULT_TOP_K`
  - `USAGE_PROMPT_TOKEN_PRICE_PER_1K`
  - `USAGE_COMPLETION_TOKEN_PRICE_PER_1K`

## 阶段 5 增量（full-data-auth 首版）

- 新增用户认证：`register/login/me`，JWT（HS256）签发与校验
- 新增最小会话管理：refresh token（哈希落库）轮换、会话查询与撤销（按 session / 全部）
- 新增 `users` / `user_settings` 表，并将 `sessions/tasks/messages` 写入与查询切为 `user_id` 隔离
- 新增 `auth_sessions` 表（refresh token 哈希、过期时间、撤销时间、UA/IP）
- 设置改为用户级，`api_key` 以服务端主密钥加密后落库（`user_settings.api_key_enc`）
- 新增环境变量：
  - `INSIGHT_AGENT_JWT_SECRET`
  - `INSIGHT_AGENT_ACCESS_TOKEN_TTL_MINUTES`
  - `INSIGHT_AGENT_REFRESH_TOKEN_TTL_DAYS`
  - `INSIGHT_AGENT_SECRET_KEY`

## 阶段 5 增量（PostgreSQL 迁移主线）

- 后端运行时统一使用 PostgreSQL：
  - `INSIGHT_AGENT_DATABASE_URL=postgresql://...`
- `app/db.py` 已收敛为 PostgreSQL 单后端实现（业务 SQL 调用层保持不变）
- 新增迁移脚本：`scripts/migrate_sqlite_to_postgres.py`
  - 平迁表：`users`、`user_settings`、`sessions`、`tasks`、`messages`
  - 策略：幂等 upsert（可重复执行）

## 本地启动

推荐使用 **Python 3.14**（与 `compose.full.yml`、GitHub Actions `backend-e2e` 一致；仓库根 `.python-version` 为 `3.14`，便于 pyenv 等对齐）。若旧版解释器创建过 `backend/.venv`，`pyvenv.cfg` 可能仍指向旧版本且与 `bin/python` 不一致，应**删除 `backend/.venv` 后**用 3.14 重新执行 `python -m venv .venv` 与 `pip install -r requirements.txt`，不要手改 `pyvenv.cfg`。

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端（推荐），可在仓库根目录执行：

```bash
./start_insightagent.command
```

该脚本会自动拉起并等待 `postgres/chroma` 就绪，且已兼容 `backend/.env` 缺失场景。
脚本内 Chroma 就绪检查使用 `v2` heartbeat，兼容新版 Chroma 容器；启动前会额外清理旧后端进程，并等待后端健康检查通过。
后端进程由**本机解释器**启动：优先 `backend/.venv/bin/python`，否则回退 `python3`（见脚本内逻辑）；请使用 **Python 3.14** 创建/重建 `.venv`，与仓库根 `.python-version` 及 CI 一致。`compose.full.yml` 中的 `python:3.14-slim` 仅在「用 Compose 跑后端容器」时使用，与一键脚本的本地 uvicorn 路径相互独立。前端 dev 依赖本机 **Node.js 24.x**（与根目录 `.nvmrc`、`frontend/package.json` 的 `engines` 一致；一键脚本里为 `npm run dev`，不经过 `node:24-alpine` 镜像）。

如需将本地 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

最小 e2e 基线（登录/过期/登出/跨账号隔离/发送流）可执行：

```bash
python scripts/e2e_baseline.py --base-url http://127.0.0.1:8000
```

主链路 e2e（登录 -> 设置校验/保存 -> 发送任务并校验 trace -> RAG ingest/query -> 任务/会话导出）可执行：

```bash
python scripts/e2e_main_path.py --base-url http://127.0.0.1:8000
```

取消/超时链路 e2e 可执行（默认先跑取消；超时链路建议在低超时后端实例验证）：

```bash
# 默认本地后端（通常 TASK_TIMEOUT_SEC 较大）可先验证取消链路
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout

# 单独起一个低超时实例验证 timeout（示例：1 秒）
TASK_TIMEOUT_SEC=1 uvicorn app.main:app --host 127.0.0.1 --port 8010
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8010
```

如需 Memory 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

## 后续阶段决策（后端视角）

### 优先做

1. `full-trace-session-lite`：任务详情快照与导出入口已接入；后续补详情视图增强与导出 e2e。
2. `trace-export-json-md`：单任务 JSON/Markdown 导出接口已落地；后续补字段稳定性与导出 e2e 校验。
3. `session-export-lite`：会话级 JSON/Markdown 导出接口已落地；后续补字段稳定性与导出 e2e 校验。
4. `remote-provider-hardening`：已完成首轮（错误码归一 + SSE 透传 + 前端映射联动）。
5. `e2e-main-path`：主链路 e2e 脚本已落地（登录、模型配置、任务流、Trace、RAG、导出）并接入后端 CI；后续补失败快照留档。
6. `task-cancel-timeout`：首版已落地（取消接口 + 超时中断 + SSE 事件），并新增 cancel/timeout e2e 脚本；后续补细粒度状态反馈。
7. `running-task-recovery`：前端恢复链路已接入，后续可补失败快照与恢复可观测字段。
8. `rag-kb-governance-lite`：知识库列表、清空/删除 collection、来源展示。
9. `usage-dashboard-lite` / `audit-event-expansion`：补用户/会话/任务维度统计与关键事件审计。

### 暂不做

1. Redis/Kafka/Celery 分布式队列（当前规模不需要）。
2. K8s / 微服务拆分（对当前阶段收益低）。
3. 复杂多跳 RAG 与重排体系（先把最小治理与导出复盘做扎实）。
4. 企业级 SSO/RBAC 全套（保留扩展位，先做轻量 RBAC）。

## 当前限制（W4 生产化前）

- PostgreSQL 已成为默认且唯一运行后端，仍需完成真实环境平迁与回滚演练
- 真实工具调用循环仍以 mock 工具编排为主（RAG 检索已真实接入）
- token 仍为估算值（非 provider 官方 usage 回传）
- `trace/delta` 当前链路已稳定，后续仅做参数级调优（不影响 W2 已收口）
