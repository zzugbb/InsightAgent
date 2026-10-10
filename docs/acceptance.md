# 验收指南

本文记录本机工程、真实模型、业务任务与部署的验证范围，并提供复验入口。结论与证据分开阅读，模型替身、真实模型及目标环境结果分别统计。

## 当前结论

| 范围 | 当前结论 |
| --- | --- |
| 本地实现与工程收尾 | 已完成，后续按可复现问题维护；源码与检查范围见[验证基线](#验证基线) |
| 真实 GLM 复验 | 最近原四场景 **3/4** 完整通过，明确表达式的独立分支恢复 **1/1**；历史 RAG 严格三场景 **2/3**，见[真实模型记录](#真实模型记录) |
| 已知模型问题 | 出现约 60 秒规划超时与规则回退；同会话续算曾回答正确但未执行要求的计算工具。独立分支通过不覆盖原失败 |
| 外部试点与生产就绪 | 真实业务资料、目标用户签收与部署环境待提供，尚未验收 |

用量只汇总已记录字段，未知消耗不补零，配置费用估算不等于供应商账单。没有提供输入或仅得到 skipped/manual 结果的阶段，不计作验收通过。

## 验证基线

应用验证记录截至 2026-10-09。当前界面源码基线为 `b255509`，下表本地验证对应该提交的应用改动；后端、真实模型及镜像沿用各自已有基线。本地工程收尾完成，后续按可复现问题维护。写入工具并行、HTTP/DAG checkpoint 和 ESLint 10 不属于当前收尾。

### 源码与验证范围

| 范围 | 已完成结果 | 来源 |
| --- | --- | --- |
| 后端 `bc1346f` | full slice 2224/2224、模块 9/9，含 OpenAPI 指纹；摘要脱敏新增 3/3 | `/tmp/insightagent-docs-backend.{log,md,json}`、`insightagent-docs-security-red.log` |
| 静态运维与工具 | 预检 5/5、Compose 7/7、普通故障标记 1/1；tooling 1/1、hygiene 4/4 | `/tmp/insightagent-docs-tooling.{md,json}`、`insightagent-docs-tooling-retry.log`、`insightagent-docs-hygiene.{log,md,json}` |
| 前端应用 `103ea1f` | node 217/217、lint 0 error / 2 既有 warning、Turbopack/webpack 双构建 | `/tmp/insightagent-ui-audit-frontend.{log,md,json}`、`insightagent-ui-audit-final-build-{turbo,webpack}.log` |
| 浏览器 `103ea1f` | Chromium Trace 1440/390px 2/2、原布局 2/2；Chrome 登录/工作台/任务/治理、完整 ID 复制；Mac 键盘三浏览器/两尺寸 6/6 | `/tmp/insightagent-ui-audit-{trace,e2e}.log`；运行命令见[手册](development-runbook.md) |
| 页面只读复核 `bc1346f` | Chrome 390×900：登录/注册、任务中心→详情、Failure 筛选；无页面横向溢出，覆盖层/console error 0；两个 ID 复制入口可见 | 本机开发页；复制内容与完整 e2e 沿用上一行 |
| 当前界面维护 `b255509` | 前端门禁 4/4：node 217/217、lint 0 error / 2 既有 warning、Turbopack/webpack 双构建；hygiene 4/4 | `/tmp/insightagent-layout-frontend.{log,md,json}`、`/tmp/insightagent-layout-hygiene.{log,md,json}` |
| 当前界面浏览器专项 `b255509` | Chromium/Firefox/WebKit 共 27/27：21 项布局/交互与 6 项 Trace 流程图；工作台 1440/390px，登录 1920/390px、深浅主题、中英文、注册切换；模型设置 Enter 提交与关闭后草稿复位 | `/tmp/insightagent-layout-e2e-matrix.log`；隔离 HTTP fixture，不计作真实模型或真实后端写入验收 |
| 隔离验收工具 | RAG 静态 17/17、独立 PostgreSQL/Chroma 1/1，规划等待/取消/迟到结果/重跑 5/5，导出静态 1/1 与 drill 自测 | `/tmp/insightagent-oct09-{rag-static,rag-postgres,planning-postgres}.log`、`insightagent-finalcheck-*` |
| 真实 GLM | 原四场景 3/4 完整通过，编辑表达式的独立分支恢复 1/1；原续算回退未实际调用计算工具 | [真实模型验收](acceptance.md#真实模型记录) |

tooling 首跑受沙箱 `/dev/fd` 限制，同命令提权复跑通过。后端定位摘要修复与开发 Compose loopback 定义已落源码；`bc1346f` 检查时未重启服务/容器，不能把运行实例视为已加载这些修改。端口 8000/3001 当时 HTTP 200、Chroma reachable。

### 工具与页面维护结论

- 检索调用真实 Chroma，计算使用 AST 白名单，HTTP 工具按显式配置执行；remote 缺连接值明确失败。canonical mock、协议 fixture 和历史名称兼容属于必要演示/测试路径，不是实际工具假结果。
- 普通 prompt 的测试故障标记已不影响生产 runner；登录中英文改为实际能力与估算费用，窄屏筛选、任务抽屉、发送按钮和长 ID 展示已修复。完整标识仍保留在 API/路由/导出和排障元数据中。
- 当前界面维护调整桌面登录比例与 420px 表单上限、深色主题、弹窗宽度和内部滚动；模型连接优先展示，工具与诊断折叠，保存/验证保留在底部。知识库 Collection 移入可展开详情，完整值仍可复制；用量先显示概览，高级筛选/趋势/明细折叠；空 Trace 提供任务入口，任务中心收起高级筛选并限制长标题行数。后端接口与模型调用逻辑未改；本机 8000/3001 健康检查 HTTP 200，实际 Chrome 只读核对了模型设置与知识库弹窗，未保存配置或调用供应商。
- 已检查跟踪文件，无真实 env、数据库、缓存、构建结果、日志或私钥产物；常见秘密特征扫描无命中，不等于完整 Git 历史或所有凭据类型已审计。`data/insightagent.plan.back.md` SHA256 保持 `5f6f79c4c7faf8a3becad7e6d7805fd86304425a2319b2702730fd4a54e4525d`。

### 镜像、CI 与外部验收

- 历史配对 `pilot-42ccf1f` / `pilot-9e78810` 未包含 `103ea1f` 页面/工具维护与 `bc1346f` 摘要修复。旧 `0209651` / `218f94d` 配对有 ARM64 构建、禁网 384 维 embedding、生产 PostgreSQL/Chroma、SSE/Trace/导出、恢复/取消及 Agent HTTP 协议 7/7 证据；旧 `218f94d` 配对隔离 Compose 重建后数据保留通过。均为本地模型替身，最新镜像未重建。历史摘要/配方来源可从 `65f1fde` 与 `bc1346f` 的 Git 文档查询，不沿用旧 tag 直接发布。
- 维护者于 2026-10-09 确认 `b255509` 已推送且 CI 绿色；本机检查时 `main` 与本地记录的 `origin/main` 一致、工作区干净。CI 状态由维护者提供，本轮未独立查询远端运行详情；后续文档提交不据此宣称获得新的 CI 验证。
- 真实业务引用/冲突版本/无依据回答、目标任务签收与供应商账单按[验收指南](acceptance.md)另行核对；HTTPS/访问边界、升级回滚、双存储恢复、RPO/RTO 与责任人按[部署指南](pilot-deployment-preflight.md)实测。配置 PASS 不改变未验收结论。

### 公开项目展示

2026-10-09 已整理[固定交付范围](showcase.md)：同仓库独立 `showcase/`，首页与两个预设案例的交互回放，目标为 Vercel Hobby 默认地址；不制作视频、不开放实时调用、不预设后续版本。维护者已授权案例准备阶段使用已保存的真实模型 Key，公开站不使用该 Key。

展示应用、公开截图与案例记录已实现。首页与 `/demo/` 为独立静态页面，不依赖完整应用后端；Vercel/云资源未创建，源码未推送，站点未公开发布。本轮结果不扩大完整应用的业务签收、CI、镜像或部署验收结论。

| 本轮范围 | 核对结果 | 证据与限制 |
| --- | --- | --- |
| 独立展示源码 | Node 24.14.0；typecheck、lint、格式检查通过；Node tests 6/6；Next.js 16.3.5 生产静态构建通过 | `showcase/` 与 `out/`；只验证本地静态导出，没有执行 Vercel 部署 |
| 浏览器交互 | Chromium / Firefox / WebKit × 1440px / 390px 共 6/6；播放、暂停、复位、重新播放、案例/分支切换、时间线/流程图、键盘节点选择与减少动态效果通过 | `/tmp/insightagent-showcase-browser.json`；生产 `out/` 静态服务，无页面横向溢出、控制台错误或外部/API 请求，截图已目视复核 |
| 知识检索与计算 | 专用合成资料；真实 glm-5.3 首轮规划、`task_retrieve`、`calc_eval` 完成；回答 14 万元，引用 `budget.md` 版本 | `showcase/data/cases.json`；原始耗时 95.246 秒，已记录总 tokens 7079 |
| 受控失败与独立恢复 | 原任务 fixture failed，实际计算后后续决策注入 429，没有最终回答；独立分支真实模型规划与计算 `(2+3)*2` 完成，回答 10 | fixture 不是供应商故障；失败 Trace 不伪造错误节点。恢复原始耗时 31.695 秒，已记录总 tokens 1838；恢复成功不覆盖原失败 |
| 公开素材 | 字段白名单、标识别名、来源检查与敏感字段断言通过；工作台截图只含专用合成内容 | 截图通过隔离 HTTP fixture 加载公开记录，不是后端端到端浏览器验收；素材说明见[来源文档](../showcase/data/README.md) |

执行源码基线 `58fabc3`；后台应用源码未变更。采集先按授权启动原有 PostgreSQL/Chroma 容器，未重建或删除容器/卷，采集完成后恢复停止；工作台截图用的 3001 服务和展示开发 3100 服务已停止。没有迁移/导出私人会话、数据库或完整配置，也没有进行备份/恢复演练。专用合成演示数据留在本机现有存储中。

准备过程曾出现约 60 秒规划超时、网络失败，以及未满足实际计算或专用来源断言的尝试；均未计作公开成功案例。上述 tokens 仅对应两份最终成功记录，不能代替全部准备尝试用量或供应商账单。模型回答可靠性的既有边界继续保留。

原工作台与新展示应用的验证范围独立；本轮未重跑无关后端全量或沿用旧 CI 作为新应用通过证据。本轮 hygiene 4/4，受影响文档本地链接 95 项无缺失，新增展示源码冲突标记与采集脚本语法检查通过；原始计划 SHA256 未变。摘要 `/tmp/insightagent-showcase-hygiene.{md,json}`。浏览器路径：本会话没有 Browser 插件（`Browser plugin not available`），复用仓库已有 Playwright；复验入口 `node showcase/scripts/verify-browser.mjs`。

范围文档检查：本地链接 107 项无缺失，hygiene 4/4，`git diff --check` 通过；原始计划 SHA256 保持既有值。摘要 `/tmp/insightagent-showcase-scope-hygiene.{md,json}`。这些结果仅为文档检查，不计作展示应用验收。

#### 初版架构交互与阅读引导（2026-10-10，历史验证）

在展示源码 `0b77318` 基础上按维护者需求完善既有两页：原 Next.js → FastAPI → 模型 API / PostgreSQL / Chroma 总览保留为“系统分层”；新增“任务执行”视图、八步显式讲解、节点职责/源码依据、路径高亮、手机节点聚焦与全图查看。案例增加观察重点与明确“查看全图”按钮。保持现有深色/绿色视觉，不新增页面、案例、视频或 Agent 能力。

展示应用 typecheck、lint、格式检查、Node tests 6/6 与生产静态构建通过。Chromium / Firefox / WebKit × 1440px / 390px 共 6/6，覆盖原图五模块保留、节点鼠标/键盘选择、八步播放/暂停/复位/结束、视图切换停止播放、手机节点清晰度、减少动态效果，以及既有案例/分支回放与全图操作；无页面横向溢出、控制台错误或外部/API 请求。验证中补齐受控图的节点尺寸同步，使聚焦与全图缩放使用实际渲染尺寸，保持记录顺序/声明依赖的既有布局契约。结果 `/tmp/insightagent-showcase-browser.json`；架构、原图与案例截图已目视复核，并在 Codex 内置浏览器核对桌面/手机预览。复验入口仍为 `node showcase/scripts/verify-browser.mjs`。

本轮 hygiene 4/4，受影响文档与架构源码入口的本地路径共 107 项无缺失，原始计划 SHA256 未变；摘要 `/tmp/insightagent-architecture-hygiene.{md,json}`、`/tmp/insightagent-architecture-links.json`。架构动画是概念示意，未请求真实模型、修改公开案例记录或原应用代码；复用已有 3101 静态服务。三个 README、展示运行说明与固定范围已同步；本轮变更尚未提交、推送或部署，不作为新 CI、镜像或业务验收结果。

#### 四段首页与自动架构讲解（2026-10-10，上一轮本地验证）

按维护者确认将首页组织为 01 核心能力、02 系统架构、03 任务执行、04 工程实践：原系统总览与执行图直接显示，无需切换；工程内容顺延，不增加第五段。保留原五模块、深色/绿色样式和节点职责，工程区内部编号改为图标。执行图完成加载与初始聚焦且至少四分之一进入视野后自动讲解一次（1.8 秒/步），结束停留；离开视野或页面切至后台即暂停，返回不自动恢复，手动操作优先。减少动态效果时只手动播放，并显示对应提示；画布上的滚轮允许继续滚动页面。案例播放方式本轮仍为手动。

最终源码 typecheck、lint、格式检查、Node tests 6/6、Next.js 16.3.5 静态生产构建通过。Chromium / Firefox / WebKit × 1440px / 390px 共 6/6，覆盖四段顺序、两图无需切换、原五模块、鼠标/键盘节点选择、手机节点聚焦、首次进入视野自动播放/结束不循环、离屏暂停且返回不重启、手动播放/暂停/复位、减少动态效果禁自动播放与动态切换后暂停、画布滚轮不阻断页面，以及原有案例/分支回放与全图操作。无页面横向溢出、控制台错误或外部/API 请求；结果 `/tmp/insightagent-showcase-browser.json`，系统架构与执行区桌面/手机截图已目视复核，Codex 内置浏览器复核了页面衔接与滚动。

hygiene 4/4，原始计划 SHA256 未变；摘要 `/tmp/insightagent-showcase-four-sections-hygiene.{md,json}`。同步三个 README、展示运行说明与固定范围，复用已有 3101 静态服务。既有暂存内容保留，本次调整未暂存、提交、推送或部署；没有更改原应用、公开案例数据、容器或存储，没有调用模型，不作为新 CI、镜像或业务验收结果。

#### 案例进入与切换自动回放（2026-10-10，本地验证基线）

按维护者明确需求，案例页进入时自动播放默认知识检索/计算记录，主动切换案例或原任务/恢复分支后复位并播放对应记录一次；重复点击当前案例/分支不重播。查看时间线或流程图节点时暂停，复位后停止，结束后停留，不循环或自动跳转案例/分支；后台可见性事件或启用减少动态效果时暂停，返回不自动恢复。减少动态效果时只手动播放，页面提示同步切换；播放节奏保持原有 1.1 秒/步。仅调整公开回放交互和空状态文案，不更改公开记录、来源或模型/后端契约。

展示应用 typecheck、lint、格式检查、Node tests 6/6、Next.js 16.3.5 静态生产构建通过。Chromium / Firefox / WebKit × 1440px / 390px 共 6/6，覆盖页面/切换自动回放、原任务与恢复分支独立结论、结束不循环或自动切换、重复点击不重播、节点鼠标/键盘查看、暂停/重播/复位、减少动态效果禁自动播放及动态切换后暂停、时间线/流程图和既有首页架构回归；无页面横向溢出、控制台错误或外部/API 请求。后台暂停与返回不重启使用模拟 `document.hidden` / `visibilitychange` 事件核对，不等于完整操作系统后台调度验收。浏览器结果 `/tmp/insightagent-showcase-browser.json`；桌面/手机截图目视核对，并使用 Codex 内置浏览器核对进入与切换回放。Browser 插件未列出，复用仓库既有 Playwright 验证入口。

hygiene 4/4，受影响文档本地链接 94 项无缺失，原始计划 SHA256 未变；摘要 `/tmp/insightagent-showcase-case-autoplay-hygiene.{md,json}`、`/tmp/insightagent-showcase-case-autoplay-links.json`。复用已有 3101 静态服务，三个 README、展示运行说明与固定范围按影响同步。本地提交范围为四段首页、交互架构、案例自动回放、对应验证脚本与文档；未启动完整应用、调用模型、修改容器或存储，推送与部署尚未执行。不作为新 CI、镜像、供应商或外部验收结果。

#### GitHub Pages 发布适配（2026-10-10，本地验证基线）

维护者选择同仓库 GitHub Pages 替代 Vercel 作为当前静态展示发布目标。展示构建新增 `NEXT_PUBLIC_BASE_PATH`，默认根路径不变；Pages 按仓库名设置 `/InsightAgent`，页面链接与公开截图使用同一前缀。新增 `showcase-pages` 工作流：push/PR 仅检查、构建并上传 `showcase/out` 静态产物，只有 main 手动运行才进入部署任务；部署配置不自动启用 Pages。不增加依赖、页面、案例或原应用能力。

展示应用 typecheck、lint、格式检查、Node tests 6/6 通过，根路径与 Pages 子路径的 Next.js 16.3.5 静态构建均通过。复用 3101 根路径预览，另用固定静态快照在 3102 模拟 `/InsightAgent/`。两种路径各运行 Chromium / Firefox / WebKit × 1440px / 390px，共 12/12；覆盖图片、首页与案例跳转、案例直接访问/刷新、懒加载执行图与流程图、自动/手动回放及既有交互，未发现横向溢出、控制台错误、HTTP 错误或外部/API 请求。根路径与 Pages 导出 HTML 各核对 31 个本地素材/导航目标存在；浏览器结果 `/tmp/insightagent-showcase-browser.json`、`/tmp/insightagent-showcase-browser-pages.json`。首轮检查受共享构建输出切换干扰，随后改用固定快照；检查脚本区分正常导航取消的预取与网络错误后复验通过。

工作流仅完成本地 YAML 解析及触发条件、权限、依赖与产物目录检查，未在 GitHub 运行。三个 README、展示运行说明和固定范围已同步；hygiene 4/4、文档本地链接无缺失，原始计划 SHA256 未变。摘要 `/tmp/insightagent-pages-hygiene.{md,json}`、`/tmp/insightagent-pages-links.json`。检查后恢复根路径导出，停止本轮 3102 静态服务，保留既有 3101 预览；未启动完整应用、调用模型或修改容器/存储。推送、Pages 启用、公开发布和目标环境验收尚未执行，默认项目地址仅为预计地址；上线实测后再添加正式链接。不沿用旧 CI 或历史镜像作为本次发布证据。

## 本机检查入口

```bash
bash scripts/local_acceptance.sh --help
bash scripts/local_acceptance.sh
```

默认检查健康、静态发布门禁和验收工具自测，不调用真实模型、不重建镜像、不清理已有数据库。Docker/端口/浏览器权限按[运行手册](development-runbook.md)处理。报告默认位于 `/tmp/insightagent-local-acceptance-report.{md,json}`，可用 `--report-md` / `--report-json` 更改；运行时记录 Git 状态、阶段与候选镜像，不写死提交或 PR 状态。

可选输入：`--materials-dir`、`--questions-file` 和 `--pilot-url`。提供业务资料、问题清单及鉴权 token 后，业务 RAG 阶段会按当前用户模型设置执行，remote **可能消耗真实用量**；HTTPS 探测只读。缺输入的阶段标记 skipped，不能视为通过。`--with-real-glm` / `--with-pilot-image-rebuild` 打开相应人工指引/可选阶段，不表示已经完成模型或镜像验收。浏览器键盘和隔离数据库专项按运行手册执行，不由默认入口重复代跑。

## 业务 RAG

资料目录递归读取 `.md` / `.txt`，文件名作为 source / document_id。问题格式参考 [questions.json](../scripts/fixtures/business_rag_acceptance/synthetic/questions.json)。工具创建独立 `acceptance-toolkit-*` 知识库，逐题执行任务和 SSE，输出低敏报告。

登录 token 通过当前进程的 `INSIGHT_AGENT_ACCESS_TOKEN` 提供，不写进命令、历史、报告或仓库。使用已启动的本机服务：

```bash
backend/.venv/bin/python scripts/business_rag_acceptance_runner.py \
  --api-base-url http://127.0.0.1:8000 \
  --materials-dir /path/to/business/materials \
  --questions-file /path/to/questions.json \
  --output-md /tmp/insightagent-business-rag-acceptance/report.md \
  --output-json /tmp/insightagent-business-rag-acceptance/report.json
```

默认保留本次知识库供复核；显式 `--cleanup` 删除本次创建的库，不应指向已有业务库。无服务静态检查为 `backend/.venv/bin/python scripts/test_business_rag_acceptance_static.py`；`business_rag_acceptance_runner.py --self-test` 使用独立 Docker PostgreSQL/Chroma 与模型替身，结束清理测试资源，不能替代真实业务验收。`test_business_rag_acceptance.py` 包装器会先跑静态，再在 Docker 可用时跑隔离自测；Docker 不可用的 skipped 不等于集成通过。

| `checks.auto` 类型 | 核对内容 |
| --- | --- |
| `citation_source` | 检索 Trace 含指定 source |
| `answer_contains` | 回答包含子串，报告仅记录该子串哈希 |
| `answer_not_documented` | 明确说明未记载/未提及 |
| `tool_executed` / `tool_not_executed` | 前者只认本任务 done action，排除 checkpoint 复用；后者也拒绝失败调用尝试 |
| 内置 `tool_claim_vs_trace` | 回答的计算工具声明与实际 Trace 是否相符 |

所有题目必须 completed 且回答非空。工具声明检测是启发式：明确否定不因工具词误报，历史/条件/模糊提及进入 `manual_review`。`checks.manual` 的字符串列表需人工核对。报告区分 `auto_pass` / `manual_review` / `auto_fail`，自动通过不等于业务签收；用量 known 只表示已记录字段可汇总，不证明所有失败/放弃的供应商消耗已计入。

## 目标任务与签收

选 2–3 个来自真实业务的任务，先写预期再执行：

| 任务 | 验收重点 |
| --- | --- |
| 检索 + 派生计算 | source / document_version 正确，Trace 有真实检索与计算，回答与用量一致 |
| 冲突版本或无依据问题 | 引用对应版本，不编造未记载事实；人工复核规划回退和等待体验 |
| 工作台完整路径 | 登录→输入→SSE/Trace→历史/导出；必要时验证取消与分支恢复 |

每项记录源码/镜像/环境、用户角色、输入的脱敏描述、预期、会话/任务 ID、通过/不通过/带风险通过、耗时、问题、人工复核人和是否同意试点。用户确认与业务原文保存在受控验收记录中，不进入公共仓库。

```bash
backend/.venv/bin/python scripts/export_acceptance_evidence.py \
  --api-base-url http://127.0.0.1:8000 \
  --session-id <会话UUID> \
  --output-dir /tmp/insightagent-acceptance-evidence
```

可多次指定 `--task-id` 限定任务；证据包仅含指纹与低敏元数据，不含消息正文或密钥。目标 HTTPS、升级回滚、备份恢复与 RPO/RTO 按[部署指南](pilot-deployment-preflight.md#目标环境演练记录)单独实测，不把合成资料、模型替身或静态预检计作部署签收。

## 真实模型记录

更新：2026-10-09。使用已保存的智谱 `glm-5.3` remote 设置，服务为本机 `8000` / `3001` 与真实 PostgreSQL/Chroma；不记录凭据或私人对话，不计作镜像或目标部署实测。历史验收会话与独立合成库保留，临时日志消失不推翻本文件记录。

**最近原四场景 3/4 完整通过，明确表达式的独立分支恢复 1/1。** 同会话续算回答正确但规划回退未调用要求的计算工具，成功分支不覆盖该结果。业务资料、目标用户、供应商账单及部署未验收，范围见[验证基线](acceptance.md#验证基线)。

### 最近复验（2026-10-09）

应用基线 `c909306`，后端运行时相对 `42ccf1f` 无提交差异。计算/续算/恢复用 Chrome，RAG 用已鉴权业务 HTTP。

| 场景 | 任务 ID | 结果 | 规划 / 回答 / 已记录总 tokens |
| --- | --- | --- | --- |
| API 合成资料预算加倍 | `535bf6b7-b931-4c45-b40c-06210edba50e` | 检索与实际计算 14，通过；回答来源与 sha256 版本均存在 | 4103 / 1284 / 5387 |
| API 资料未记载上线日期 | `a9b24874-087d-4cf2-9779-b99fcef5ced3` | 真实规划/检索，明确未记载，来源版本存在，通过 | 2635 / 1067 / 3702 |
| 工作台 29×13 | `3fef852d-43f1-4412-b35c-2c4cb4ec9eac` | Enter 发送、实际 Calculator、377、done，通过 | 1186 / 1346 / 2532 |
| 工作台上轮结果加 23 | `de625991-a505-48f6-ad3b-f12313aeffed` | 回答自行推算 400 正确，明确本轮未执行计算工具；规划走规则回退，未满足实际调用工具要求 | 未知 / 931 / 931（仅已知回答） |
| 上述任务的独立分支，编辑为 377+23 | `d43ea50d-2096-4e32-933c-a0a896421e48` | 详情 → 分支重跑 → 编辑 → 创建并运行，实际 Calculator、400、done，通过；父子关联核对通过 | 1745 / 1345 / 3090 |

五项均 completed；Trace、全量 delta、JSON v1.0、Markdown 和 assistant 消息一致，不能写成目标 5/5。已记录 **15,642 tokens**：四项完整规划+回答 14,711，回退续算仅已知回答 931；未返回的失败/放弃规划消耗未知，不是全部供应商消耗或账单成本。

两条 RAG 任务约 46.072 / 46.007 秒，17 / 21 个 heartbeat，首次约 2.123 / 2.098 秒；小样本不能作为性能承诺。Chrome 等待文案、恢复路径及父子关联正常，无捕获的框架覆盖层/warn/error。Codex 内置浏览器登录后曾 `Failed to fetch`，原因未确诊，不能宣称所有浏览器通过。

- 保留会话：API `3624659a-40c4-4de1-a56f-2ab0d988d8f2`（真实模型收尾复验）、Chrome `9c5fc72f-57db-4f2e-a17c-4253596a785c`（工作台真实模型复验）、分支 `4d4cf1f7-f12c-4476-8833-08261cf43c66`；独立合成库 `acceptance-toolkit-oct09-1791508418` 保留。无旧知识库或业务数据清理。

最终低敏证据 `/tmp/insightagent-oct09-real-verified.{json,md,log}`、`/tmp/insightagent-oct09-real-evidence.json`；早期未修正用量读取的报告不作为最终用量依据。验收工具要求 completed/非空回答、done action，不把 checkpoint 复用算成调用；自然语言声明检测是启发式，操作见[验收指南](acceptance.md)。静态 17/17、隔离 RAG 1/1、规划等待/取消/迟到结果/分支恢复 5/5，来源 `/tmp/insightagent-oct09-{rag-static,rag-postgres,planning-postgres}.log`，属于本地替身验证。

### 初始基础验证（2026-10-08）

应用来源 `218f94d`，本机开发服务。实际流式连通 125 tokens、约 4.06 秒，结束原因 stop。验收会话 `06a94f04-8c6d-4756-9bb7-8bbf1fbc7979`。

| 入口与场景 | 任务 ID | 结果 | 规划 tokens | 回答 tokens | 总 tokens |
| --- | --- | --- | ---: | ---: | ---: |
| 后端任务服务：17×19 | `f6b9601f-85ea-45e7-b6a8-5728d2347a98` | completed，323 | 873 | 747 | 1,620 |
| 后端任务服务：上轮结果加 7 | `3c075773-7cde-48d4-8f8e-2e7e69219e8d` | completed，330 | 1,617 | 1,171 | 2,788 |
| 登录浏览器工作台发送：23×11 | `293b69e5-2c3e-43ed-95b4-96ac64c10365` | completed，253，UI 显示 done | 1,462 | 535 | 1,997 |

三任务 3/3，6,405 tokens，加连通共 **6,530**。前两项调用任务服务，第三项覆盖工作台→HTTP→SSE；真实规划、计算、历史、消息、Trace/delta/导出和规划+回答用量一致。来源 `/tmp/insightagent-real-model-configured-tasks.{json,log}`；不将服务调用范围说成浏览器全路径。

### RAG 引用与执行声明（2026-10-08）

此前发现回答声称执行了未调用的计算工具，以及规划尝试绑定检索正文预算。已向最终模型提供成功执行/复用清单；检索绑定只允许 hit_count / knowledge_base_id，正文事实通过后续反馈规划计算。运行时仍拒绝非法路径；提示约束不能保证模型所有回答绝不误述。

| 场景 | 任务 ID | 结论 | 已返回 tokens |
| --- | --- | --- | ---: |
| 正文预算 7 → 真实检索、反馈计算 14 | `dfcc2a7a-bd7d-4183-aa4f-b8f969434253` | PASS；来源 `star-sail-guide.md` / `sha256:0816e12da7d64061` | 5,612 |
| 正文预算 5 → 真实检索、反馈计算 10 | `a9b22b66-be93-42c8-9173-57dc39b0dc3c` | PASS；来源 `star-sail-guide.md` / `sha256:0c54ed5d00e3146e` | 5,995 |
| 询问资料未记载的上线日期 | `f0c7487b-c73f-409e-a319-b795771845d4` | 首轮规划约 60 秒超时后规则检索；真实回答明确未记载，来源/版本正确。因验收脚本强制要求真实规划，严格结果 FAIL，不能计入全规划成功 | 2,138（仅已知最终用量） |
| 注入规划超时 → 真实最终回答 | `6a15ac46-9054-4df3-b4c2-f5b8ec1ff384` | 明确没有调用计算工具，14 为自行推算；请求缺口说明正确 | 1,706（仅已知最终用量） |

正常检索/计算 **2/2**；严格前三场景 **2/3**，未知日期回答正确但约 60 秒首轮规划超时回退。第四项仅最终回答是真实模型，规划超时为注入，不算全程真实规划。Trace/delta/导出、正文、来源/版本及已知用量一致。来源 `/tmp/insightagent-real-rag-acceptance-fixed.{json,log}`、`/tmp/insightagent-real-fallback-acceptance.{json,log}`；修复前记录 `/tmp/insightagent-real-rag-acceptance.{json,log}`。执行证据静态 7/7、独立 PostgreSQL/Chroma 核心 11/11 为历史本地验证。

### 规划等待与恢复边界

只读汇总的 HTTP 尝试耗时如下，含错误/回退；两组任务和轮数不同，不能据均值变化宣称性能改善：

| 日志样本 | 非流式请求数 | 请求 min / mean / max（秒） | 流式请求数 | 流 min / mean / max（秒） | outcome 为 unexpected_error |
| --- | ---: | --- | ---: | --- | ---: |
| 修复前真实 RAG | 4 | 3.096 / 33.304 / 60.081 | 2 | 10.280 / 15.519 / 20.758 | 1 |
| 修复后真实 RAG | 7 | 4.156 / 21.307 / 60.075 | 3 | 22.946 / 27.185 / 32.979 | 1 |

来源 `/tmp/insightagent-provider-latency-{before,fixed}.json`。Provider 默认 socket timeout 60 秒；两次异常约 60 秒、另一次成功请求 59.094 秒。日志不足以区分连接、读取、推理等待或确诊供应商根因，不能推算失败率、首 token 时间和账单。

首轮规划在线程中执行，流主循环每 2 秒发 heartbeat 并检查取消/超时。取消后不等规划线程结束，迟到结果不改写 Trace、消息或用量；底层供应商调用仍可能跑完并收费。隔离 `test_provider_planning_wait_postgres.py` 5/5 验证等待、取消、空规划回退用量和失败分支恢复，不代替真实一分钟等待体验。保留首轮规则回退、后续规划失败及未知用量规则，没有延长超时或新增自动重试。

真实业务引用、冲突版本、无依据回答、目标用户等待体验、成本与目标环境另行验收；当前工程维护不把上述未验收项写成通过。
