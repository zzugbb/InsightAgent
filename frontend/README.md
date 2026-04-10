# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand 的 W1 聊天工作台。

## 当前已有内容

- 工程：`package.json`、`tsconfig.json`、`next.config.ts`、`app/layout.tsx`（含 `metadata` 与站点图标路径）
- 样式与资源：`app/globals.css`、`app/icon.svg`、`public/favicon.ico`（ICO 可由 `scripts/generate-favicon-ico.py` 再生）
- `app/components/workbench/`：侧栏、对话区、右侧检查器（Inspector）、`trace-flow-view.tsx`（@xyflow 自定义 `traceStep` 节点：按 thought/action/observation 配色、元信息行、`<details>` 内容摘要）、品牌 Logo 组件、运行设置菜单与模型弹窗
- `lib/stores/chat-stream-store.ts`：Task Stream / trace 状态
- `lib/sse/parse.ts`：SSE 分块解析
- `lib/api-client.ts`：含 `apiPatchJson` 等与后端对接
- `lib/storage-keys.ts`：侧栏 / 右栏宽度与折叠状态等 localStorage 键
- `lib/i18n/`：中英文文案集中管理

## 当前边界（功能）

- 主流程通过 `useChatStreamStore` 使用 `POST /api/tasks` + `GET /api/tasks/{task_id}/stream`
- **布局**：左侧最近会话、中间消息流、右侧「轨迹 / 上下文」；左下角「设置」（主题 / **主题色（含自定义色）** / 语言 / 模型与运行）
- **桌面宽屏**：左栏、右栏均支持 **拖拽调宽**、**折叠为窄条**（宽度与折叠状态持久化）；折叠/展开图标与 Lucide **Panel*Open / Panel*Close** 系一致
- **会话**：列表（**分页加载更多**，`useInfiniteQuery` + `has_more`）、切换、`POST /api/sessions` 创建；**重命名**（`PATCH`）、**删除**；无选中会话时发送会先创建会话再跑任务流
- **轨迹**：`GET .../trace` 回放、`.../trace/delta` 增量；默认仅展示最近若干步，可展开全部；流式失败提示与 **aria-live** 摘要
- **数据请求**：TanStack Query；**`GET /api/tasks`** 使用 **`useInfiniteQuery`**（本会话 **12** 条/页、全局 **8** 条/页）+ **`has_more`**；Inspector 任务列表支持 **加载更多**；流式结束后按需 invalidate（含 **`session-memory-status`**）
- **Markdown**：`react-markdown` + GFM + sanitize；数学/高亮等按组件配置
- **窄屏**：左侧会话抽屉 + 右侧轨迹抽屉，遮罩与 **焦点陷阱**、Esc 关闭
- **列表性能**：消息约 24+ 条虚拟列表；侧栏会话约 14+ 条虚拟化
- **无障碍**：⌘K / Ctrl+K 聚焦输入框；错误映射 `lib/errors.ts`
- **轨迹可视化（W2 起步）**：右侧「轨迹」面板支持 **时间线 / 流程图**；**时间线** 每条 `trace-card` 与流程图一致按 **`meta.tool` / `meta.rag` 与 type** 映射为 **工具 / RAG / 思考 / 行动 / 观察** 的左侧色条（`data-trace-kind`）；**流程图**（`@xyflow/react`）为 `smoothstep` 边、自定义节点徽章与折叠内容；随主题亮/暗切换）
- **上下文 · Memory**：说明文案 + **实时状态**（`GET .../memory/status`）+ **调试区**：`POST .../memory/add`（可选 **metadata** JSON）/ `.../memory/query`（选中会话后可用；写入成功会 toast 并刷新条数）

## 进度与里程碑

**里程碑 2** 已达成交付（可观测轨迹 + Memory 调试 + 本会话任务列表等），详见仓库 **[`docs/DEVELOPMENT_PLAN.md`](../docs/DEVELOPMENT_PLAN.md)**。

消费 SSE 时请与 **[`docs/SSE_AND_TRACE_CONTRACT.md`](../docs/SSE_AND_TRACE_CONTRACT.md)** 及 `lib/types/trace.ts` 对齐；`dispatchSseEvent`（`lib/stores/chat-stream-store.ts`）为当前权威解析逻辑。Memory 与 Chroma 行为见 **[`docs/MEMORY_CHROMADB.md`](../docs/MEMORY_CHROMADB.md)**。

## 下一步（W2 收尾）

与根目录 `README.md` 及 `docs/DEVELOPMENT_PLAN.md` 一致：真实工具/RAG、OpenAPI 示例等；前端侧可继续按不阻塞主链路做交互与可访问性小优化。