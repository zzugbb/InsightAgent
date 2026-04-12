# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand 的 Agent 工作台前端。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3/W4：未开始（真实工具 / RAG）

## 当前已有内容

- 三栏布局：会话、消息、轨迹/上下文
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
- usage 展示：支持当前任务、任务列表摘要；汇总由后端 `GET /api/tasks/usage/summary` 驱动（全局/会话自动切换），并具备 loading/error/empty 状态与统计覆盖率展示
- Memory：状态展示 + add/query 调试（含 metadata）
- 设置：主题、主题色、语言、模型与运行模式
- 工程校验：已配置 `.eslintrc.json`，`npm run lint` 可直接运行且当前告警已清零

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/types/trace.ts`：前端 TraceStep 类型
- `lib/api-client.ts`：REST 请求封装

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

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端（未设置时使用 `http://127.0.0.1:8000`）。

## 下一步（W3/W4）

- 配合后端接入真实工具/RAG 后补齐流程图语义
- 将当前 mock `tool_start/tool_end` 升级为真实工具执行与失败重试可视化
- 继续完善 usage/token/cost 的统计维度（跨会话/时间段聚合）
- 持续优化流式回放体验（参数级调优与性能提升）
- 继续做不阻塞主链路的可访问性与交互细化
