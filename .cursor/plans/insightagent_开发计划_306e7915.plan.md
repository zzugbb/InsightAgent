---
name: InsightAgent 开发计划
overview: 本地开发与工程收尾已封板，当前按实际问题维护；外部部署、业务资料与用户签收延期。
current_focus:
  mainline: project-completion-audit
  status: 本地封板；外部试点/生产就绪未验收
  latest_change: 2026-10-09 复核五项专项，修复数据库摘要泄漏连接选项，开发 Compose 改为 loopback；三个 README 与全仓文档整理，原始备份计划只读
file_size_baseline:
  boundary: 可维护源码 <= 3000 行；backend slice 主题 <= 2500 行，沿用主题包与 facade
  reference: backend/README.md 的实现入口、docs/development-runbook.md 的规模与门禁规则
stable_contracts:
  - SSE / TraceStep / delta / JSON v1.0 / Markdown 主结构兼容，步骤更新递增 seq；公开结果与诊断继续脱敏
  - 工具使用实际 runner；普通提示故障标记不自动注入异常，canonical mock 仅为明确演示路径
  - 成功状态、回答消息、Trace/usage 同事务提交；终态竞争不覆盖，Memory 和 done 在提交后
  - 首轮规划异常保留规则回退，后续失败按任务错误；非法依赖图整图拒绝，未知用量不补零
  - 多轮 Agent 默认 3 轮/32 节点，DAG 最多128边；绑定仅公开预览标量到 query/expression
  - 工具默认串行，仅就绪内建读取/计算及明确只读 HTTP GET 有界并发，进程最多8读取线程；取消丢弃迟到结果
  - 完整分支为独立会话；checkpoint 仅内建顺序计划，复用和新执行区分，写入并行与 HTTP/DAG checkpoint 延期
  - RAG 后台导入幂等、5000切块预算、分批确认、排队取消和中断复核；跨存储无分布式事务
  - 前端按 step_id/seq 与 normalized 状态消费；输入法 Enter 不发送，布局/ID展示不改变API身份
  - JWT/refresh、用户隔离、共享库权限、Key加密和低敏日志沿用；数据库摘要不包含 query/fragment
  - 长期规则详见 docs/runtime-contracts.md 与技术专题；接口变更按 docs/api-changelog.md 人工判断
validation_baseline:
  current: 后端2/2 PASS，2224/2224、模块9/9；摘要脱敏3/3、预检5/5、Compose入口7/7、故障标记1/1、tooling1/1、hygiene4/4；37份Markdown的216个本地链接通过
  frontend: 103ea1f 应用基线217/217、lint0 error/2既有warning、双构建；本轮未改应用，未重跑完整前端
  browser: 本轮390px登录/注册、任务中心/详情和Failure筛选只读检查；原Trace桌面/手机2/2、布局2/2、完整ID复制、Mac键盘6/6保留
  real_model: 原四场景3/4完整通过，编辑分支恢复1/1；原上下文续算规划回退未执行要求的工具，已知供应商消耗15642 tokens，账单及放弃消耗未知
  images: 旧pilot-42ccf1f / pilot-9e78810未包含当前维护，未重建；原替身联调和持久化范围单独保留
  ci: 1b850bc绿色CI来源用户确认，维护提交未推送，不复用为当前CI结果
  reference: docs/validation-baseline.md、docs/real-model-acceptance.md、docs/pilot-image-evidence.md
