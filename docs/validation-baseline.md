# 当前验证基线

更新：2026-10-09。区分应用实现、本地替身、真实供应商、镜像、CI 与外部验收；临时日志可能不存在，以本文件和专项验收的持久结论为依据。

## 本轮配置与文档维护

基于 `103ea1f` 的干净工作区开展，只修改数据库定位摘要脱敏、开发 Compose loopback 定义与文档，不改前端应用、模型配置、数据库记录或已有容器。

| 检查 | 结果 / 范围 |
| --- | --- |
| 数据库摘要回归 | 新增 3/3；原实现 2 个失败 / 1 个错误，修复后通过。覆盖 query/fragment 秘密、非法 authority 和 IPv6。 |
| 后端门禁 | 2/2 PASS：full slice 2224/2224、模块边界 9/9；含 OpenAPI 指纹。 |
| 试点静态自测 | 预检 5/5、Compose 入口 7/7；不启动容器、不请求真实模型。 |
| 普通故障标记 | 1/1 回归通过，四个标记在 attempt 0/1 都使用真实计算 runner；此前 run_tool 349/349 基线保留。 |
| 当前页面 | Chrome 本机开发页，390×900：登录/注册标题切换、任务中心→新标签页详情、缩略ID及两个复制入口、Failure末项点击选中；页面scrollWidth=390、错误覆盖层/控制台error均0。复制内容和完整e2e沿用下方基线。 |
| 本机健康 | 8000 / 3001 HTTP 200、Chroma reachable；本轮不重启开发服务，不改变既有数据。 |
| tooling / hygiene | 1/1、4/4 PASS；tooling 首跑受沙箱 `/dev/fd` 限制，同命令提权复跑通过。 |
| 文档与仓库 | 37 份 Markdown、216 个本地链接通过检查；常见密钥特征扫描无命中，无不应跟踪的运行产物；原始计划 SHA256 未变。特征扫描不等于完整历史安全审计。 |

来源：`/tmp/insightagent-docs-security-red.log`、`/tmp/insightagent-docs-backend.{log,md,json}`、`/tmp/insightagent-docs-tooling.{md,json}`、`/tmp/insightagent-docs-tooling-retry.log`、`/tmp/insightagent-docs-hygiene.{log,md,json}`、`/tmp/insightagent-docs-check.json`。本轮 Compose 定义未应用到已有容器，后端摘要修复需在后续正常重启时加载；不把旧镜像或运行实例视为新源码验证。

## 沿用的应用与浏览器基线

| 验证 | 已完成范围 | 来源 |
| --- | --- | --- |
| 前端门禁 | 应用 `103ea1f`：Node 217/217，lint 0 error / 2 既有 warning，Turbopack/webpack 双生产构建 | `/tmp/insightagent-ui-audit-frontend.{log,md,json}`；最终标题 CSS 双构建 `insightagent-ui-audit-final-build-{turbo,webpack}.log` |
| 页面专项 | Chromium Trace 1440/390px 2/2，原布局 2/2；Chrome 登录/工作台/任务/治理页面走查，完整 ID 复制核对 | [五项专项检查](post-seal-usability-audit.md) |
| 本机键盘 | 三浏览器桌面/手机 6/6；不是操作系统输入法全面验收 | [运行手册](development-runbook.md) |
| 收尾工具 | tooling 1/1、RAG 静态 17/17、隔离 RAG 1/1、规划恢复 5/5、导出静态 1/1、drill 自测 | [收尾审计](project-completion-audit.md) |

本轮未改前端应用、未重跑完整前端构建或全部浏览器 e2e；原源码基线与测试范围保留，不能写成这些检查在本轮全部重新执行。

## 真实模型、镜像与 CI

- 真实 GLM 原四场景 3/4 完整通过，独立编辑分支恢复 1/1；同会话续算回答正确但规划回退未实际调用要求的计算工具。五项均 completed，不等于用户目标 5/5。详见[真实模型验收](real-model-acceptance.md)。
- 历史镜像 `pilot-42ccf1f` / `pilot-9e78810` 未包含 `103ea1f` 和本轮脱敏修改；既有联调/持久化是本地替身结果。未来发布须重建配对，范围见[镜像证据](pilot-image-evidence.md)。
- 已推送基线 `1b850bc` 的 CI 绿由用户确认，本轮未读取 run/artifact。后续本地提交尚未推送，不能沿用旧 CI 作为新提交的远端验证。
- 本地开发与工程收尾已封板；真实业务资料、用户签收、目标 HTTPS/部署/升级回滚及存储恢复按用户决策延期，外部试点/生产就绪未验收。配置检查 PASS 不改变这一结论。

写入工具并行与 HTTP/DAG checkpoint 继续延期；ESLint 10 等上游兼容后再评估。本轮没有新增真实模型请求、镜像重建、部署、数据清理或 Git 推送。
