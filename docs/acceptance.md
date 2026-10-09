# 验收指南

本机工程检查、真实模型验证、业务签收和部署实证分别记录。当前本地收尾完成，真实业务资料、目标用户和部署环境待提供；本文是可执行指南，不包含未发生的签收。已有结果见[验证基线](validation-baseline.md)与[真实模型记录](real-model-acceptance.md)。

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
