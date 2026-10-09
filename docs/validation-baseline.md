# 验证基线与当前状态

更新：2026-10-09。本地实现与工程收尾完成，现阶段按可复现问题维护；部署、真实业务资料和目标用户签收按维护者决定延期。写入工具并行、HTTP/DAG checkpoint 和 ESLint 10 不属于当前收尾。外部试点/生产就绪尚未验收，没有经确认必须新增的功能主线。

## 源码与验证范围

| 范围 | 已完成结果 | 来源 |
| --- | --- | --- |
| 后端 `bc1346f` | full slice 2224/2224、模块 9/9，含 OpenAPI 指纹；摘要脱敏新增 3/3 | `/tmp/insightagent-docs-backend.{log,md,json}`、`insightagent-docs-security-red.log` |
| 静态运维与工具 | 预检 5/5、Compose 7/7、普通故障标记 1/1；tooling 1/1、hygiene 4/4 | `/tmp/insightagent-docs-tooling.{md,json}`、`insightagent-docs-tooling-retry.log`、`insightagent-docs-hygiene.{log,md,json}` |
| 前端应用 `103ea1f` | node 217/217、lint 0 error / 2 既有 warning、Turbopack/webpack 双构建 | `/tmp/insightagent-ui-audit-frontend.{log,md,json}`、`insightagent-ui-audit-final-build-{turbo,webpack}.log` |
| 浏览器 `103ea1f` | Chromium Trace 1440/390px 2/2、原布局 2/2；Chrome 登录/工作台/任务/治理、完整 ID 复制；Mac 键盘三浏览器/两尺寸 6/6 | `/tmp/insightagent-ui-audit-{trace,e2e}.log`；运行命令见[手册](development-runbook.md) |
| 页面只读复核 `bc1346f` | Chrome 390×900：登录/注册、任务中心→详情、Failure 筛选；无页面横向溢出，覆盖层/console error 0；两个 ID 复制入口可见 | 本机开发页；复制内容与完整 e2e 沿用上一行 |
| 隔离验收工具 | RAG 静态 17/17、独立 PostgreSQL/Chroma 1/1，规划等待/取消/迟到结果/重跑 5/5，导出静态 1/1 与 drill 自测 | `/tmp/insightagent-oct09-{rag-static,rag-postgres,planning-postgres}.log`、`insightagent-finalcheck-*` |
| 真实 GLM | 原四场景 3/4 完整通过，编辑表达式的独立分支恢复 1/1；原续算回退未实际调用计算工具 | [真实模型验收](real-model-acceptance.md) |

tooling 首跑受沙箱 `/dev/fd` 限制，同命令提权复跑通过。后端定位摘要修复与开发 Compose loopback 定义已落源码；`bc1346f` 检查时未重启服务/容器，不能把运行实例视为已加载这些修改。端口 8000/3001 当时 HTTP 200、Chroma reachable。

## 工具与页面维护结论

- 检索调用真实 Chroma，计算使用 AST 白名单，HTTP 工具按显式配置执行；remote 缺连接值明确失败。canonical mock、协议 fixture 和历史名称兼容属于必要演示/测试路径，不是实际工具假结果。
- 普通 prompt 的测试故障标记已不影响生产 runner；登录中英文改为实际能力与估算费用，窄屏筛选、任务抽屉、发送按钮和长 ID 展示已修复。完整标识仍保留在 API/路由/导出和排障元数据中。
- 已检查跟踪文件，无真实 env、数据库、缓存、构建结果、日志或私钥产物；常见秘密特征扫描无命中，不等于完整 Git 历史或所有凭据类型已审计。`data/insightagent.plan.back.md` SHA256 保持 `5f6f79c4c7faf8a3becad7e6d7805fd86304425a2319b2702730fd4a54e4525d`。

## 镜像、CI 与外部验收

- 历史配对 `pilot-42ccf1f` / `pilot-9e78810` 未包含 `103ea1f` 页面/工具维护与 `bc1346f` 摘要修复。旧 `0209651` / `218f94d` 配对有 ARM64 构建、禁网 384 维 embedding、生产 PostgreSQL/Chroma、SSE/Trace/导出、恢复/取消及 Agent HTTP 协议 7/7 证据；旧 `218f94d` 配对隔离 Compose 重建后数据保留通过。均为本地模型替身，最新镜像未重建。历史摘要/配方来源可从 `65f1fde` 与 `bc1346f` 的 Git 文档查询，不沿用旧 tag 直接发布。
- 已推送基线 `1b850bc` 的 CI 绿由维护者确认，后续本地维护没有据此获得新的远端验证。提交是否推送、当前 CI 和运行健康应实时查询，不从本文历史状态推断。
- 真实业务引用/冲突版本/无依据回答、目标任务签收与供应商账单按[验收指南](acceptance.md)另行核对；HTTPS/访问边界、升级回滚、双存储恢复、RPO/RTO 与责任人按[部署指南](pilot-deployment-preflight.md)实测。配置 PASS 不改变未验收结论。

## 文档清理验证

本次仅清理文档，不改运行代码、前端、模型设置或数据，不新增供应商调用、服务重启、镜像构建和部署；不重跑完整应用门禁，沿用上表源码基线。删除实时计划及7份重复过程文档，必要操作和验收规则合并保留。30份Markdown、187个本地链接、README接口清单51/51通过，已删除文档引用为0；原始计划摘要未变，常见秘密特征扫描无命中，hygiene 4/4。来源 `/tmp/insightagent-docs-cleanup-check.json` 与 `/tmp/insightagent-docs-cleanup-hygiene.{log,md,json}`。
