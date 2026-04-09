# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand 的 W1 聊天工作台。

## 当前已有内容

- 工程：`package.json`、`tsconfig.json`、`next.config.ts`、`app/layout.tsx`（含 `metadata` 与站点图标路径）
- 样式与资源：`app/globals.css`、`app/icon.svg`、`public/favicon.ico`（ICO 可由 `scripts/generate-favicon-ico.py` 再生）
- `app/components/workbench/`：侧栏、对话区、右侧检查器（Inspector）、`trace-flow-view.tsx`（@xyflow 线性轨迹图）、品牌 Logo 组件、运行设置菜单与模型弹窗
- `lib/stores/chat-stream-store.ts`：Task Stream / trace 状态
- `lib/sse/parse.ts`：SSE 分块解析
- `lib/api-client.ts`：含 `apiPatchJson` 等与后端对接
- `lib/storage-keys.ts`：侧栏 / 右栏宽度与折叠状态等 localStorage 键
- `lib/i18n/`：中英文文案集中管理

## 当前边界（功能）

- 主流程通过 `useChatStreamStore` 使用 `POST /api/tasks` + `GET /api/tasks/{task_id}/stream`
- **布局**：左侧最近会话、中间消息流、右侧「轨迹 / 上下文」；左下角「设置」（主题 / **主题色（含自定义色）** / 语言 / 模型与运行）
- **桌面宽屏**：左栏、右栏均支持 **拖拽调宽**、**折叠为窄条**（宽度与折叠状态持久化）；折叠/展开图标与 Lucide **Panel*Open / Panel*Close** 系一致
- **会话**：列表、切换、`POST /api/sessions` 创建；**重命名**（`PATCH`）、**删除**；无选中会话时发送会先创建会话再跑任务流
- **轨迹**：`GET .../trace` 回放、`.../trace/delta` 增量；默认仅展示最近若干步，可展开全部；流式失败提示与 **aria-live** 摘要
- **数据请求**：TanStack Query；流式结束后按需 invalidate
- **Markdown**：`react-markdown` + GFM + sanitize；数学/高亮等按组件配置
- **窄屏**：左侧会话抽屉 + 右侧轨迹抽屉，遮罩与 **焦点陷阱**、Esc 关闭
- **列表性能**：消息约 24+ 条虚拟列表；侧栏会话约 14+ 条虚拟化
- **无障碍**：⌘K / Ctrl+K 聚焦输入框；错误映射 `lib/errors.ts`
- **轨迹可视化（W2 起步）**：右侧「轨迹」面板支持 **时间线 / 流程图**（`@xyflow/react`，当前为按步骤顺序的只读线性图，随主题亮/暗切换）

## 下一步

与仓库根目录 `README.md` 一致：扩展 **Flow 节点**（自定义类型、折叠详情）、Memory / Chroma 接入前的契约与 UI 占位。