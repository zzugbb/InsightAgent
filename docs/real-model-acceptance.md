# 真实模型配置验收

## 当前结论

2026-10-08，用户已保存的智谱 `glm-5.3` 配置可用。基础连通/计算与真实 Chroma 合成资料的引用/计算已验证；发现并修复未执行工具却声称已验证，以及检索正文错误绑定两处提示缺口。项目收尾仍进行中；真实业务资料质量、整体失败恢复体验、供应商账单成本和目标部署仍待验收。

## 基础配置验证（执行证据修复前）

- 服务：本机开发后端 `127.0.0.1:8000`、前端 `127.0.0.1:3001`，真实 PostgreSQL/Chroma 和远端供应商；当次应用源码与候选镜像来源 `218f94d` 一致，运行方式为原生开发服务，不能计作候选镜像实测。
- 配置：使用用户已经保存的 remote 设置；只读取提供方、模型及 Key 是否可用，不记录 Key、登录凭据或其他会话内容。
- 连通：实际流式请求成功，结束原因 `stop`，23 输入 / 102 输出 / 125 总 tokens，约 4.06 秒。
- 验收会话：`真实模型配置验收 · 2026-10-08`，ID `06a94f04-8c6d-4756-9bb7-8bbf1fbc7979`，保留供工作台复核。
- 低敏结果：`/tmp/insightagent-real-model-configured-tasks.json`；后端服务任务日志 `/tmp/insightagent-real-model-configured-tasks.log`。临时证据不替代本文件的持久结论。

| 入口与场景 | 任务 ID | 结果 | 规划 tokens | 回答 tokens | 总 tokens |
| --- | --- | --- | ---: | ---: | ---: |
| 后端任务服务：17×19 | `f6b9601f-85ea-45e7-b6a8-5728d2347a98` | completed，323 | 873 | 747 | 1,620 |
| 后端任务服务：上轮结果加 7 | `3c075773-7cde-48d4-8f8e-2e7e69219e8d` | completed，330 | 1,617 | 1,171 | 2,788 |
| 登录浏览器工作台发送：23×11 | `293b69e5-2c3e-43ed-95b4-96ac64c10365` | completed，253，UI 显示 done | 1,462 | 535 | 1,997 |

前两条直接调用任务创建/执行服务，真实访问供应商，未覆盖 HTTP 鉴权或浏览器；第三条通过用户授权登录的工作台发送，覆盖页面 → 业务 HTTP → SSE → 回答/Trace 显示。三任务均核对真实模型规划、Calculator 输出、0/1/2 轮历史、成功消息保存、Trace/delta/JSON 一致及 Markdown 导出；结束原因均为 `stop`，后端总用量等于规划加回答。

三任务共 6,405 tokens，加连通验证共 **6,530 tokens**。这是提供方返回的用量，页面估算费用未与供应商账单核对，不作为真实成本结论。原有完整静态门禁与专项测试范围保留，该次未重跑全量门禁，也未变更应用实现；文档验收 hygiene 3/3 PASS，来源 `/tmp/insightagent-real-model-acceptance-hygiene.md` / `.json`，备份计划无变更。

## 剩余验收

1. 将已验证的合成 RAG 场景扩展到目标业务资料，检查引用鲁棒性、冲突版本和无依据问题表现。
2. 用 2–3 个目标业务任务走查质量、可理解性、失败恢复与签收；当前三条合成计算不能代替真实样本。
3. 补供应商账单成本及目标环境的部署、TLS/访问边界、升级回滚、双存储备份恢复与 RPO/RTO 记录。

历史账号的 HTTP 429/到期记录不代表当前配置状态。凭据不进入仓库，备份计划保持只读；状态变更同步四份活跃文档与收尾审计。

## RAG 与执行声明维护

### 修复与契约

- 首轮规划超时后的既有规则回退可能只完成检索；此前真实回答却声称已用 Python 计算工具验证。最终回答现在额外收到成功工具和复用结果清单，不复制输入/原始响应；要求自行推算标为推理，未执行动作明确说明。checkpoint 结果单独标为复用，canonical mock 提示保持原行为。这是模型提示约束，不能保证所有回答绝不误述。
- 真实规划曾绑定检索正文中的预算，运行时正确返回 `tool_dependency_input_unavailable`。内建检索规划提示现声明仅 `hit_count` / `knowledge_base_id` 可绑定；需要正文事实的计算先检索，再由反馈轮给出表达式。仅约束匹配内建 runner 和预览字段的工具，不误限自定义检索；运行时仍拒绝不存在的路径。
- 外部 API、SSE、Trace、JSON v1.0/Markdown、规则回退与用量字段不变。提供方规划超时无用量时保持未知，不从答案补估消耗。

