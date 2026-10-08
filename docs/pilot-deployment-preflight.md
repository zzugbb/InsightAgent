# 试点部署配置预检

此流程用于准备 A2 试点部署证据。仓库中的 `compose.full.yml` 是开发栈，包含 `--reload`、`npm run dev`、启动时安装依赖及默认 PostgreSQL 密码，不作为试点部署文件。单机试点使用 `compose.pilot.yml` 和 `scripts/pilot_compose.py`；目标主机需要另行提供 HTTPS 代理、证书及访问控制。

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

`PILOT_FRONTEND_BUILD_API_BASE_URL` 是前端构建时的 `NEXT_PUBLIC_API_BASE_URL` 记录，必须与实际浏览器 API 地址一致。文件解析支持普通 `KEY=VALUE` 和单层引号，不执行 shell 展开。下方隔离联调可检查已构建镜像实际发出的浏览器请求是否指向该地址；镜像构建来源仍需人工核验。

从仓库根目录运行：

```bash
python3 scripts/check_pilot_deploy_config.py --env-file /安全路径/pilot.env
```

预检会检查生产环境标志、HTTPS 地址、CORS、非默认数据库密码、两个独立密钥是否有基本长度，以及四个部署镜像和两个构建基础镜像是否用 `sha256` 摘要固定。`PASS` 仅表示这些静态值符合最低格式；它不访问镜像仓库、数据库、提供方或部署环境，也不证明密钥熵、镜像内容和 HTTPS 入口已生效。

## 生产镜像配方

`backend/Dockerfile.pilot` 通过 `requirements.pilot.txt` 固定 Chroma 直接依赖为 `1.5.7`，再用 `requirements.pilot.lock` 约束试点镜像的 84 个直接/传递依赖版本；构建期运行 `pip check`，并要求最终 `pip freeze` 与锁文件逐项一致。运行时采用非 root Uvicorn，不使用源码卷或 `--reload`。UID/GID 10001 用户具备 `/home/insightagent` 主目录；构建期使用 Chroma 默认 embedding 函数下载、校验并准备模型，API 和导入 worker 共用该用户缓存，运行时无需首次下载。下载地址与模型 SHA256 由锁定的 Chroma 实现确定，构建失败不能发布镜像。`frontend/Dockerfile.pilot` 用 `npm ci`、`next build` 生成 Next standalone 产物，再以非 root 用户运行 `server.js`。两份 `.dockerignore` 排除本地环境文件、依赖目录、缓存及测试产物，避免把开发机密钥或大体积构建目录送入 Docker 上下文。

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

构建后推送到目标镜像仓库并取得仓库返回的摘要，再填写 `PILOT_BACKEND_IMAGE` 和 `PILOT_FRONTEND_IMAGE`。后端锁文件是从已验证的 Linux ARM64 / Python 3.14 镜像导出的版本基线；升级直接依赖时应在隔离镜像中重新解析、验证并更新它。版本约束没有锁定 wheel 哈希，跨架构可用性也尚未验证；镜像摘要用于固定最终构建产物。目标环境的镜像拉取、健康检查、TLS/访问边界和回滚仍需实测。

### 当前本地候选记录（2026-10-08）

