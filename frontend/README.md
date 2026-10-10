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

公开案例展示由独立[showcase/](../showcase/README.md)承担，已实现首页、两个固定案例、时间线/流程图和节点详情；静态回放无需登录或后端。首页按四段组织，系统分层与执行流程直接展示，支持节点职责；执行图进入视野播放一次，可暂停、重播和复位；案例进入或主动切换后自动回放一次，查看节点即暂停；提示观察重点，流程图可明确查看全图。减少动态效果时手动播放。原工作台运行契约不变，范围见[展示说明](../docs/showcase.md)，本地结果见[验收基线](../docs/acceptance.md#公开项目展示)。当前尚未公开发布。

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

工作台组件位于 `app/components/workbench/`，主入口如下；辅助逻辑与对应组件放在同一主题目录。

| 职责 | 入口 |
| --- | --- |
| 主编排、消息与会话导航 | `index.tsx`、`chat-column.tsx`、`sidebar.tsx`、`sidebar-settings-menu.tsx` |
| 轨迹、上下文与流程图 | `inspector.tsx`、`trace-flow-view.tsx`、`utils.ts` |
| 模型设置、用量与审计 | `model-settings-modal.tsx`、`usage-dashboard-modal.tsx`、`audit-logs-modal.tsx` |
| 知识库治理、导入与调试 | `knowledge-base-governance-modal.tsx`、`knowledge-import-modal.tsx`、`runtime-debug-modal.tsx` |
| 任务详情、分支与步骤恢复 | `app/tasks/[taskId]/` 下的 `page.tsx`、`task-rerun-panel.tsx`、`task-checkpoint-panel.tsx` |
| 流状态与结果合并 | `lib/stores/chat-stream-store.ts`、`lib/stores/chat-stream-store-utils.ts` |
| 请求、认证与 Trace 类型 | `lib/api-client.ts`、`lib/types/trace.ts` |

## SSE 消费与稳定契约

前端按 `step_id` 合并工具事件，允许并发交错；Trace 与 REST 记录同构。完整事件和字段见[运行时契约](../docs/runtime-contracts.md#ssetrace-与导出)。

Workbench 拉取 `trace/delta`，失败退避并在流结束后补拉，同步健康度显示在 Context。刷新或切换会话会接管已有活动任务；轮询发现失败状态时仍保留 SSE 的具体错误。

状态与筛选使用服务端归一化字段；流程图分别展示记录顺序与声明依赖。回答结束提示按最新 `seq` 和白名单原因显示，规则见[回答完整性](../docs/runtime-contracts.md#历史与页面completion)。

输入法组合中的 Enter 保留给输入法，普通 Enter 发送、Shift+Enter 换行。窄屏筛选换行、宽表格在容器内滚动；必要 ID 缩略显示，可查看/复制完整值，路由、配置与导出保留完整标识。详见[运行时契约](../docs/runtime-contracts.md)，页面复核范围见[验证基线](../docs/acceptance.md#验证基线)。

登录表单最大宽度 420px，桌面和手机分别调整比例、间距，并支持深浅主题。模型设置、知识库治理和用量弹窗限制在视口内，标题与模型保存操作保持可见，长内容在弹窗内部滚动。高级工具配置、诊断、治理筛选、趋势和排行可展开；Trace 空状态提供任务中心入口，有记录后显示筛选与计数。公共布局样式位于 `app/styles/workbench-dialogs.css`，隔离布局回归位于 `e2e/workbench-presentation.spec.ts`。

## Memory / RAG

- Memory 的 status/add/query 为会话级手工调试入口；数据存储和知识库隔离见[架构说明](../docs/architecture.md)。
- 普通入口“设置 → 知识库 → 导入知识”支持 UTF-8 TXT/Markdown，预览后使用后台任务；同名文件归入同文档并保留版本，结果不确定时重试原载荷/幂等键。
- 关闭弹窗停止前端轮询，已受理的后台任务继续执行；重新打开读回状态与确认进度。失败需复核已写入内容。
- 检索测试带入目标库，展示来源、版本、distance 与召回摘要；这些字段辅助复核，不等于答案质量评分。

接口与预算见[后台导入](../docs/rag-background-ingest.md)和[后端接口范围](../backend/README.md#http-接口范围)。

## 安全与设置

API Key 仅在组件草稿中暂存，通过鉴权请求提交，保存后清空。模型设置操作见[配置指南](../docs/configuration.md)；access / refresh token 当前使用 localStorage，保护要求见[安全政策](../SECURITY.md)。

前端继续消费服务端统一 preview/output/result-summary，避免为不同 Provider 派生独立结果语义。对话、Trace 与导出可能包含用户业务内容，分享前按资料访问权限检查。

## 验证与维护

```bash
npm --prefix frontend run lint
bash scripts/ci_run_release_gate.sh --phase frontend
# 在 frontend/ 下、按运行手册准备服务/权限后执行
npm run test:e2e
npm run test:e2e:smoke:matrix
```

门禁包含 Node tests、lint、Turbopack 与 webpack 双生产构建；浏览器 fixture 和真实业务路径分开统计。源码基线、检查结果与已知 warning 统一见[验证基线](../docs/acceptance.md#验证基线)。

Next.js / React / ESLint 精确版本见 [package.json](package.json) 与锁文件；依赖升级需检查上游兼容性。

开发遵循[维护规则](../AGENTS.md)与[贡献指南](../CONTRIBUTING.md)，按影响更新专题契约与验证基线。
