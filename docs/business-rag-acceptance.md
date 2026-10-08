# 真实业务 RAG 验收工具包

## 状态

**待外部验收（缺真实业务资料）**。仓库内合成样本仅用于 VM/CI 自测，不能代替用户在目标业务资料下的质量签收。

## 用途

在用户提供资料目录与问题清单后，于本机一次跑完：

1. 导入到独立 `knowledge_base_id`（默认 `acceptance-toolkit-<随机>`，不触碰开发用默认库）。
2. 逐题创建任务并等待 SSE 完成。
3. 自动核对：引用来源、回答是否明确“未记载”、Trace 中实际执行工具与回答中的工具声明、用量是否已知。
4. 输出不含正文与密钥的 `report.md` / `report.json`，区分 `auto_pass` / `manual_review` / `auto_fail`。

## 问题清单格式

见 `scripts/fixtures/business_rag_acceptance/synthetic/questions.json`。`checks.auto` 支持：

| kind | 含义 |
| --- | --- |
| `citation_source` | Trace 检索元数据包含指定 `source` |
| `answer_contains` | 回答包含子串（报告中只记录子串哈希） |
| `answer_not_documented` | 回答含“未记载/未提及”等明确措辞 |
| `tool_executed` / `tool_not_executed` | Trace 工具名 |
| （内置）`tool_claim_vs_trace` | 回答声称计算但 Trace 无 `calc_eval` 等 |

`checks.manual` 字符串列表进入报告，需人工判断（例如真实模型规划是否超时回退）。

资料目录：递归读取 `.md` / `.txt`，文件名作为 `source` / `document_id`。

## 本机（真实模型 / 已启动服务）

```bash
export INSIGHT_AGENT_ACCESS_TOKEN="<工作台登录后 access token，勿提交仓库>"
backend/.venv/bin/python scripts/business_rag_acceptance_runner.py \
  --api-base-url http://127.0.0.1:8000 \
  --materials-dir /path/to/your/materials \
  --questions-file /path/to/questions.json \
  --output-md /tmp/insightagent-business-rag-acceptance/report.md \
  --output-json /tmp/insightagent-business-rag-acceptance/report.json \
  --cleanup
```

`--cleanup` 会删除本次创建的知识库；不加则保留供人工复核。脚本不读取或打印 token。

## VM 自测（合成样本 + 替身）

```bash
backend/.venv/bin/python scripts/business_rag_acceptance_runner.py --self-test
# 或
backend/.venv/bin/python scripts/test_business_rag_acceptance.py
```

使用独立 Docker PostgreSQL/Chroma，结束后删除容器与测试集合。

## 与既有验收的关系

前轮[真实模型验收](real-model-acceptance.md)中的合成 `star-sail-guide` 场景为手工/临时脚本证据；本工具包将同类检查产品化为可重复入口，**不覆盖**真实 glm 账单、规划超时体验或业务用户签收。