- 后端从干净应用提交 `0209651385e38097747d0698b1be88901e731ddc` 构建，包含执行证据与检索绑定提示修复；tag `insightagent-backend:pilot-0209651`，revision label `0209651`，ID `sha256:6e819a52ad6ba75485cdaeb4659630dc0371c5c4e2d655635cb16697024bc313`，ARM64，用户 `10001:10001`。
- 前端应用源码/锁文件/构建配方相对 `218f94d` 未变（仅 README 更新，`git diff --exit-code 218f94d HEAD -- frontend ':(exclude)frontend/README.md'` 通过）；复用 `insightagent-frontend:pilot-218f94d`，revision label `218f94d`，ID `sha256:5f740a3bfd07961c1ab4e225c7774fdafb6186fe06b800968244b5dbb8c2a634`，ARM64，用户 `node`，API 地址 `https://api.pilot.example.com`。
- 配方 SHA256 保持：后端 `4c6e03c3972c713fbd9bc8f6e1848435806217188c2e2c322cf74fcf7e462b49`；前端 `59387de5c78de9643507a368d56686a8021a8e7b73f255e7f45a331913ae3ec4`；后端 84 项依赖锁 `63bfdbdcdec309134535512227921c083b6ad4f2c735968fc6451a83846ac49d`。Python 基础镜像 `python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d`；前端既有 Node 来源 `node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6`。
- 按相对路径排序，逐个拼接路径 UTF-8、NUL 与文件内容后计算 SHA256；宿主 `backend/app` 与禁网只读镜像 `/app/app` 的 78 个 `.py` 文件均为 `3f5679b28404f14a17211bd80ddc96f37d3743f1e228363b6ecb5123745c9d86`。标签本身不能证明内容，摘要仅覆盖这些 Python 文件。
- 新配对隔离联调 PASS：禁网 embedding 384 维；生产模式、真实 PostgreSQL/Chroma 下后台幂等导入/召回、任务 SSE/Trace/delta/JSON v1.0/Markdown、步骤恢复与 2 个工具结果复用/usage 清零、排队取消、前端 HTML/CSS/浏览器 API 地址均通过。Agent HTTP 协议专项 7 场景：5 完成/2 失败、13 规划/5 回答请求，历史/会话隔离、两种正文驱动反馈与来源/版本、空正文/429 用量隔离和导出一致。资源清理后才报告成功，scope `local_production_protocol_fixture`；模型仅本地替身，不消耗真实 Key。
- 当前来源 `/tmp/insightagent-pilot-0209651-backend-retry.log`、`/tmp/insightagent-pilot-0209651-source-proof.log` / `.json`、`/tmp/insightagent-pilot-0209651-smoke.log`；首次 embedding HTTPS 握手超时后相同配方重试成功，模型下载/hash/预热保留原校验。测试依赖摘要继续使用下方命令中的固定值。
- 本轮镜像/文档 hygiene 3/3 PASS，来源 `/tmp/insightagent-pilot-0209651-hygiene.md` / `.json`；备份计划未修改。
- Compose 全容器重建持久化保留旧 `218f94d` 双镜像基线，来源 `/tmp/insightagent-pilot-218f94d-compose-smoke.log`；本轮无数据库/持久化/Compose/前端应用变化，未重跑该专项。当前后端门禁 2/2：2217/2217、模块 9/9；核心 PostgreSQL/Chroma 11/11，前端保留上一 node 217/217/lint/双构建基线。本机真实模型的合成验收范围单独见[验收记录](real-model-acceptance.md)。

本地镜像 ID 不能充当目标仓库摘要。候选未推送或部署；跨架构、真实模型质量、TLS/访问边界和升级回滚仍未验证。

在 Docker 可用且上述四份镜像已在本机时，可运行隔离联调（运行和访问本机端口通常需要提权）：

```bash
backend/.venv/bin/python scripts/smoke_pilot_images.py \
  --backend-image insightagent-backend:pilot-0209651 \
  --frontend-image insightagent-frontend:pilot-218f94d \
  --expected-api-base-url https://api.pilot.example.com \
  --postgres-image postgres@sha256:20edbde7749f822887a1a022ad526fde0a47d6b2be9a8364433605cf65099416 \
  --chroma-image chromadb/chroma@sha256:fc8dc8e11fb252b3bc610f6affe6e0ac883252519f4f6021a08a2e31d9a295f4
```

