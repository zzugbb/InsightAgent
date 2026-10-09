# 封板后的工具与页面专项检查

日期：2026-10-09。基于 `180ffdc` 后的维护修改，响应用户提出的 mock、仓库内容、登录文案、布局与 ID 五项检查。原本地收尾封板结论保留；部署、真实业务资料与用户签收仍在本次范围外。

## 结果与取舍

| 项目 | 检查与处理 |
| --- | --- |
| 工具 mock | `task_retrieve` 调用实际知识库检索，`calc_eval` 使用安全 AST 计算；`task_plan` 展示实际计划。remote 模型缺 Key/地址时不会悄悄替换成 mock。修复 `run_tool` 无条件读取故障标记的问题：`[tool-error]`、`[mock-tool-error]`、`[tool-fatal]`、`[mock-tool-fatal]` 在普通提示中不再注入失败。显式故障辅助函数仅供测试调用，runner 实际异常、重试和原有错误契约保留。 |
| 必要替身 | 明确选择的 mock 模型用于演示和离线验证；HTTP/Provider fixture、历史 `mock_plan` / `mock_retrieve` 名称兼容及旧异常类命名保留。它们不代表检索或计算是假结果。没有新增网页搜索工具。 |
| 仓库内容 | 检查开始时 488 个 tracked 文件：无真实 env、缓存、数据库、日志、构建结果或私钥文件，唯一二进制为 favicon；无大于 500 KB 的 tracked 文件。常见私钥/token 特征扫描无命中；指定 env/私钥/数据库路径的历史检查无记录。`.env.example`、锁文件、测试 fixture 与强制 tracked 实时计划应保留。没有据此删除文件。此结果不是完整历史或所有凭据类型的泄密审计。 |
| 登录文案 | 中英文改为描述对话、工具、知识与执行依据，删除协作/交付闭环和全程成本追踪等过度表述，明确费用估算；注册页标题随模式切换。手机收紧简介，平板标题不再受字符宽度限制。 |
| 工作台布局 | Trace 筛选换行，末项可见且可选；保持选中样式与语义。任务中心加宽抽屉与任务列、紧凑手机筛选，任务标题可进入详情；宽表格在容器内滚动。手机发送按钮移至右侧，修复被 Next 开发工具遮挡的问题。配置好的 remote 不再持续显示黄色配置警告，mock 和缺 Key 提示保留。 |
| ID | 任务详情的任务/会话 ID、运行调试会话 ID 使用缩略展示，复制获得完整值。会话名称优先于原始 UUID。配置输入、API/路由、导出、Trace 元数据及排障所需 ID 保留；知识库标识保留语义文本，并允许长值换行。 |

## 验证与证据

- 故障标记新增用例先复现失败（1 个测试、6 个子场景错误），修复后 `-k run_tool` **349/349**；工具 runner 的真实非致命异常继续传播。
- 后端门禁 **2/2 PASS**：full slice **2221/2221**、模块边界 **9/9**，来源 `/tmp/insightagent-ui-audit-backend.{log,md,json}`。API 指纹/SSE/Trace/export 契约保持兼容。
- 前端最终门禁 **4/4 PASS**：node **217/217**、lint **0 error / 2 个既有 warning**、Turbopack/webpack 双生产构建；最终标题 CSS 修改后单独重跑两种构建，来源 `/tmp/insightagent-ui-audit-final-build-{turbo,webpack}.log`；其余门禁来源 `/tmp/insightagent-ui-audit-frontend.{log,md,json}`。隔离副本只复制 tracked 源码与新增 ID 组件、克隆已有依赖，不复制私人环境，不影响运行中的开发构建；127 个前端应用/工具文件摘要（排除 README 和生成 next-env）见 `/tmp/insightagent-ui-audit-source.json`。
- Chromium Trace **2/2 PASS**（1440/390px，340px Inspector、筛选边界、末项选中及流程图）；原布局专项 **2/2 PASS**。首跑 Trace 手机发送被开发工具遮挡而失败，修复后复跑通过。来源 `/tmp/insightagent-ui-audit-trace.log` 与 `/tmp/insightagent-ui-audit-e2e.log`。Trace 用业务 API fixture；原布局专项使用独立本机测试账号，无真实供应商调用。
- Chrome 页面走查：登录/注册、工作台、任务中心、任务详情、运行调试/RAG、模型设置、用量、知识库治理与审计日志。390px 页面宽度保持 390；五个手机弹窗宽/scrollWidth 均 374，宽表格独立滚动。768px 登录页检查；桌面 1512px 走查。登录/工作台/手机视图无 Next 错误覆盖层，读取的控制台 error 为 0。完整任务 ID 复制核对通过，未改模型配置或知识库数据。
- 本机开发后端已安全重启加载修复；8000/3001 HTTP 200，原 Chroma reachable。未操作原 PostgreSQL/Chroma 容器/卷。真实 GLM 沿用原验收，不把 UI fixture 计作真实模型结果。
- 本轮 hygiene **4/4 PASS**，七份活跃/验收文档本地链接核对通过；来源 `/tmp/insightagent-ui-audit-hygiene.{log,md,json}`。截图位于 `/tmp/insightagent-{login-mobile,workbench-desktop,task-center,task-center-mobile,task-identifiers,trace-mobile}-after.png`，不是 tracked 业务资料。

## 边界与后续

先前真实模型规划回退、自然语言执行声明与账单口径风险仍保留。当前修改只关闭这五项检查中的可复现问题，不代表所有页面/所有数据长度已穷尽验证。

旧后端 `pilot-42ccf1f` / 前端 `pilot-9e78810` 只保留原联调证据，未包含本轮后端与前端修改。本轮未重建镜像，不能把旧配对说成与当前源码一致。未来部署前需重新构建配对、核对摘要并执行联调。

本轮本地提交后尚未推送，不能沿用此前绿色 CI 作为本轮远端验证。写入工具并行和 HTTP/DAG checkpoint 继续延期；不新增功能主线。
