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

## Vercel 发布配置（尚未发布）

单独取得推送/公开发布授权后，使用维护者的 GitHub 与 Vercel Hobby 账号：

| 设置 | 值 |
| --- | --- |
| Root Directory | `showcase` |
| Framework Preset | Next.js |
| Node.js Version | 24.x |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | 使用 Next.js 预设；本地静态导出目录是 `out` |
| Environment Variables | 无需设置模型、鉴权或后端环境变量 |

使用 Vercel 默认地址即可，无需购买域名或配置数据库。关联 Git 仓库后，推送可能触发自动发布，需要按公开发布授权处理。部署完成后再实测两条路由、素材、浏览器控制台、案例交互和外部请求，并添加实际有效的线上链接。

当前实现与本地静态验证不能替代 Vercel 账号连接、免费额度核对和目标环境验证。参考[Vercel Next.js 支持](https://vercel.com/docs/frameworks/full-stack/nextjs)、[Node.js 版本](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions)、[Hobby 使用规则](https://vercel.com/docs/plans/hobby)。
