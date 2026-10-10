# 验收指南

本文记录本机工程、真实模型、业务任务与部署的验证范围，并提供复验入口。结论与证据分开阅读，模型替身、真实模型及目标环境结果分别统计。

## 当前结论

| 范围 | 当前结论 |
| --- | --- |
| 本地实现与工程收尾 | 已完成，后续按可复现问题维护；源码与检查范围见[验证基线](#验证基线) |
| 真实 GLM 复验 | 最近原四场景 **3/4** 完整通过，明确表达式的独立分支恢复 **1/1**；历史 RAG 严格三场景 **2/3**，见[真实模型记录](#真实模型记录) |
| 已知模型问题 | 出现约 60 秒规划超时与规则回退；同会话续算曾回答正确但未执行要求的计算工具。独立分支通过不覆盖原失败 |
| 公开静态展示 | GitHub Pages 已发布，线上三浏览器/两尺寸 6/6；仅预设记录回放，见[公开项目展示](#公开项目展示)，不等于完整应用部署 |
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

表中 `/tmp` 文件是历史临时证据，可能已清理；已有记录不因文件消失而失效，复验使用下方入口。源码检查不证明已有运行实例加载了修改；服务与存储状态须在操作前另查。

### 工具与页面维护结论

- 检索调用真实 Chroma，计算使用 AST 白名单，HTTP 工具按显式配置执行；remote 缺连接值明确失败。canonical mock、协议 fixture 和历史名称兼容属于必要演示/测试路径，不是实际工具假结果。
- 普通 prompt 的测试故障标记已不影响生产 runner；登录中英文改为实际能力与估算费用，窄屏筛选、任务抽屉、发送按钮和长 ID 展示已修复。完整标识仍保留在 API/路由/导出和排障元数据中。
- 当前界面维护调整桌面登录比例与 420px 表单上限、深色主题、弹窗宽度和内部滚动；模型连接优先展示，工具与诊断折叠，保存/验证保留在底部。知识库 Collection 移入可展开详情，完整值仍可复制；用量先显示概览，高级筛选/趋势/明细折叠；空 Trace 提供任务入口，任务中心收起高级筛选并限制长标题行数。后端接口与模型调用逻辑未改；当时 Chrome 只读核对了模型设置与知识库弹窗，未保存配置或调用供应商。
- 已检查跟踪文件，无真实 env、数据库、缓存、构建结果、日志或私钥产物；常见秘密特征扫描无命中，不等于完整 Git 历史或所有凭据类型已审计。`data/insightagent.plan.back.md` SHA256 保持 `5f6f79c4c7faf8a3becad7e6d7805fd86304425a2319b2702730fd4a54e4525d`。

### 镜像、CI 与外部验收

- 历史配对 `pilot-42ccf1f` / `pilot-9e78810` 未包含 `103ea1f` 页面/工具维护与 `bc1346f` 摘要修复。旧 `0209651` / `218f94d` 配对有 ARM64 构建、禁网 384 维 embedding、生产 PostgreSQL/Chroma、SSE/Trace/导出、恢复/取消及 Agent HTTP 协议 7/7 证据；旧 `218f94d` 配对隔离 Compose 重建后数据保留通过。均为本地模型替身。历史候选应用镜像已从本机删除，最新源码须重新构建和验证，不能假设旧 tag 仍存在。历史摘要/配方来源可从 `65f1fde` 与 `bc1346f` 的 Git 文档查询，不沿用旧 tag 直接发布。
- 维护者于 2026-10-09 确认 `b255509` 已推送且 CI 绿色；本机检查时 `main` 与本地记录的 `origin/main` 一致、工作区干净。CI 状态由维护者提供，本轮未独立查询远端运行详情；后续文档提交不据此宣称获得新的 CI 验证。
- 真实业务引用/冲突版本/无依据回答、目标任务签收与供应商账单按[验收指南](acceptance.md)另行核对；HTTPS/访问边界、升级回滚、双存储恢复、RPO/RTO 与责任人按[部署指南](pilot-deployment-preflight.md)实测。配置 PASS 不改变未验收结论。

### 公开项目展示

截至 2026-10-10，[首页](https://zzugbb.github.io/InsightAgent/)与[案例页](https://zzugbb.github.io/InsightAgent/demo/)已在 GitHub Pages 发布。展示源码基线为 `d514e30`；完整应用执行代码与公开素材采集基线为 `58fabc3`。当前页面与发布规则见[展示说明](showcase.md)，维护命令见[展示 README](../showcase/README.md)。开发过程和被替代的阶段记录从 Git 查询。

| 范围 | 已完成结果 | 证据与限制 |
| --- | --- | --- |
| 静态源码 | Node 24.14.0、Next.js 16.3.5；typecheck、lint、格式检查、Node tests 6/6；根路径与 Pages 子路径构建通过 | 独立 `showcase/`，静态 `out/` 不提交，无完整应用运行时依赖 |
| 本地浏览器 | 根路径与 `/InsightAgent/` 各三浏览器 × 1440/390px，共 12/12；各导出 31 个素材/导航目标存在 | `/tmp/insightagent-showcase-browser.json`、`/tmp/insightagent-showcase-browser-pages.json`；固定静态快照复验，区分正常导航取消与请求错误 |
| GitHub 发布 | `d514e30` 的 [showcase-pages #1](https://github.com/zzugbb/InsightAgent/actions/runs/38020458507) build / deploy 均成功 | 独立查询工作流；Pages 来源为 GitHub Actions，默认域名 HTTPS。main 相关改动自动发布，PR 只检查 |
| 线上浏览器 | Chromium / Firefox / WebKit × 1440/390px 共 6/6 | `/tmp/insightagent-showcase-browser-online.json`；首页四段、两图、截图、懒加载、回放、节点/分支、键盘、减少动态效果、直接访问/刷新与返回首页通过；无页面横向溢出、控制台/HTTP 错误或外部/API 请求 |
| 知识检索与计算 | 真实 glm-5.3 规划、`task_retrieve`、`calc_eval`，回答 14 万元，保留 `budget.md` 版本 | 原始 95.246 秒，已记录总 tokens 7079；专用合成资料，非业务签收 |
| 失败与独立恢复 | fixture 原任务实际计算后决策注入 429，无最终回答；真实模型独立分支计算 `(2+3)*2`，回答 10 | fixture 不是供应商故障，不伪造失败工具节点；恢复 31.695 秒、已记录总 tokens 1838，成功不覆盖原失败 |
| 公开素材 | 字段白名单、公开标识别名、来源与敏感字段检查通过 | [来源说明](../showcase/data/README.md)；真实工作台截图通过隔离 HTTP fixture 加载公开记录，不是完整后端浏览器验收 |

后台暂停与返回不重启通过模拟 `document.hidden` / `visibilitychange` 核对，不等于操作系统后台调度全面验收。架构动画是概念示意，案例自动回放一次且不循环；阅读节奏与原始耗时分开。

素材准备曾出现约 60 秒规划超时、网络失败及不满足实际计算/专用来源断言的尝试，均未计入公开成功案例。两份成功记录的 tokens 不包含全部准备消耗或供应商账单；模型可靠性的既有边界继续保留。采集仅创建专用合成会话/知识库，没有迁移或导出私人数据、数据库、Key 或完整配置，没有进行备份/恢复演练。旧存储容器未重建或删除，合成数据留在本机存储中。

独立核对 `d514e30` 的 [release-gate #67](https://github.com/zzugbb/InsightAgent/actions/runs/38020458522)、[backend-e2e #234](https://github.com/zzugbb/InsightAgent/actions/runs/38020458657) 和 [frontend-e2e #217](https://github.com/zzugbb/InsightAgent/actions/runs/38020458515) 均通过；后者于 2026-10-10 补查确认。结果仅对应该源码，不作为后续文档提交的 CI 结果。公开静态展示上线不替代完整应用部署、真实业务签收或双存储恢复验收。

### 文档维护核对

2026-10-10：更新项目入口与上线状态，将展示规划和重复阶段记录合并为维护说明及当前基线。22 份跟踪 Markdown 的 221 个本地链接/锚点有效，513 份跟踪文本的对外文案已核对；原应用与展示源码、案例数据未修改。hygiene 4/4，原始只读计划 SHA256 不变。未重跑无关应用全量、调用模型或操作数据服务；此项仅为文档核对，不扩大运行与部署验收范围。

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

**最近原四场景 3/4 完整通过，明确表达式的独立分支恢复 1/1。** 同会话续算回答正确但规划回退未调用要求的计算工具，成功分支不覆盖该结果。业务资料、目标用户、供应商账单及完整应用部署未验收，范围见[验证基线](acceptance.md#验证基线)。

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
