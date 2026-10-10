# InsightAgent 公开展示

独立静态站：首页介绍完整项目，`/demo/` 回放两个预设案例。用于开源展示与面试讲解，不提供在线 Agent 服务。固定范围见[展示说明](../docs/showcase.md)，验证结果见[验收基线](../docs/acceptance.md#公开项目展示)。

## 本地运行

从仓库根目录执行，使用 Node 24.x 和 npm：

```bash
npm --prefix showcase ci
npm --prefix showcase run dev
```

开发预览为 `http://127.0.0.1:3100/`。运行前先查已有监听；不启动完整工作台、FastAPI 或数据服务。

```bash
npm --prefix showcase run typecheck
npm --prefix showcase run lint
npm --prefix showcase run format:check
npm --prefix showcase test
npm --prefix showcase run build
```

生产构建为 `showcase/out/`，输出仅含静态 HTML、JS、CSS、图片与公开案例。可用任意静态文件服务器验证；例如在仓库根目录运行：

```bash
backend/.venv/bin/python -m http.server 3101 --bind 127.0.0.1 --directory showcase/out
```

这条命令只提供静态文件，不运行项目后端。构建、缓存、依赖与检查产物不提交。

在静态预览已运行、原 `frontend/` Playwright 依赖与三个浏览器已安装的环境中，可复验桌面/手机交互：

```bash
node showcase/scripts/verify-browser.mjs
```

脚本复用原仓库的浏览器检查工具，不进入展示站构建；结果与截图写入 `/tmp/insightagent-showcase-*`。浏览器与本机访问按当前权限流程执行。

## 交互与素材

- 首页 `/`：项目定位、工作台截图、01 核心能力、02 系统架构、03 任务执行、04 工程实践、验证边界与源码入口。
- 架构区：原系统分层总览与任务执行图分别直接展示，支持节点职责/源码依据、八步播放/暂停/复位、缩放与查看全图；执行图进入视野且完成加载后自动播放一次，结束停留、离开视野或页面切至后台即暂停，返回不自动恢复；减少动态效果时仅手动播放，手机默认聚焦选中节点。讲解是概念示意，不是任务 Trace 或实时 SSE。
- 案例 `/demo/`：知识检索与计算；受控失败与真实模型独立恢复分支。进入页面播放默认案例，主动切换案例或原任务/恢复分支后播放对应记录一次；重复点击当前案例/分支不重播。可暂停、复位、重新播放、切换时间线/流程图和点击节点；查看节点会暂停，结束停留，切至后台或启用减少动态效果时暂停且不自动恢复；减少动态效果时仅手动播放。任务输入下提示观察重点，流程图区有明确“查看全图”按钮。
- 回放每步约 1.1 秒，仅为阅读节奏；原始执行耗时另行展示。流程图区分记录顺序与已声明依赖/决策关系，不推造 DAG。
- 页面无需登录，不调用完整应用 API 或模型，不接收 Key，不保存访客任务，不包含统计追踪。

公开素材的来源与处理范围见[data/README.md](data/README.md)。`public/workbench.png` 是现有工作台的真实界面截图，通过隔离 HTTP fixture 装载公开案例中的问题、回答和 Trace；不是截图时重新请求真实模型，也不算完整后端浏览器验收。

Trace 布局逻辑来自原工作台，相关独立模块在 `lib/`；展示站不从 `frontend/` 或 `backend/` 导入运行时代码。首页执行图在架构区进入视野时加载；案例 React Flow 在访客选择流程图后加载。两处均只读取静态公开数据。

## GitHub Pages 发布（尚未发布）

当前选择同一公开仓库的 GitHub Pages，不需要服务器、域名、Vercel 项目或模型 Key。默认项目地址预计为 `https://zzugbb.github.io/InsightAgent/`，只有线上验证通过后才作为有效展示链接添加到仓库介绍和主 README。

[发布工作流](../.github/workflows/showcase-pages.yml)使用 Node 24、`npm ci` 和现有检查，构建时按仓库名设置 `NEXT_PUBLIC_BASE_PATH=/InsightAgent`，只上传 `showcase/out`。该变量是公开路径前缀，不是凭据；Next.js 页面链接自动加前缀，公开图片显式使用相同前缀。不提交构建产物或添加后端环境配置。

- 推送 main 或创建涉及展示源码的 PR：检查和构建，**不发布**。
- 取得推送授权并上传本次提交后，检查对应工作流结果；不能沿用旧 CI。
- 单独取得公开发布授权后，在仓库 `Settings → Pages → Build and deployment → Source` 选择 `GitHub Actions`。
- 在 `Actions → showcase-pages → Run workflow` 选择 `main`，手动触发构建和发布。只有 main 的手动运行才进入 `github-pages` 部署环境；配置步骤不会自动启用 Pages。
- 实测首页、`/demo/` 直接访问与刷新、图片、懒加载图、回放、移动布局、控制台及外部请求后，再添加实际链接。
- 后续修复仍手动发布；回滚时将所需修复或 revert 提交纳入 main，再运行同一工作流。无需新增展示版本或功能。

本地根路径开发和构建不设置前缀。模拟 Pages 项目路径时，从仓库根目录执行：

```bash
NEXT_PUBLIC_BASE_PATH=/InsightAgent npm --prefix showcase run build
pages_preview="$(mktemp -d /tmp/insightagent-pages.XXXXXX)"
mkdir "$pages_preview/InsightAgent"
cp -R showcase/out/. "$pages_preview/InsightAgent/"
backend/.venv/bin/python -m http.server 3102 --bind 127.0.0.1 --directory "$pages_preview"
```

另一个终端运行浏览器检查：

```bash
SHOWCASE_BASE_URL=http://127.0.0.1:3102/InsightAgent/ node showcase/scripts/verify-browser.mjs
```

预览前核对端口并按本机访问权限流程执行；结果写入 `/tmp/insightagent-showcase-browser-pages.json`。项目路径构建不能直接用于根路径预览；如需恢复 3101 预览，重新执行不带前缀的 `npm --prefix showcase run build`。静态预览和工作流配置检查不等于 GitHub Pages 已发布成功。

GitHub Free 支持公开仓库的 Pages。依据：[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[自定义发布工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[Next.js 子路径](https://nextjs.org/docs/app/api-reference/config/next-config-js/basePath)。

Vercel 仍可作为备选：项目根目录 `showcase`、Node 24、安装 `npm ci`、构建 `npm run build`，不设置 `NEXT_PUBLIC_BASE_PATH` 或模型变量；关联和发布同样需要授权。当前未创建或关联 Vercel 项目。
