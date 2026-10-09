# 历史候选镜像证据

以下记录保留既有构建与联调来源，**没有重建当前源码镜像**。后端 `pilot-42ccf1f` 与前端 `pilot-9e78810` 不含 `103ea1f` 及本轮数据库摘要修复；不能把历史来源的“当轮源码相等”当成当前 HEAD 相等。目标部署、真实模型与用户验收分别记录。

构建、预检和操作方式见[部署指南](pilot-deployment-preflight.md)。临时日志消失不推翻已记载的持久范围。

## 最近历史候选记录（2026-10-09）

- 后端 `insightagent-backend:pilot-42ccf1f`，ID `sha256:981c5025b88bfea3f354592629cef55a481b7f893d1a9f1b5b89842a9b7536c2`，ARM64；前端 `insightagent-frontend:pilot-9e78810`，ID `sha256:010b1e010ba8a49a0f22c3166b844bf228fe415032264acf435aa6c2437a583e`，ARM64。该次维护只读 Docker inspect 核对；该次维护应用/依赖/配方未改，未重建镜像。
- 既有配对 `--with-agent-fixture` 冒烟 PASS，前后卷/网络零新增，来源 `/tmp/insightagent-pilot-9e78810-{frontend-build,smoke}.log`，已记录于 `c909306`；该次维护未重跑镜像专项。后端应用/配方/依赖相对 `42ccf1f` 无提交差异，前端应用相对 `9e78810` 无提交差异（排除 README）。
- 该次本机真实模型复验见[验收记录](real-model-acceptance.md)，与镜像替身验证分开。候选未推送/部署；目标 HTTPS、升级回滚与备份恢复仍待验。

## 历史候选记录（2026-10-08，0209651 / 218f94d）

- 后端从干净应用提交 `0209651385e38097747d0698b1be88901e731ddc` 构建，包含执行证据与检索绑定提示修复；tag `insightagent-backend:pilot-0209651`，revision label `0209651`，ID `sha256:6e819a52ad6ba75485cdaeb4659630dc0371c5c4e2d655635cb16697024bc313`，ARM64，用户 `10001:10001`。
- 前端应用源码/锁文件/构建配方相对 `218f94d` 未变（仅 README 更新，`git diff --exit-code 218f94d HEAD -- frontend ':(exclude)frontend/README.md'` 通过）；复用 `insightagent-frontend:pilot-218f94d`，revision label `218f94d`，ID `sha256:5f740a3bfd07961c1ab4e225c7774fdafb6186fe06b800968244b5dbb8c2a634`，ARM64，用户 `node`，API 地址 `https://api.pilot.example.com`。
- 配方 SHA256 保持：后端 `4c6e03c3972c713fbd9bc8f6e1848435806217188c2e2c322cf74fcf7e462b49`；前端 `59387de5c78de9643507a368d56686a8021a8e7b73f255e7f45a331913ae3ec4`；后端 84 项依赖锁 `63bfdbdcdec309134535512227921c083b6ad4f2c735968fc6451a83846ac49d`。Python 基础镜像 `python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d`；前端既有 Node 来源 `node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6`。
- 按相对路径排序，逐个拼接路径 UTF-8、NUL 与文件内容后计算 SHA256；宿主 `backend/app` 与禁网只读镜像 `/app/app` 的 78 个 `.py` 文件均为 `3f5679b28404f14a17211bd80ddc96f37d3743f1e228363b6ecb5123745c9d86`。标签本身不能证明内容，摘要仅覆盖这些 Python 文件。
- 新配对隔离联调 PASS：禁网 embedding 384 维；生产模式、真实 PostgreSQL/Chroma 下后台幂等导入/召回、任务 SSE/Trace/delta/JSON v1.0/Markdown、步骤恢复与 2 个工具结果复用/usage 清零、排队取消、前端 HTML/CSS/浏览器 API 地址均通过。Agent HTTP 协议专项 7 场景：5 完成/2 失败、13 规划/5 回答请求，历史/会话隔离、两种正文驱动反馈与来源/版本、空正文/429 用量隔离和导出一致。资源清理后才报告成功，scope `local_production_protocol_fixture`；模型仅本地替身，不消耗真实 Key。
- 该次来源 `/tmp/insightagent-pilot-0209651-backend-retry.log`、`/tmp/insightagent-pilot-0209651-source-proof.log` / `.json`、`/tmp/insightagent-pilot-0209651-smoke.log`；首次 embedding HTTPS 握手超时后相同配方重试成功，模型下载/hash/预热保留原校验。测试依赖摘要继续使用下方命令中的固定值。
- 该次维护镜像/文档 hygiene 3/3 PASS，来源 `/tmp/insightagent-pilot-0209651-hygiene.md` / `.json`；备份计划未修改。
- Compose 全容器重建持久化保留旧 `218f94d` 双镜像基线，来源 `/tmp/insightagent-pilot-218f94d-compose-smoke.log`；该次维护无数据库/持久化/Compose/前端应用变化，未重跑该专项。该次后端门禁 2/2：**2220/2220**、模块 9/9；核心 PostgreSQL/Chroma 11/11，前端保留上一 node 217/217/lint/双构建基线。本机真实模型的合成验收范围单独见[验收记录](real-model-acceptance.md)。