completed_mainlines:
  - project-completion-audit：本地开发与工程收尾封板，部署/用户签收/真实业务验收按用户决策延期，已知风险与验证边界保留
  - agent-core-alignment：本地实现/契约封板；有界对话上下文、模型 RAG 证据、Observation 决策、Trace 关系和文件导入，真实模型基础链路与合成 RAG 已验证，业务质量仍待验
  - provider-tool-expansion：provider search 归一化、planner 多协议 tool call、JSON 字符串参数、reconnect 错误码
  - production-runtime-hardening：SSE/failure audit diagnostic、前端审计详情 reason、reconnect provider 错误消息映射，后续运维体验已补 /health.operations 与 release/artifact/trend operator-facing 摘要及契约门禁
  - source-size-maintenance：tool runtime/test slice、chat persistence 与 frontend globals.css 已拆分并纳入规模边界
  - ci-release-engineering：静态 release gate、PR auto routing、summary artifact、readiness matrix、service-backed e2e workflow queue、artifact strict policy
  - product-ux-polish：语义 Trace、normalized 状态/失败诊断、治理与观测列表错误恢复、operator next-action、跨视图知识库往返，以及 Runtime Debug RAG 状态/写入/检索恢复与跨库反馈隔离
  - production-operations-readiness：/health.operations 非敏感运维 readiness、部署/SLO/备份恢复/runbook/演练摘要、warning_summary、risk_domains、readiness_checks 与 readiness_level
  - security-hardening：安全 header、JWT header/默认密钥/CORS 硬阻断、refresh token 输入收敛、认证错误低敏化、auth session 副作用保护与 secret material 默认凭据阻断
  - release-observability-polish：release readiness matrix、artifact retention、release gate summary/trend summary、previous artifact 下载诊断与 release/rollback decision_summary
  - test-maintainability-hardening：四个大测试主题稳定 facade + 双分片、2500 行主题门禁、零匹配诊断、测试预览与六个维护选择器
  - runtime-dependency-modernization：Node 24 ESM、Python 3.14 FastAPI、Next 15.5.25、ESLint CLI flat config、审计安全补丁锁定与最终 service-backed e2e
  - next-major-upgrade-readiness：Next 16.3.5 / React 19.2.8、原生 flat ESLint、React Compiler 规则无例外、Turbopack/webpack 双构建与 full Chromium 验证；ESLint 10 作为上游兼容动作显式保留
next_candidate_mainlines:
  - 按实际复现问题维护，无确认必须新增的功能主线
  - eslint-10-adoption：上游正式兼容后受控升级
next_steps:
  - 当前无必须新增主线；部署、真实业务和用户验收条件具备后单独启动
  - 发布前重建匹配源码镜像，验证目标环境；既有存储未经备份禁止重建
logging_rule: 仅保留当前进度和高信号摘要，技术规则链接专题；每轮同步三个README与本计划，原始备份计划永远不修改。
---

# InsightAgent 实时计划

## 当前状态与范围

本地开发与工程收尾已封板。封板后五项工具/仓库/文案/布局/ID维护已完成，当前复核未发现新的前端代码缺口；本轮修复数据库定位摘要泄漏连接选项，并收紧开发 Compose 的新配置端口发布。没有修改用户模型设置、调用真实供应商、重建镜像或操作既有存储。

三个 README 改为项目、后端和前端的专业入口；补齐架构、配置、契约导航、贡献、安全与验证基线。两份早期运行时 spec/handoff 的有效决策迁入架构，旧流水账删除但 Git 历史可追溯；镜像详细来源迁入独立证据文档。导航见[文档索引](../../docs/README.md)。

## 已完成能力

- 工具驱动 Agent、有界对话上下文、RAG 正文/来源/版本、Observation 反馈、实际执行清单与流式最终回答。
- 可配置 HTTP JSON 执行器、动态 registry/source、Provider 工具规划协议归一化、输入校验与结果投影脱敏。
- Trace 时间线/流程图/语义筛选、任务与会话导出、失败诊断、审计、用量、知识版本治理和文件导入。
- 取消/超时、排队接管、持久导入、完整分支、限定 checkpoint、DAG 与明确只读工具并发。
- JWT / refresh / RBAC-lite、PostgreSQL、Chroma Memory/RAG、低敏请求与调用观测、OpenAPI指纹、发布门禁与隔离e2e。

实现位置、SSE/Trace与Memory/RAG长期参考保留在三个README及[架构](../../docs/architecture.md)/[契约](../../docs/runtime-contracts.md)，不把界面“可解释”宣称为模型内部推理公开。

## 验证与未验收边界

本轮后端2224/2224、模块9/9；前端217/217与双构建沿用103ea1f，无新增前端代码。真实GLM原四场景3/4、编辑分支恢复1/1，原回退问题不被成功分支覆盖。来源与最终文档/hygiene检查见[验证基线](../../docs/validation-baseline.md)。

外部部署、业务资料和用户签收按用户决策延期，不影响本地封板，也不写成外部就绪。旧候选镜像不含当前修改；当前维护提交未推送，绿色CI仍仅属于用户确认的旧基线。

## 下一步

日常维护依据复现问题开展。写入工具并行、HTTP/DAG checkpoint延期，ESLint10待上游兼容；条件具备后单独启动目标部署、存储恢复与真实业务验收。

## 维护约定

- `data/insightagent.plan.back.md` 是原始完整计划，永远只读；不因旧规划自动启动新功能。
- 每轮同步三个 README 与本计划，进度收敛、长期规则保留，避免重复过程流水账。
- 运行/测试/提交遵循[开发运行手册](../../docs/development-runbook.md)，后端用 `backend/.venv/bin/python`；强制纳入 tracked 实时计划。