`--expected-api-base-url` 应取环境文件中的 `PILOT_FRONTEND_BUILD_API_BASE_URL`。脚本先在禁网容器中核对非 root embedding，再创建随机命名的临时网络与容器、临时凭据，不挂载仓库或既有数据卷；以生产模式和显式 mock 模型启动后端，开启内建工具并发为 2，验证 PostgreSQL 注册/会话写读、真实 Chroma 后台导入/检索、任务 SSE/Trace/delta/导出、步骤恢复与排队取消。Trace ID/seq、幂等分支、复用 usage 和来源不变均须通过才报告成功，摘要标明 `local_production_mock`。编排检查拆入 `scripts/pilot_task_smoke.py`；无服务自测 `scripts/test_pilot_task_smoke.py` 已接入 tooling 门禁。

前端检查使用本机 Node/Playwright，在浏览器中注入一次性假 token 并拦截外网请求，核对认证请求的实际 API 地址及 HTML/CSS；配置不一致即失败。结束时核验清理。默认 PostgreSQL/Chroma 镜像仅用于本地联调，可通过参数指定；此项不证明目标 API 可达、真实跨域调用、模型质量或 TLS。默认 embedding 的单文档召回也不代表真实资料质量/吞吐验收。

仅复核 Dockerfile 静态规则可运行 `docker build --check --build-arg PYTHON_BASE_IMAGE=python:3.14-slim -f backend/Dockerfile.pilot backend` 与对应的前端命令（`NODE_BASE_IMAGE=node:24-bookworm-slim`、`NEXT_PUBLIC_API_BASE_URL=https://api.example.com`）。此检查不会执行依赖安装或验证最终镜像；真正构建仍必须传入摘要固定的基础镜像。

### Agent 核心协议专项

在上方 `smoke_pilot_images.py` 命令追加 `--with-agent-fixture`。它先完成原有 mock 链路，再在同一临时网络启动只读 Python HTTP 替身容器；仅给临时测试用户配置固定的假 Key 与内部模型地址，通过镜像的真实 HTTP Provider 和公开 API 执行场景。替身不保存或输出提示词、请求头或密钥，健康摘要只保留固定模型标签、调用计数和无效请求数。缺少历史、知识正文/来源/版本或计算证据时拒绝回答，防止规则回退误报通过。

当前应用候选 `218f94d` 的 **7/7 场景通过**：历史问答进入规划/回答且不改写用户消息；新会话不带旧历史；两个同命中数、不同正文的知识库分别驱动 `7*2`/`5*2`，最终回答保留来源和内容版本；首轮空正文仍保存本次 12 token 并回退回答，后续空正文保存两次规划的 24 token 后失败，后续 429 只保留此前 12 token。5 个任务完成、2 个失败；实际 HTTP 请求为 13 次规划/5 次回答，无多余请求或无效请求，失败任务不生成 assistant。Trace/delta/JSON v1.0/Markdown、消息与用量核对通过。成功摘要仅在临时资源清理通过后输出。

原始镜像协议记录 `/tmp/insightagent-pilot-agent-protocol.log`，scope 为 `local_production_protocol_fixture`，Agent 子项为 `local_http_protocol_fixture`。无服务自测 `backend/.venv/bin/python scripts/test_pilot_agent_smoke.py` **9/9**，原 task smoke 自测 **6/6**（含清理失败不输出 PASS）；已进入 `test_ci_e2e_tooling.sh`。当前 tooling **1/1**、hygiene **3/3** PASS，摘要为 `/tmp/insightagent-pilot-agent-{tooling,hygiene}.md` / `.json`。本轮应用代码及镜像未变，继续保留 2210/217 的完整静态门禁基线；修改的是验证工具与文档。

这项验证证明候选镜像能传递并保存这些协议场景的数据；替身依据预设规则返回结果，不能证明真实模型的推理、引用质量、成本或服务商兼容性。完整浏览器交互、目标 TLS/访问边界及真实模型验收仍使用各自的独立证据。

## 单机试点 Compose