本地镜像 ID 不能充当目标仓库摘要。候选未推送或部署；跨架构、真实模型质量、TLS/访问边界和升级回滚仍未验证。


## 早期 Agent 协议证据

该次应用候选 `218f94d` 的 **7/7 场景通过**：历史问答进入规划/回答且不改写用户消息；新会话不带旧历史；两个同命中数、不同正文的知识库分别驱动 `7*2`/`5*2`，最终回答保留来源和内容版本；首轮空正文仍保存本次 12 token 并回退回答，后续空正文保存两次规划的 24 token 后失败，后续 429 只保留此前 12 token。5 个任务完成、2 个失败；实际 HTTP 请求为 13 次规划/5 次回答，无多余请求或无效请求，失败任务不生成 assistant。Trace/delta/JSON v1.0/Markdown、消息与用量核对通过。成功摘要仅在临时资源清理通过后输出。

原始镜像协议记录 `/tmp/insightagent-pilot-agent-protocol.log`，scope 为 `local_production_protocol_fixture`，Agent 子项为 `local_http_protocol_fixture`。无服务自测 `backend/.venv/bin/python scripts/test_pilot_agent_smoke.py` **9/9**，原 task smoke 自测 **6/6**（含清理失败不输出 PASS）；已进入 `test_ci_e2e_tooling.sh`。该次 tooling **1/1**、hygiene **3/3** PASS，摘要为 `/tmp/insightagent-pilot-agent-{tooling,hygiene}.md` / `.json`。该次维护应用代码及镜像未变，继续保留 2210/217 的完整静态门禁基线；修改的是验证工具与文档。

这项验证证明候选镜像能传递并保存这些协议场景的数据；替身依据预设规则返回结果，不能证明真实模型的推理、引用质量、成本或服务商兼容性。完整浏览器交互、目标 TLS/访问边界及真实模型验收仍使用各自的独立证据。

## 历史 Compose 持久化验证

2026-10-08 旧 `218f94d` 配对的 Compose 持久化验证通过，原始记录为 `/tmp/insightagent-pilot-218f94d-compose-smoke.log`。无服务配置/低敏自测 `scripts/test_pilot_compose.py` 7/7 已纳入 tooling；`compose.pilot.yml` 的变更触发 release-gate/backend-e2e/frontend-e2e，release gate auto 保守选择全部阶段。应用提交的 full release gate 10/10 来源为 `/tmp/insightagent-planning-call-usage-release.md` 与 `.json`，包含后端 2210/2210、module boundary 9/9、前端 217/217、lint 0 error/2 个既有 warning 与 Turbopack/webpack 双构建；该次应用代码未变；当时后端修复后的门禁及新配对来源见上方记录，该次维护未重跑 Compose 持久化。Compose 联调不覆盖多轮模型反馈或全部浏览器交互；模型反馈新增上方镜像 HTTP 协议专项，各 UI 范围保留专项基线。目标镜像拉取、TLS、真实模型、升级回滚及备份恢复仍未验证。
