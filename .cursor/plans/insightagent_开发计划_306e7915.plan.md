---
name: InsightAgent 开发计划
overview: provider-tool-expansion 已 100% 封板；当前进入 ci-release-engineering，先建立不启动服务的发布前门禁。
current_focus:
  mainline: ci-release-engineering
  status: 10% 开发中
  next_candidate: release/e2e 分层编排、失败诊断收敛、发布前检查文档化
  latest_change: 新增 scripts/ci_run_release_gate.sh 与 .github/workflows/release-gate.yml，聚合 backend/frontend/tooling/hygiene 静态门禁
  file_size_baseline:
    scope: backend/app、backend/scripts 与 frontend 源码；排除 package-lock.json 等生成锁文件
    boundary: 可维护源码文件 <= 3000 行
    largest_source: backend/scripts/tool_runtime_slice/planning_provider.py 2923 行
    key_facades: tool_runtime_execution.py 2864、tool_runtime_registry.py 2768、tool_runtime.py 2547、tool_runtime_http_json.py 2522、frontend/app/globals.css 7
    extracted_modules: chat_persistence_trace_export、chat_persistence_usage、tool_runtime_display、tool_runtime_execution_flow、tool_runtime_registry_settings、registry_runtime、http_json_response、http_json_execution、registry_public
    frontend_styles: theme-base、workbench-shell、messages-composer、inspector-trace、tasks-governance、responsive-markdown、settings-model
constraints:
  - 永远不修改 data/insightagent.plan.back.md
  - 先补 failing test，再改实现
  - 保持 SSE / trace / export / e2e 契约稳定
  - 单文件明显膨胀时先拆主题文件/模块
  - 测试、e2e、启动、提交先参考 docs/development-runbook.md
  - backend 使用 backend/.venv/bin/python
validation_baseline:
  release_gate: scripts/ci_run_release_gate.sh --phase all passed
  backend_full_slice: backend/scripts/test_tool_runtime_slice.py 1983/1983
  backend_targeted: registry 534/534; http_json 531/531; provider 538/538; runtime 163/163; trace 188/188; export 184/184; usage 63/63
  module_boundaries: backend/scripts/test_tool_runtime_module_boundaries.py 4/4，含后端 3000 行规模边界
  frontend: node tests 122/122; npm run lint; npm run build; source-file-size boundary
  e2e_baseline: backend main passed; frontend full Chromium 52 passed / 1 skipped; targeted Chromium workbench-main-path 5/5
  hygiene: py_compile; git diff --check; backup plan diff clean
stable_contracts:
  - 默认 settings 根据 provider/model/api_key 自动选择 remote 或 canonical mock
  - SSE 事件、TraceStep、result summary、safe output、JSON/Markdown export shape 保持稳定
  - queued/running/cancel/reconnect 与 task recovery 语义保持稳定
completed:
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - runtime split：tool_runtime facade、planner、execution、registry、HTTP JSON、chat persistence 与测试 slice 已按主题分模块
  - frontend style split：globals.css 保持 import facade，主题样式迁移到 frontend/app/styles
  - ci-release-engineering kickoff：release gate 脚本与 GitHub Actions workflow，默认不启动服务、不替代 service-backed e2e
next_steps:
  - 继续收敛 release/e2e 分层：区分快速静态门禁、service-backed e2e、artifact/diagnostics 守卫和 main push 严格度
  - 新 CI 变更继续先红测，再跑 release gate 与必要 e2e；不扩大 SSE / trace / export 外部契约
logging_rule: 本文件只保存当前状态、验证基线、稳定契约与少量下一步，不记录轮次流水账。
---
