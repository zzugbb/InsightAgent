# 本机统一验收清单

入口：`bash scripts/local_acceptance.sh`（可选参数见 `--help`）。默认**不**消耗真实 glm 用量、**不**重建镜像、**不**触碰已有 PostgreSQL `5432` / Chroma `8001` 数据。

## 推荐命令（Mac）

```bash
cd /path/to/InsightAgent
bash scripts/local_acceptance.sh \
  --materials-dir /path/to/business/materials \
  --questions-file /path/to/questions.json \
  --pilot-url https://your-pilot-host.example.com
```

真实 glm 与镜像重建（可选，先阅读警告）：

```bash
bash scripts/local_acceptance.sh --with-real-glm --with-pilot-image-rebuild
```

报告：`/tmp/insightagent-local-acceptance-report.md`（JSON 同名 `.json`，可用 `--report-md` / `--report-json` 改路径）。报告开头的“仓库状态”和末尾“六项汇报摘要”均在运行时读取：git 分支、提交、upstream ahead/behind、相对 `origin/main` 的提交数、工作区改动计数、备份计划是否改动、阶段计数和本机 `insightagent-*:pilot-*` 镜像；脚本不写死任何历史 PR 信息，也不输出文件内容或密钥。

## 阶段说明

| 阶段 | 命令/依赖 | 预期 | 风险/耗时 | 真实用量 |
| --- | --- | --- | --- | --- |
| health | curl `8000/health`、`3001` | HTTP 200 | 需本机已启动服务；~5s | 否 |
| release_gate | `ci_run_release_gate.sh` hygiene/tooling/backend/frontend | 各 phase PASS | backend full slice 数分钟 | 否（替身/mock） |
| tooling_extra | business RAG / export / pilot drill 静态自测 | PASS | ~1min | 否 |
| business_rag_api | `business_rag_acceptance_runner.py` + token | auto_fail=0 | 依赖真实模型配置时消耗用量 | 是（若 remote） |
| pilot_https | `pilot_https_probe.sh` | health 200 | 只读外网 | 否 |
| real_glm | 文档指引 | 人工记录 | 默认跳过；`--with-real-glm` 开启 | 是 |
| pilot_images | smoke 文档 | 人工/可选 | 默认跳过；重建镜像慢 | 否（替身） |

## 与专项的关系

- PR #1 dev 三浏览器 `composer-keyboard`：需 `npm run dev` + Playwright，未纳入默认 gate（见 runbook）。
- PR #3 规划等待替身：`test_provider_planning_wait_postgres.py` 已含于 backend-e2e；本脚本不重复跑 Docker 专项除非自行添加。
- 项 B/C/D 缺输入时脚本标 `skipped` / `缺输入`，不判失败。

## 安全

不打印 `INSIGHT_AGENT_ACCESS_TOKEN`、完整配置或会话正文。`export_acceptance_evidence.py` 与 RAG 报告仅输出指纹与低敏字段。
