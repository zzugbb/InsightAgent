# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 → 任务执行 → 轨迹解释 → Memory/RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前开发进度（按完整计划对齐）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| W1 主链路 | 已完成 | 会话/任务/消息持久化、SSE 流、trace 回放与 delta、前端工作台闭环 |
| W2 可观测 + Memory 最小闭环 | 已完成（已收口） | 轨迹时间线+流程图、TraceStep 契约、Chroma 会话 memory 状态/写入/检索、`trace/delta` 流式阶段增量持久化（`seq` 递增） |
| W3 Tool + ReAct | 已完成（mock 范围） | mock 工具调用循环、可恢复重试/致命失败语义、SSE/Trace 对齐 |
| W4 RAG + 成本展示 | 进行中 | 真实 RAG ingest/检索、token/cost UI 细化 |
| 阶段 5+ 产品化 | 未开始 | PG、多用户鉴权、治理、测试与运维 |

当前默认策略：`mock` 模式优先，先稳定主链路契约与可视化，再切真实 API。

## 当前能力摘要

- backend：
  - `POST /api/tasks`、`GET /api/tasks/{task_id}/stream`、`GET /api/tasks/{task_id}/trace`、`GET /api/tasks/{task_id}/trace/delta`
  - `trace/delta` 支持 `limit` 参数控制单次增量返回量（默认 200，最大 500）
  - 流式阶段会按批次持久化最终 `observation`（默认每 8 个 token chunk 一次，并在结束时兜底），`trace/delta?after_seq=` 可持续拉取增量
  - 前端在 `trace/delta` 返回 `has_more=true` 时会快速连续拉取，优先清空积压增量
  - `GET /api/tasks` 支持 `limit/offset` 与可选 `session_id` 过滤，响应含 `total/has_more`
  - 任务相关响应补充状态派生字段：`status_normalized`、`status_label`、`status_rank`（向后兼容）
  - `GET /api/tasks/usage/summary` 支持全局与按 `session_id` 的 usage 聚合
  - 会话接口支持创建/列表/详情/消息/重命名/删除
  - 设置接口支持读取/保存/校验：`GET /api/settings`、`PUT /api/settings`、`POST /api/settings/validate`
  - `GET /api/sessions/{session_id}/usage/summary` 兼容保留（会话聚合）
  - Memory：`GET .../memory/status`、`POST .../memory/add`、`POST .../memory/query`
  - `/health` 含 Chroma 可达性
- frontend：
  - 三栏工作台（会话 / 消息 / 轨迹与上下文）
  - 右侧 Inspector（Context）完成信息架构优化：概览 KPI + 同步诊断 + 用量统计 + Memory + 任务索引分区，弱化堆叠卡片并保留扩展位
  - 任务索引支持前端本地筛选与排序（状态筛选、时间顺序、失败任务优先），便于运行态排障
  - 任务索引支持关键词快速定位（标题/ID）与失败摘要提示，便于快速定位异常任务
  - Trace 面板支持步骤类型筛选、关键词检索与类型计数（时间线/流程图一致生效），提升长轨迹排障效率
  - 右侧面板完成一体化收口优化：Trace 密度切换、Context 快速跳转、状态徽标与分区说明统一，兼顾当前能力与后续扩展
  - 左侧与中栏完成统一风格优化：会话导航强化激活层级、聊天头部运行态信息条收敛、消息与输入区交互节奏统一
  - 根据最新交互收敛要求，已移除会话状态胶囊与输入计数提示，头部恢复紧凑模式标签展示
  - 轨迹支持「时间线 / 流程图」双视图（thought/action/observation/tool/rag 区分）
  - 会话支持分页加载、重命名、删除
  - Context 面板支持 Memory 状态展示、add/query 调试
  - usage 展示增强：支持全局/会话自动切换汇总，含加载/错误/空状态与覆盖率（with_usage/total）
  - `trace/delta` 支持流式期间自动轮询同步（静默）+ 失败退避重试，并在流结束后自动补拉一次
  - 任务 SSE 支持运行中重连：`GET /api/tasks/{task_id}/stream` 在 `running` 状态下可重连并回补增量
  - Inspector 上下文摘要新增 delta 同步健康度（状态/重试次数/最近成功时间/下次重试/最近错误/恢复提示），恢复提示为短时展示并自动消退；重试中展示秒级倒计时
  - 页面处于后台（不可见）时暂停 delta 自动同步，回到前台自动恢复
  - Inspector 在 delta 连续失败时提供轻量告警提示（不阻塞主链路）
  - 前端 ESLint 基线已落地，`npm run lint` 可直接执行且当前告警已清零
  - W3 增量：mock 工具链路支持可复现错误语义（`[mock-tool-error]` 可恢复重试、`[mock-tool-fatal]` 致命失败），`tool_end` / `error` / `trace.meta.tool` 已携带 `retry_count/error`
  - W3 优化：新增本地计算器工具（`[calc:1+2*3]` 或“计算 1+2*3”），统一走 `tool_start/tool_end/trace` 生命周期
  - W1 优化：设置弹窗支持“校验配置”按钮（调用 `POST /api/settings/validate`，校验通过后再保存）
  - W1 稳定性优化：`PUT /api/settings` 与 `POST /api/settings/validate` 在 `remote` 模式下支持沿用已存储的 `api_key`（前端留空不再误清空）
  - W2 稳定性优化：前端合并 SSE/`trace/delta` 步骤后按 `seq` 稳定排序，降低时间线/流程图在高频增量场景下的乱序概率
  - W2 稳定性优化：`trace/delta` 增加任务隔离保护，旧任务延迟返回不再污染当前任务轨迹
  - W3 稳定性优化：前端仅在 `error.fatal=true` 时将全局 phase 置为 `error`；可重试工具错误不再误伤主任务状态
  - W1/W2 稳定性优化：SSE 流式期间改为周期 heartbeat，且后端 trace 持久化增加节流，降低连接误判与 SQLite 写放大
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
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 嵌入策略：当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- 错误语义：
  - Chroma 不可达时，`memory/add` 与 `memory/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

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

## 下一步（W4+）

- 真实工具调用与错误/重试语义（生产化，从当前 mock 语义升级）
- 真实 RAG ingest/检索（W4）
- `trace/delta` 流式增量持久化与前端自动同步优化链路已完成收口
- usage / token / cost 展示继续完善（如跨会话历史趋势）
