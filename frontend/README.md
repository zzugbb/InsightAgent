# InsightAgent Frontend

Next.js 工作台把会话、回答和执行证据关联展示。前端负责交互、实时状态与历史回放，工具结果和任务终态以服务端记录为准。

[项目概览](../README.md) · [架构](../docs/architecture.md) · [配置](../docs/configuration.md) · [契约](../docs/runtime-contracts.md)

## 本地运行

使用 Node.js 24+，在项目根目录执行：

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

开发地址为 `http://127.0.0.1:3001`；后端默认 `http://127.0.0.1:8000`。`NEXT_PUBLIC_API_BASE_URL` 由浏览器使用，生产构建时写入 bundle，部署后仅修改容器环境不能替换旧地址。此变量必须是公开地址，不能放 Key 或带凭据 URL。生产 standalone 配方见 [Dockerfile.pilot](Dockerfile.pilot) 与[部署指南](../docs/pilot-deployment-preflight.md)。

已有服务先核对端口与健康状态，避免重复启动；一键启动脚本的重启行为与 Docker 权限见[运行手册](../docs/development-runbook.md)。

## 页面与能力

| 页面 / 入口 | 职责 |
| --- | --- |
| 登录 / 注册 | 中英文身份入口、登录态检查与 refresh 轮换；界面描述实际对话、工具和知识能力。 |
| Workbench | 会话列表、Markdown/公式回答、流式发送与取消、queued/running 接管。 |
| Trace / Context Inspector | 时间线与流程图、工具公开结果、依赖与并发关系、同步诊断与用量。 |
| 任务中心 / 详情 | 搜索、状态与失败筛选、来源往返、历史回放、任务导出与分支重跑。 |
| 知识库 | 文件预览与后台导入、来源/文档版本、共享权限、检索测试和治理。 |
| 运行调试 | Memory 与 RAG 的状态、手工写入及检索，不等于自动长期记忆链。 |
| 模型设置 / 用量 / 审计 | remote 配置校验、工具来源诊断、队列压力、用量趋势和失败审计。 |

任务详情 `/tasks/[taskId]` 支持 `trace_semantic` 参数直达语义筛选。分支重跑可编辑输入并创建独立会话；“从步骤继续”标为实验功能，只支持有快照的内建顺序计划，复用结果与新执行分开显示。

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、会话导出入口与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：模型设置、审计、用量统计、知识库治理与当前用户信息入口
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/usage-dashboard-modal.tsx`：用量仪表盘
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx` / `audit-logs-modal-utils.ts`：审计日志筛选、服务端 keyword URL、分页、失败详情可读化、展开与导出
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库治理与导入/检索入口
- `app/components/workbench/knowledge-import-modal.tsx` / `knowledge-import-utils.ts`：UTF-8 文件校验、预览与既有后台导入任务衔接
- `app/components/workbench/runtime-debug-modal.tsx` / `runtime-debug-memory-section.tsx`：RAG 调试编排与按会话重建的 Memory 调试区
- `app/tasks/[taskId]/page.tsx`：任务详情页与任务导出入口
- `app/tasks/[taskId]/task-checkpoint-panel.tsx`：实验性起点选择、成功前缀说明、失败同键重试与独立会话接管
- `app/tasks/[taskId]/task-rerun-panel.tsx`：独立任务分支、输入编辑、同键重试、来源分页与 Workbench 会话接管
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/stores/chat-stream-store-utils.ts`：tool_end / tool meta 合并、preview/output/result-summary 归一化
- `app/components/workbench/utils.ts`：trace display、tool result preview、follow-up 展示与搜索辅助
- `app/components/workbench/model-settings-modal-utils.ts`：settings 预览、provider/source/tool registry diagnostics 与 task queue diagnostics 说明
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期
- `lib/types/trace.ts`：前端 TraceStep 类型

## SSE 消费与稳定契约

事件为 `start / state / trace / tool_start / tool_end / heartbeat / token / cancelled / timeout / done / error`。trace 的 step 与服务端 REST 同构，tool 事件按 step_id 合并；允许并发事件交错，不依赖单一运行工具假设。

Workbench 静默拉取 `trace/delta`，失败退避并在流结束后补拉；同步健康度显示在 Context。failed 状态轮询不提前截断仍活动的 SSE，具体错误优先保留；流关闭后必要时补拉既有任务/Trace。刷新与会话切换接管已有 queued/pending/running，不创建重复任务。

状态/轮询使用 normalized 状态，失败摘要优先显式 hint/source；本地筛选和处置提示不改写服务端状态。流程图虚线仅为记录顺序，实线仅为声明依赖/决策来源；缺少历史字段不推断。回答结束提示消费白名单原因及最新 seq，completed 不代表目标全部满足。

输入法组合中的 Enter 保留给输入法，普通 Enter 发送、Shift+Enter 换行。窄屏筛选换行、宽表格在容器内滚动；必要 ID 缩略显示，可查看/复制完整值，路由、配置与导出保留完整标识。详见[运行时契约](../docs/runtime-contracts.md)，页面复核范围见[验证基线](../docs/validation-baseline.md)。

## Memory / RAG

- Memory：会话 collection `memory_{session_id}`；status/add/query 为手工调试入口。完整历史在 PostgreSQL。
- RAG：知识库 collection `kb_{user_hash}_{knowledge_base_id}`，默认 ID 为 `default`；`shared-*` 写入由管理员权限控制。
- 普通入口“设置 → 知识库 → 导入知识”支持 UTF-8 TXT/Markdown，预览后使用后台任务；同名文件归入同文档并保留版本，结果不确定时重试原载荷/幂等键。
- 关闭弹窗停止前端轮询，已受理的后台任务继续执行；重新打开读回状态与确认进度。失败需复核已写入内容。
- 检索测试带入目标库，展示来源、版本、distance 与召回摘要；这些字段辅助复核，不等于答案质量评分。

接口与预算见[后台导入](../docs/rag-background-ingest.md)和[后端接口范围](../backend/README.md#http-接口范围)。

## 安全与设置

API Key 输入仅存于组件草稿，通过鉴权请求发给后端；摘要不返回 Key，保存后清空输入。access / refresh token 当前保存在浏览器 localStorage，不是 HttpOnly Cookie；部署须控制访问边界并保护同源脚本，详见[安全政策](../SECURITY.md)。

前端继续消费服务端统一 preview/output/result-summary，避免为不同 Provider 派生独立结果语义。对话、Trace 与导出可能包含用户业务内容，分享前按资料访问权限检查。

## 验证与维护

```bash
npm --prefix frontend run lint
bash scripts/ci_run_release_gate.sh --phase frontend
# 在 frontend/ 下、按运行手册准备服务/权限后执行
npm run test:e2e
npm run test:e2e:smoke:matrix
```

门禁包含 Node tests、lint、Turbopack 与 webpack 双生产构建；浏览器 fixture 和真实业务路径分开统计。当前文档维护未改前端应用，沿用既有应用验证；源码、计数、桌面/手机检查与已知 warning 统一见[验证基线](../docs/validation-baseline.md)。

本地收尾已封板，部署、真实资料与用户签收延期；当前按实际问题维护。Next.js / React / ESLint 精确版本见 [package.json](package.json) 与锁文件；ESLint 10 等上游兼容后再评估。写入工具并行、HTTP/DAG checkpoint 不在本轮范围。

开发后同步三个 README 与受影响专题，验证集中在验证基线；保留长期实现/契约参考，不再维护开发实时计划。原始完整备份计划永远只读。