### 当前验证

| 场景 | 任务 ID | 结论 | 已返回 tokens |
| --- | --- | --- | ---: |
| 正文预算 7 → 真实检索、反馈计算 14 | `dfcc2a7a-bd7d-4183-aa4f-b8f969434253` | PASS；来源 `star-sail-guide.md` / `sha256:0816e12da7d64061` | 5,612 |
| 正文预算 5 → 真实检索、反馈计算 10 | `a9b22b66-be93-42c8-9173-57dc39b0dc3c` | PASS；来源 `star-sail-guide.md` / `sha256:0c54ed5d00e3146e` | 5,995 |
| 询问资料未记载的上线日期 | `f0c7487b-c73f-409e-a319-b795771845d4` | 首轮规划约 60 秒超时后规则检索；真实回答明确未记载，来源/版本正确。因验收脚本强制要求真实规划，严格结果 FAIL，不能计入全规划成功 | 2,138（仅已知最终用量） |
| 注入规划超时 → 真实最终回答 | `6a15ac46-9054-4df3-b4c2-f5b8ec1ff384` | 明确没有调用计算工具，14 为自行推算；请求缺口说明正确 | 1,706（仅已知最终用量） |

正常检索/计算 **2/2** 通过，Trace/delta/导出、正文/来源/版本和用量一致；严格三场景报告为 **2/3**，未知日期场景的回答正确但规划回退。正常 RAG 来源 `/tmp/insightagent-real-rag-acceptance-fixed.json` / `.log`；规划失败注入来源 `/tmp/insightagent-real-fallback-acceptance.json` / `.log`，scope 为 `real_final_provider_with_injected_planning_timeout`，不是全程真实规划。修复前证据 `/tmp/insightagent-real-rag-acceptance.json` / `.log` 保留，包含一次规则回退的错误执行声明及一次安全拒绝的绑定错误。

新增执行证据静态 **7/7**（先记录 5 个失败测试再实现）、独立 PostgreSQL/Chroma 核心 **11/11**；后端门禁 **2/2**，full slice **2217/2217**、模块边界 **9/9**。来源 `/tmp/insightagent-execution-evidence-{red,static,postgres,release}.log` 及 release `.md` / `.json`。本轮 hygiene 3/3 PASS，来源 `/tmp/insightagent-execution-evidence-hygiene.md` / `.json`；本机后端已重启加载修复，健康检查与前端访问 HTTP 200。前端未修改，保留上一门禁基线。本次修复已进入后端 `pilot-0209651`，配对未变的前端 `pilot-218f94d` 完成生产模式/禁网 embedding 与 Agent 协议联调；源码摘要相等、测试资源清理通过，来源 `/tmp/insightagent-pilot-0209651-{backend-retry,source-proof,smoke}.log`。本机真实模型实测与镜像本地替身验证分别保留范围，完整候选来源见[试点记录](pilot-deployment-preflight.md)。

真实供应商曾两次首轮规划约 60 秒超时，当前样本不足以证明稳定性、延迟或吞吐承诺。验收会话与独立合成知识库保留供复核；未知消耗与供应商账单仍需核对，不将合成资料计为业务用户签收。

## 规划等待排查（2026-10-08）

本轮只读复核前后两份真实 RAG 日志，未新增供应商请求。`summarize_provider_attempts.py` 现按 `request` / `stream` 输出有效耗时的 count/min/max/mean（毫秒）；缺失、负数、布尔、非数值及非有限耗时不参与统计，单独计数，原有尝试数仍保留。无样本的耗时为 null，不写零。汇总不输出原始字段或正文。

| 日志样本 | 非流式请求数 | 请求 min / mean / max（秒） | 流式请求数 | 流 min / mean / max（秒） | outcome 为 unexpected_error |
| --- | ---: | --- | ---: | --- | ---: |
| 修复前真实 RAG | 4 | 3.096 / 33.304 / 60.081 | 2 | 10.280 / 15.519 / 20.758 | 1 |
| 修复后真实 RAG | 7 | 4.156 / 21.307 / 60.075 | 3 | 22.946 / 27.185 / 32.979 | 1 |

