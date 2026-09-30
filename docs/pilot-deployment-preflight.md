# 试点部署配置预检

此流程用于准备 A2 试点部署证据。仓库中的 `compose.full.yml` 是开发栈，包含 `--reload`、`npm run dev`、启动时安装依赖及默认 PostgreSQL 密码，不作为试点部署文件。

## 配置文件

在仓库外创建仅操作员可读的环境文件，填入以下变量。不要提交文件、打印文件内容或把密钥写入命令行参数。预检只输出固定检查码。

```dotenv
INSIGHT_AGENT_ENV=production
PILOT_FRONTEND_URL=https://pilot.example.com
NEXT_PUBLIC_API_BASE_URL=https://api.pilot.example.com
PILOT_FRONTEND_BUILD_API_BASE_URL=https://api.pilot.example.com
INSIGHT_AGENT_CORS_ORIGINS='["https://pilot.example.com"]'
INSIGHT_AGENT_JWT_SECRET=<至少 32 字符的随机值>
INSIGHT_AGENT_SECRET_KEY=<至少 32 字符的独立随机值>
INSIGHT_AGENT_DATABASE_URL=postgresql://<用户>:<非默认密码>@<数据库主机>:5432/<数据库名>
PILOT_BACKEND_IMAGE=registry.example.com/insight-backend@sha256:<64 位十六进制摘要>
PILOT_FRONTEND_IMAGE=registry.example.com/insight-frontend@sha256:<64 位十六进制摘要>
PILOT_CHROMA_IMAGE=registry.example.com/chroma@sha256:<64 位十六进制摘要>
PILOT_POSTGRES_IMAGE=registry.example.com/postgres@sha256:<64 位十六进制摘要>
PILOT_PYTHON_BASE_IMAGE=python:3.14-slim@sha256:<64 位十六进制摘要>
PILOT_NODE_BASE_IMAGE=node:24-bookworm-slim@sha256:<64 位十六进制摘要>
```

`PILOT_FRONTEND_BUILD_API_BASE_URL` 是前端构建时的 `NEXT_PUBLIC_API_BASE_URL` 记录，必须与实际浏览器 API 地址一致。文件解析支持普通 `KEY=VALUE` 和单层引号，不执行 shell 展开。实际镜像构建来源及该值是否进入构建产物仍需人工核验。

从仓库根目录运行：

```bash
python3 scripts/check_pilot_deploy_config.py --env-file /安全路径/pilot.env
```

预检会检查生产环境标志、HTTPS 地址、CORS、非默认数据库密码、两个独立密钥是否有基本长度，以及四个部署镜像和两个构建基础镜像是否用 `sha256` 摘要固定。`PASS` 仅表示这些静态值符合最低格式；它不访问镜像仓库、数据库、提供方或部署环境，也不证明密钥熵、镜像内容和 HTTPS 入口已生效。

## 生产镜像配方

`backend/Dockerfile.pilot` 安装后端依赖并以非 root 用户运行 Uvicorn，不使用源码卷或 `--reload`；`frontend/Dockerfile.pilot` 用 `npm ci`、`next build` 生成 Next standalone 产物，再以非 root 用户运行 `server.js`。两份 `.dockerignore` 排除本地环境文件、依赖目录、缓存及测试产物，避免把开发机密钥或大体积构建目录送入 Docker 上下文。

在构建机使用已核对摘要的官方 Python/Node 基础镜像，示例命令中的值由操作员替换；前端 API 地址是公开的构建参数，不传入后端密钥：

```bash
docker build -f backend/Dockerfile.pilot \
  --build-arg PYTHON_BASE_IMAGE='python:3.14-slim@sha256:<已核对摘要>' \
  -t insightagent-backend:<候选版本> backend
docker build -f frontend/Dockerfile.pilot \
  --build-arg NODE_BASE_IMAGE='node:24-bookworm-slim@sha256:<已核对摘要>' \
  --build-arg NEXT_PUBLIC_API_BASE_URL='https://api.pilot.example.com' \
  -t insightagent-frontend:<候选版本> frontend
```

构建后推送到目标镜像仓库并取得仓库返回的摘要，再填写 `PILOT_BACKEND_IMAGE` 和 `PILOT_FRONTEND_IMAGE`。当前后端 `chromadb>=0.5.20` 及其传递依赖未由仓库锁文件完全固定；镜像摘要可固定已构建产物，但同一源码再次构建仍需核对依赖解析与产物差异。目标环境的镜像拉取、健康检查、TLS/访问边界和回滚仍需实测。

仅复核 Dockerfile 静态规则可运行 `docker build --check --build-arg PYTHON_BASE_IMAGE=python:3.14-slim -f backend/Dockerfile.pilot backend` 与对应的前端命令（`NODE_BASE_IMAGE=node:24-bookworm-slim`、`NEXT_PUBLIC_API_BASE_URL=https://api.example.com`）。此检查不会执行依赖安装或验证最终镜像；真正构建仍必须传入摘要固定的基础镜像。

## 目标环境演练记录

1. 确认目标主机、操作者、访问边界、TLS 终止点与证书，并保存脱敏的代理配置/检查结果；前后端、PostgreSQL、Chroma 的对外端口按环境设计限制访问。
2. 从可复核源码与锁文件构建后端/前端生产镜像；前端在构建期运行 `next build` 并在容器内运行 standalone `server.js`，后端不使用 `--reload`，容器启动时不安装依赖。记录源码提交、构建命令、基础与成品镜像摘要及构建时 API 地址。
3. 在目标环境运行预检并保存其固定检查码结果；部署后核对 HTTPS、登录、会话、任务/SSE/Trace、RAG、导出、健康摘要和低敏日志。真实 LLM 成功路径需有效账号，GLM 到期期间保持未验证。
4. 升级前保存 PostgreSQL/Chroma 备份，按照[恢复流程](local-stack-backup-restore.md)记录恢复可用性；以固定旧镜像摘要执行一次回滚，核对数据、登录和主链路。记录升级/回滚时间、失败点、责任人和最终结论。

目标环境及这些实测记录尚未具备，因此 A2 当前仍为 `待实证`。
