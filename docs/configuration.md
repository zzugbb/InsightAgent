# 配置与凭据管理

开发配置、用户模型设置和试点部署配置是三种不同入口。它们共享服务端行为，但不能混用密钥位置、网络地址或验证结论。

## 配置入口与优先级

| 入口 | 位置 / 用途 | 是否提交 |
| --- | --- | --- |
| 开发模板 | `backend/.env.example`；mock 与本机依赖示例 | 保留模板，无真实 Key |
| 实际开发配置 | `backend/.env` 或进程环境；进程环境覆盖文件值 | 不提交 |
| 用户模型设置 | 登录 → 模型设置；用户范围的 PostgreSQL 记录 | 不提交数据库/导出 |
| 前端 API 地址 | `NEXT_PUBLIC_API_BASE_URL`，浏览器请求地址 | 仅公开地址可进入构建 |
| 展示路径前缀 | `showcase/` 的 `NEXT_PUBLIC_BASE_PATH`，Pages 使用 `/InsightAgent`，本地默认空 | 公开路径，可进入构建 |
| 试点部署配置 | 仓库外、仅操作员可读的 env，交给 `pilot_compose.py` | 不提交 |

后端配置由 `app/config.py` 读取，修改进程配置需重启对应实例。用户设置覆盖已保存的 mode/provider/model/profile/source；未设置的连接字段继承服务端默认值。没有用户记录时使用默认配置，provider/model/key 齐备时可自动选择 remote。

静态展示不设置后端 API 地址或模型变量；路径前缀只控制静态链接，不提供模型连接。运行与发布见[展示 README](../showcase/README.md)。

## 真实模型 Key 的使用路径

1. 登录后选择 remote，填写提供方标签、实际模型名称、OpenAI-compatible API 基础地址和 Key。标签不意味着该供应商已通过真实兼容验收。
2. “校验”探测连接/授权；成功不证明 chat/completions、流式结束或工具规划都正常。随后用小任务核对实际 Trace 和回答，参考[真实模型验收](acceptance.md#真实模型记录)。
3. 保存时由服务端加密写入 `user_settings.api_key_enc`。设置响应只返回 `api_key_configured`，前端保存后清空 Key 草稿，不将 Key 放入 localStorage。
4. remote 空 Key / 地址表示沿用既有值，不能把空输入当成删除按钮。切到 mock 会清空用户保存的连接值；服务端全局默认 Key 仍有继承可能，当前没有单独的“撤销继承”配置。真正停用某个 Key 需在供应商侧撤销，并检查服务端默认值。

Base URL 会出现在设置摘要中，不能嵌入用户名、密码、token 查询参数或片段；认证使用独立 Key/服务端 HTTP headers。remote 允许 HTTP 以支持本机替身，自托管外部模型应使用 HTTPS 或受控内部网络。用户可配置远端地址，当前没有通用网络目标白名单；对不可信用户开放前需由部署边界限制注册和后端网络出口。

## 关键运行参数

| 变量 | 当前默认 / 用途 |
| --- | --- |
| `INSIGHT_AGENT_ENV` | development；试点显式 production |
| `INSIGHT_AGENT_MODE / PROVIDER / MODEL` | mock / mock / mock-gpt；remote 使用实际提供方与模型 |
| `INSIGHT_AGENT_BASE_URL / API_KEY` | 全局连接默认值；Key 只在后端配置 |
| `INSIGHT_AGENT_DATABASE_URL` | 开发 PostgreSQL 示例；生产独立凭据，URL 保留字符需编码 |
| `CHROMA_HOST / PORT / PROBE` | 127.0.0.1 / 8001 / true；同 Compose 网络用 chroma:8000 |
| `INSIGHT_AGENT_JWT_SECRET` | 开发示例只用于本机；生产使用随机独立值 |
| `INSIGHT_AGENT_SECRET_KEY` | 用户 Key 加密与 refresh 哈希派生材料；为空回退 JWT，仅建议开发 |
| `INSIGHT_AGENT_CORS_ORIGINS` | 本机 3001 来源；生产显式 JSON HTTPS origins，无 wildcard |
| `INSIGHT_AGENT_ACCESS_TOKEN_TTL_MINUTES` | 开发默认 10080；生产按访问策略评估，不将其视为推荐时长 |
| `INSIGHT_AGENT_REFRESH_TOKEN_TTL_DAYS` | 30；需结合撤销与访问控制 |
| `TASK_TIMEOUT_SEC / AGENT_MAX_ROUNDS` | 180 秒 / 3 轮，有界执行 |
| `TASK_QUEUE_MAX_CONCURRENT` | 单进程最多 32 任务；不是全局分布式额度 |
| `TASK_QUEUE_MAX_CONCURRENT_PER_USER / PER_SESSION` | 默认 0，不启用范围上限 |
| `TASK_TOOL_MAX_CONCURRENT` | 默认 1，1–4；仅合格读取/计算工具并发 |
| `RAG_INGEST_JOB_TIMEOUT_SEC / BATCH_SIZE` | 300 秒 / 128 切块，超时不自动重放 |
| `USAGE_*_TOKEN_PRICE_PER_1K` | 项目配置的 USD 估算单价，必须按实际模型调整，不是供应商报价 |

Trace 持久化/重连轮询、执行 owner/heartbeat/stale recovery、备份/运维摘要参数和 tool registry 组合项，以 [config.py](../backend/app/config.py) 与[运行手册](development-runbook.md)为准。工具模板、认证头和原始响应属于受控服务端配置，只公开投影后的允许字段。

## 前端与容器网络

`NEXT_PUBLIC_*` 会进入浏览器。生产前端 API 地址在构建时固化，必须是用户浏览器可达的地址；不能填仅 Docker 内可解析的 `backend:8000`。HTTPS 页面调用 HTTP API 会被浏览器拦截；试点前端 build API 地址、目标 API 地址和 CORS 必须匹配。

开发 Compose 仅发布到 127.0.0.1；它仍使用开发密码、浮动镜像、启动安装依赖及 reload/dev。`compose.pilot.yml` 不发布数据库/Chroma，应用端口也只发布到 loopback，HTTPS 代理和访问控制另行准备。使用[预检与镜像配方](pilot-deployment-preflight.md)，不要在公开日志运行会展开秘密的 `docker compose config`。

修改 Compose 文件**不会改变已运行容器的端口绑定**；新配置须待备份后由操作者安排应用。已有旧 Chroma `/chroma/chroma` 挂载可能漏掉容器内 `/data`，禁止直接重建。详见[备份恢复](pilot-deployment-preflight.md#开发栈备份恢复)。

## 密钥保存、备份和轮换

生产预检要求 JWT 与加密主密钥分别至少 32 字符且不同，数据库采用非默认密码；这仅检查格式，不能证明随机熵或权限。加密实现为当前自有 v1 格式（随机 nonce、HMAC 派生流与完整性标签），不是托管 KMS，也未宣称通过独立密码学审计。

数据库备份包含用户数据和加密 Key；加密主密钥必须单独受控保管。当前没有透明主密钥重加密迁移流程，直接更换会使旧 Key 无法解密，并影响 refresh token 哈希匹配。JWT 轮换使已有 access token 失效；无独立主密钥时还影响上述派生材料。轮换前先确定重新登录、重新配置用户 Key 与回滚方案，不复制真实秘密进文档。

更多权限和披露约定见 [SECURITY.md](../SECURITY.md)。