`compose.pilot.yml` 运行四个已构建镜像，不挂载源码、不覆盖镜像启动命令、不在启动时安装依赖。PostgreSQL 16 使用 `pg_data:/var/lib/postgresql/data`，Chroma 使用 `chroma_data:/data`；镜像必须与这两个持久路径兼容。数据库和 Chroma 不发布主机端口，backend/frontend 仅绑定主机 `127.0.0.1:8000` / `127.0.0.1:3001`，由同机 HTTPS 代理转发。远程或容器化代理需要单独设计网络，不能直接使用其容器内的 `127.0.0.1`。没有 TLS 入口时，该清单还不能交付外部用户。

PostgreSQL 通过健康检查后才启动 backend；backend 的健康检查包含 Chroma 可达性，frontend 等 backend 健康后启动。服务配置 `unless-stopped` 重启策略；`up --wait` 等待有健康检查的服务就绪。Chroma 本身没有额外容器健康检查，其可达性由 backend 验证。健康检查不调用真实模型，也不证明模型账号可用。此等待语义遵循 [Docker Compose 启动顺序文档](https://docs.docker.com/compose/how-tos/startup-order/)。

在前面的外部环境文件中补充以下值；`INSIGHT_AGENT_DATABASE_URL` 必须指向服务名 `postgres:5432`，用户名、解码后的密码和数据库名须与下面三项一致，URL 中的保留字符须 percent-encode。固定 PostgreSQL 16 镜像及摘要后再启动，不能直接换大版本并复用原卷。

```dotenv
PILOT_POSTGRES_USER=pilot
PILOT_POSTGRES_PASSWORD='<独立数据库密码>'
PILOT_POSTGRES_DB=insightagent
INSIGHT_AGENT_MODE=remote
INSIGHT_AGENT_PROVIDER=<实际兼容提供方名称>
INSIGHT_AGENT_MODEL=<实际模型名称>
INSIGHT_AGENT_BASE_URL=https://<实际提供方>/v1
INSIGHT_AGENT_API_KEY='<有效密钥，仅存仓库外>'
# 可选；必须为不同的 1–65535 主机端口，绑定地址始终为 127.0.0.1
PILOT_BACKEND_PORT=8000
PILOT_FRONTEND_PORT=3001
```

环境文件仍须仅操作员可读。`pilot_compose.py` 使用已有只读解析器，把单行值作为字面量传给 Compose；不执行 shell 展开或转义解码，`$` 可放在单引号内，不支持多行值。入口屏蔽环境中已有的 `PILOT_`、`INSIGHT_AGENT_`、`NEXT_PUBLIC_` 和 `COMPOSE_` 覆盖，并显式禁用开发 `.env`，使预检与启动使用同一组值。直接调用 Compose 的环境变量有不同的[优先级及插值规则](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)，试点操作统一使用下方入口。

```bash
# check 只验证配置和 Compose 解析，不启动容器、不请求模型
backend/.venv/bin/python scripts/pilot_compose.py check \
  --env-file /安全路径/pilot.env --project insightagent-pilot
# 环境、镜像和 HTTPS 代理准备后再启动；等待健康检查
backend/.venv/bin/python scripts/pilot_compose.py up \
  --env-file /安全路径/pilot.env --project insightagent-pilot
# 停止或移除容器时保留持久卷
backend/.venv/bin/python scripts/pilot_compose.py stop \
  --env-file /安全路径/pilot.env --project insightagent-pilot
backend/.venv/bin/python scripts/pilot_compose.py down \
  --env-file /安全路径/pilot.env --project insightagent-pilot
```

入口先检查六个镜像摘要、HTTPS/CORS、独立密钥、Compose 数据库一致性、模型配置是否齐全和主机端口，再解析清单。未配置真实 key 时会拒绝启动，不用 mock 代替正式试点。输出只有固定码与 action，不输出 Compose 解析结果、Docker stdout/stderr 或配置值；不要额外运行 `docker compose config` 并把包含密钥的输出写入公开日志。`check` 的 PASS 仅证明配置/语法；`up` 的 PASS 证明容器健康等待成功。`restart` 仅重启现有容器，不应用新的配置；配置或镜像变更用 `up`，并保持相同 project 名称。`stop`/`down` 的 PASS 表示命令成功，不表示备份已完成。

升级/回滚仍须先备份、记录固定新旧镜像摘要并进行数据兼容检查。`down` 保留两份卷；更换 project 名称会创建另一组数据卷，不能把这种启动当作恢复。当前[快照工具](local-stack-backup-restore.md)的已验证范围仍是开发栈，本轮容器重建读回不替代备份恢复或 RPO/RTO 验收。

### Compose 隔离验证

```bash
backend/.venv/bin/python scripts/smoke_pilot_compose.py \
  --backend-image insightagent-backend:pilot-0209651 \
  --frontend-image insightagent-frontend:pilot-218f94d \
  --expected-api-base-url https://api.pilot.example.com \
  --postgres-image postgres@sha256:20edbde7749f822887a1a022ad526fde0a47d6b2be9a8364433605cf65099416 \
  --chroma-image chromadb/chroma@sha256:fc8dc8e11fb252b3bc610f6affe6e0ac883252519f4f6021a08a2e31d9a295f4
```

脚本先解析原生产清单并核对 remote、前端无密钥、无源码挂载/启动命令覆盖；随后仅在随机命名 fixture 项目中覆盖为 mock、本地镜像 tag 和随机 loopback 端口，不发出真实模型请求。实际验证健康启动、前端 API 地址、后台导入/检索、任务/Trace/导出、步骤恢复与取消；然后移除全部容器、保留卷并重新创建，核对登录、会话、任务/Trace/messages 和知识召回保留。结束时仅删除自己的测试容器、网络和卷，检查清理后才报告 PASS，摘要 scope 为 `local_compose_mock_recreate`。

2026-10-08 旧 `218f94d` 配对的 Compose 持久化验证通过，原始记录为 `/tmp/insightagent-pilot-218f94d-compose-smoke.log`。无服务配置/低敏自测 `scripts/test_pilot_compose.py` 7/7 已纳入 tooling；`compose.pilot.yml` 的变更触发 release-gate/backend-e2e/frontend-e2e，release gate auto 保守选择全部阶段。应用提交的 full release gate 10/10 来源为 `/tmp/insightagent-planning-call-usage-release.md` 与 `.json`，包含后端 2210/2210、module boundary 9/9、前端 217/217、lint 0 error/2 个既有 warning 与 Turbopack/webpack 双构建；该次应用代码未变；本次后端修复后的门禁及新配对来源见上方记录，本轮未重跑 Compose 持久化。Compose 联调不覆盖多轮模型反馈或全部浏览器交互；模型反馈新增上方镜像 HTTP 协议专项，各 UI 范围保留专项基线。目标镜像拉取、TLS、真实模型、升级回滚及备份恢复仍未验证。

## 目标环境演练记录

1. 确认目标主机、操作者、访问边界、TLS 终止点与证书，并保存脱敏的代理配置/检查结果；前后端、PostgreSQL、Chroma 的对外端口按环境设计限制访问。
2. 从可复核源码、后端依赖清单与前端锁文件构建生产镜像；前端在构建期运行 `next build` 并在容器内运行 standalone `server.js`，后端不使用 `--reload`，容器启动时不安装依赖。记录源码提交、构建命令、基础与成品镜像摘要及构建时 API 地址。
3. 在目标环境运行预检并保存其固定检查码结果；部署后核对 HTTPS、登录、会话、任务/SSE/Trace、RAG、导出、健康摘要和低敏日志。真实 LLM 成功路径需有效账号，GLM 到期期间保持未验证。
4. 升级前保存 PostgreSQL/Chroma 备份，按照[恢复流程](local-stack-backup-restore.md)记录恢复可用性；以固定旧镜像摘要执行一次回滚，核对数据、登录和主链路。记录升级/回滚时间、失败点、责任人和最终结论。

目标环境及这些实测记录尚未具备，因此 A2 当前仍为 `待实证`。