- 源日志 `/tmp/insightagent-real-rag-acceptance{,-fixed}.log`，低敏汇总 `/tmp/insightagent-provider-latency-{before,fixed}.json`；这些数字是 HTTP 尝试耗时，包含错误/回退请求，不是任务延迟、首 token 时间或供应商生成时间。两组任务/规划轮数不同，不能据均值下降宣称修复提升性能。该表作为持久证据，临时日志消失不会推翻既有验收。
- 代码核对：兼容 Provider 默认 `timeout_sec=60.0`；非流式 `urlopen` 与响应读取没有通用重试循环，首轮规划异常进入既有规则回退。两次异常约 60 秒、未返回 status family/usage，与超时记录一致；另一次成功请求耗时 59.094 秒。现有日志不能区分连接等待、读取等待或供应商推理慢，也没有请求/任务关联字段；`unexpected_error` 本身不能确诊 TimeoutError。不能推断总任务数、失败率、账单消耗或供应商根因。
- 当前决策：不延长超时、不新增自动重试；保留首轮回退及未知用量口径。约一分钟规划等待仍是 A1 风险，恢复体验与目标用户可接受等待尚未验收；后续以真实业务任务复核等待、回退可理解性和分支重跑，供应商账单另行核对。
- 本轮修改仅离线工具和测试/文档，应用实现、服务配置与候选镜像不变。耗时专项 `-k provider_attempt` 11/11（新增 3 个），来源 `/tmp/insightagent-provider-latency-static.log`；后端门禁 2/2 PASS（full slice 2220/2220、模块 9/9），hygiene 3/3 PASS，来源 `/tmp/insightagent-provider-latency-{release,hygiene}.md` / `.json`；前端与数据库/镜像专项保留既有验证范围。

## 规划等待与失败恢复（替身复现，2026-10-08）

本轮用本地 Provider/HTTP 替身复现首轮规划阻塞窗口，不请求真实供应商、不延长 60 秒超时、不加自动重试。

| 场景 | 修复前现象（代码核对 + 替身） | 本轮结论 |
| --- | --- | --- |
| 首轮规划耗时数秒 | `state: thinking` 之后同步 `build_tool_plan_artifacts`，期间无 SSE `heartbeat`，也不探测取消 | 规划在线程池执行，主循环按 2s 间隔发 `heartbeat` 并 `force_status_probe` 取消/超时；取消后 `shutdown(wait=False)`，不等待规划线程结束 |
| 规划期间取消 | 取消写入 DB 后仍要等规划返回才 `raise_if_should_abort` | 替身阻塞下取消后约百毫秒级返回 `cancelled`，无工具 Trace |
| 空规划 HTTP 回退 | 既有 `planning_empty_initial` 路径 | `planning_provider_attempted=true`、`planning_provider_used=false`，规划用量 12、overall 19，任务完成 |
| 失败后分支重跑 | 反馈第二轮 429 失败任务 | `POST /reruns` + 子任务 `stream` 完成，父任务保持 failed |

- 验证：`backend/scripts/test_provider_planning_wait_postgres.py` **5/5**（独立 PostgreSQL + 本机 HTTP/离线 Provider；GitHub Actions 使用 `docker` 服务容器、无需 sudo，`task_postgres_fixture` 结束 `docker rm -f -v` 清理）。含「取消后规划线程晚些返回」：任务仍 `cancelled`、Trace/消息/用量 JSON 不被迟到规划改写，放弃调用的 token 不计入任务用量（保持未知）。后端 full slice **2220/2220**、模块 **9/9**、hygiene **3/3**；前端 release gate **217/217**、lint 0 error、Turbopack/webpack 双构建。
- 实现边界：`shutdown(wait=False)` 后供应商 HTTP 仍可能跑完并写 `llm_http_attempt` 观测日志，但不调用 `future.result()`，不更新 Trace/checkpoint/任务 `usage_json`；每流新建 provider，不共享 DB 连接。每轮规划独立 `ThreadPoolExecutor(max_workers=1)`，不堆积线程池。
- `TaskUsageTopTaskRow.governance` 前向引用修正与 GitHub `release-gate`（Python **3.14** 延迟注解求值）同文件已合并于实现提交；云端 **3.12** 导入会 `NameError`，未单独 `fix:` 提交以免改写已推送历史，见 PR 描述。
- 未覆盖：真实 glm-5.3 约 60 秒等待体验、供应商账单、目标部署与候选镜像重建。交付结论仍为 **暂不可交付外部试点**。
