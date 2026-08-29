---
name: InsightAgent 开发计划
overview: provider-tool-expansion 与 ci-release-engineering 已 100% 封板；当前推进 production-runtime-hardening。
current_focus:
  mainline: production-runtime-hardening
  status: 15% 开发中
  latest_change: SSE error payload 追加低敏 diagnostic 摘要，保留旧 code/fatal/retryable/detail/status_code 字段
file_size_baseline:
  scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
  boundary: 可维护源码文件 <= 3000 行
  largest_source: backend/scripts/tool_runtime_slice/planning_provider.py 2923 行
  key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
stable_contracts:
  - 默认 settings 根据 provider/model/api_key 自动选择 remote 或 canonical mock
  - SSE 事件、TraceStep、result summary、safe output、JSON/Markdown export shape 保持稳定
  - SSE error.diagnostic 只包含低敏分类、recoverability、HTTP 状态族与 detail 存在性
  - queued/running/cancel/reconnect 与 task recovery 语义保持稳定
  - data/insightagent.plan.back.md 是只读备份计划，永远不修改
validation_baseline:
  release_gate: bash scripts/ci_run_release_gate.sh --phase auto --summary-file /tmp/release-gate-check.md --json-summary-file /tmp/release-gate-check.json passed，非 PR 保守跑 backend/frontend/tooling/hygiene 全量
  backend: full slice 1984/1984；module boundary 4/4；production_reliability 36/36；reconnect 8/8
  frontend: node tests 122/122；npm run lint passed；npm run build passed
  e2e: backend main passed；frontend full Chromium 52 passed / 1 skipped；backend/frontend queue 已纳入 CI workflow
  hygiene: py_compile、git diff --check、git diff --cached --check、backup plan diff clean
completed_mainlines:
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - source-size-maintenance：tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界
  - ci-release-engineering：静态 release gate、PR auto routing、summary artifact、readiness matrix、service-backed e2e workflow queue、artifact strict policy
next_candidate_mainlines:
  - product-ux-polish：Workbench/Task Center 高频操作、trace 回放可读性与治理页面效率
next_steps:
  - 继续收敛 provider registry 运行态诊断、远端 provider 失败可观测性与发布后回归策略
logging_rule: 本文件只保存当前状态、验证基线、稳定契约与候选主线，不记录轮次流水账。
---
