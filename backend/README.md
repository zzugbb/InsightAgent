# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式作为默认演示路径，同时支持 OpenAI-compatible `remote` 模式；覆盖任务流、轨迹、PostgreSQL 会话持久化、用户级鉴权、Memory 与 RAG。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3：已完成（mock 范围）
- W4：已完成（RAG + Token/Cost + compose.full）
- 阶段 5 增量：`full-data-auth` 首版已落地（JWT、用户隔离、用户级设置与密钥加密存储）
- 阶段 5 增量（2026-05-09）：`RBAC-lite` 基础已落地（`users.role` 字段、首个注册用户自动 admin、`require_user_roles` 依赖、admin-only `GET /api/auth/users`）
- 阶段 5 增量（2026-05-09）：`rag-rbac-lite` 已落地：`shared-*` 共享知识库命名空间 + 角色化权限（admin 可写共享库，普通用户对共享库只读；个人知识库继续按 `user_id` 隔离可读写）
- 阶段 5 增量：最小会话管理已落地（refresh token 轮换、会话查询/撤销、退出当前/全部会话）
- 阶段 5 增量：审计事件扩展已落地（`login/logout/refresh/settings_update/settings_validate/task_create/task_cancel/task_timeout/task_failed/rag_ingest/rag_kb_clear/rag_kb_delete` 写入 `audit_logs`）
- 阶段 5 增量：PostgreSQL 迁移主线已完成运行时收敛（后端运行时使用 PostgreSQL + 保留平迁脚本）
- 阶段 5 排查修复（2026-04-14）：修复 PostgreSQL 下 `POST /api/tasks` 的 `CASE WHEN` 参数类型错误（smallint -> boolean），恢复消息发送链路
- 阶段 5 排查补充：已复核 `sessions/tasks/messages/settings/rag` 查询与写入路径，核心数据均按 `user_id` 隔离
- 会话命名补充：空会话在首条消息发送时，若仍为占位标题则自动改为首条消息前缀
- 会话命名规则补充：仅在“无历史消息 + 占位标题”条件下自动命名，不覆盖用户手动重命名
- 协同进展（前端侧）：已完成登录表单填充态样式优化、密码显隐图标可见性与切换修复、登录页左侧文案（主页叙事 + 关键信息）收口、退出入口并入左下角设置模块
- 协同进展（前端侧）：已完成登录页国际化接入（Auth Gate 新增 `auth` 文案分组并覆盖中英文）
- 协同进展（前端侧）：已完成登录页设置模块（语言/主题/主题色）与主题/主题色联动适配
- 协同进展（前端侧）：已移除首次引导页；新用户登录后直接进入工作台，未配置模型时沿用用户默认设置（通常 `mock`）
- 工程协作：前端 `npm run lint` 已可直接执行，且当前告警已清零
- 协同进展：前端已切换到后端 usage 聚合接口（全局/会话双范围），并显示覆盖率与状态反馈（loading/error/empty）
- 协同进展：前端审计页已升级为分页表格可读视图（双行下拉+输入检索且控件尺寸统一、操作区右对齐、表格下方总数展示、事件标签区分、会话/任务 ID 展示、行展开明细，分页默认每页 10 条），继续复用现有 `GET /api/audit/logs` 契约
- 协同进展：前端已收口弹窗状态管理（审计日志/模型设置每次打开重置状态），避免旧筛选与旧提示跨次污染
- 协同进展：模型设置弹窗已改为“打开按后端配置回显 + 禁用浏览器自动填充”，避免浏览器凭证误填并保留可读回显
- 协同进展：前端右侧 Inspector（Context）已收敛为运行态核心分区（概览/同步诊断/当前任务），后端现有字段可直接支撑后续模块扩展
- 协同进展：前端任务索引已支持本地状态筛选/时间排序/失败置顶，不新增后端接口负担
- 协同进展：前端任务索引已支持标题/ID 快速检索与失败摘要提示（由现有任务字段推导），无需新增后端接口
- 协同进展：前端 Trace 面板已支持步骤类型筛选/关键词检索/类型计数，复用现有 TraceStep 字段，无需新增后端接口
- 协同进展：前端右侧 Inspector 已完成一体化收口（Trace 密度、Context 快速跳转、状态徽标），均基于现有字段推导，无需新增后端接口
- 协同进展：`full-trace-session-lite` 首个前端切片已接入（任务快照：prompt/最终回答摘要/最终观察/RAG 命中/状态与失败提示），复用现有 `GET /api/tasks` + `GET /api/tasks/{task_id}/trace` 契约，无需新增后端接口
- 协同进展：`full-trace-session` 首步收口已接入任务详情独立页（前端 `/tasks/[taskId]`），复用 `GET /api/tasks/{task_id}`、`GET /api/tasks/{task_id}/trace` 与既有导出接口，无需新增后端接口
- 协同进展：`full-trace-session` 重排收口已接入（前端中栏恢复聊天主视图 + 右侧任务中心抽屉）；右侧 Inspector 聚焦运行态，任务索引/筛选/搜索由抽屉承载，继续复用 `GET /api/tasks` 既有契约，无需新增后端接口
- 协同进展：`full-trace-session` 清理收口已完成；前端 Inspector 旧任务块代码已物理删除，任务分析入口统一为任务中心与任务详情页，后端接口契约保持不变
- 协同进展：`full-trace-session` 二次迁移已完成；会话导出入口迁移至左侧会话行“...”菜单（方案 1），Memory/RAG 调试迁移至设置弹窗“运行调试”，后端接口契约保持不变
- 协同进展：`full-trace-session` 交互细化已完成；运行调试弹窗样式与全站风格统一，任务中心“任务详情”按钮增强，Inspector 当前任务仅保留取消操作；后端接口契约保持不变
- 协同进展：任务中心抽屉头部已移除模式/模型展示，仅保留右侧关闭按钮；属前端展示层收口，后端接口契约保持不变
- 协同进展：任务中心列表已切换为“审计日志同款”表格分页风格（筛选/搜索 + 表格 + 分页），继续复用现有 `GET /api/tasks` 契约，无需新增后端接口
- 协同进展：任务中心顶部筛选/搜索区已进一步对齐审计日志双行布局与控件风格；仅前端展示层调整，后端接口契约保持不变
- 协同进展：任务中心“全局任务”条数对齐已通过前端完整分页拉取修复（避免首屏截断造成数量偏小）；“用量来源”列与任务详情按钮样式属前端呈现调整，后端接口契约保持不变
- 协同进展：`full-trace-session` 样式微调已完成；运行调试弹窗改为上下单列并移除分区高亮底色，后端接口契约保持不变
- 协同进展（2026-05-08）：前端 `Workbench` 任务中心抽屉已将 Ant Design `Drawer` 的 `width` 属性迁移为 `size`，消除 antd 6 废弃警告；后端接口契约保持不变
- 协同进展（2026-05-08）：前端已将任务详情导出与会话导出的下载实现收口到共享工具（`frontend/lib/export-download.ts`），统一鉴权下载错误语义与附件文件名解析；后端导出接口契约保持不变
- 协同进展（2026-05-09）：前端知识库治理弹窗已接入 `currentUser.role`，普通用户对 `shared-*` 知识库清空/删除按钮禁用，并通过统一权限提示与后端 `403` 语义对齐
- 协同进展（2026-05-09 补充）：前端 Playwright 已新增“非 admin 用户在 `shared-*` 知识库行上 clear/delete 按钮禁用”回归用例，验证 UI 权限态与后端角色化规则一致
- 协同进展（2026-05-09 再补充）：前端 `workbench-main-path` 主链路也已补同语义断言（非 admin 共享库 clear/delete 禁用，私有库按钮保持可用），避免仅在单独 spec 覆盖而主链路遗漏
- 协同进展：前端 Playwright 回归已对齐新入口（任务中心抽屉 + 新标签任务详情导出），旧的 Inspector 任务导出断言已替换；后端导出接口契约保持不变
- 协同进展：`trace-export-json-md` 首版已接入；新增 `GET /api/tasks/{task_id}/export/json` 与 `GET /api/tasks/{task_id}/export/markdown`，导出包含任务元信息、task-linked 消息、TraceStep、RAG chunks、usage
- 协同进展：`session-export-lite` 首版已接入；新增 `GET /api/sessions/{session_id}/export/json` 与 `GET /api/sessions/{session_id}/export/markdown`，导出包含会话消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage 汇总
- 阶段 5 增量：`remote-provider-hardening` 首轮已完成；Provider 运行时统一输出结构化错误码（401/403、429、5xx、网络、无效 JSON、空响应、SSE 中断），任务流 SSE `error` 事件透传 `code/fatal/retryable/detail/status_code`
- 阶段 5 增量：`task-cancel-timeout` 首版已落地；新增取消接口与超时中断，任务流支持 `cancelled/timeout` 事件
- 阶段 5 增量：`task-cancel-timeout` e2e 已补齐；新增 `scripts/e2e_task_cancel_timeout.py`，覆盖取消链路与超时链路（低 `TASK_TIMEOUT_SEC` 环境）
- 阶段 5 增量（2026-05-09）：`e2e_main_path` 已补共享知识库权限回归（`shared-*` 普通用户写操作 `403`、共享库读能力稳定；若当前 e2e 账号具备 admin 权限则追加 admin 写共享库成功断言）
- 阶段 5 增量：导出稳定性 e2e 已补齐；新增 `scripts/e2e_export_consistency.py`，覆盖任务/会话导出 JSON+Markdown 一致性、下载附件头、跨用户导出隔离 404 与不存在资源 404
- 阶段 5 增量（2026-05-08）：`e2e_export_consistency` 新增导出 `Content-Type` 断言（JSON=`application/json`、Markdown=`text/markdown`，含 `download=true`），补强导出响应协议回归覆盖
- 阶段 5 增量（2026-05-09 补充）：`e2e_export_consistency` 新增 `shared-*` 跨角色断言（非 admin 写共享库 `403`；当前账号为 admin 时补充“admin 写后普通用户可 query 命中”），确保共享库权限变更与导出回归脚本协同稳定
- 工程化增量：后端 e2e CI 已扩展（`.github/workflows/backend-e2e.yml` 覆盖 `baseline/main-path/export-consistency/cancel-timeout`，已升级 `checkout`/`setup-python` 主版本以适配 GitHub Actions Node 24 运行时；Python **3.14** 与 `compose.full.yml`、根目录 `.python-version` 对齐）；并补失败快照归档（e2e 脚本输出落盘 + health/诊断采集 + artifact 上传）
- 工程化增量（2026-05-08）：`backend-e2e` 新增 export consistency 摘要步骤，CI Summary 会输出关键检查点快照并归档 `/tmp/e2e-export-consistency-summary.txt`；并新增断言计数统计（steps/ok/pass/task-export/session-export/shared-rag/cross-user/not-found）用于快速定位回归类别；失败诊断中同步输出导出一致性日志 tail，便于回归定位
- 工程化增量（2026-05-09）：`backend-e2e` export consistency 摘要阈值已与脚本 7 步输出对齐（`steps/ok` 期望从 6 调整为 7），并新增 `shared_rag_semantics_ok` 计数项，覆盖 `shared-*` 权限语义回归
- 工程化增量（2026-05-09 再补充）：`backend-e2e` export consistency 的步数阈值已改为动态解析（从首条 `[x/N]` 自动提取 `N`），避免脚本增减步骤时 workflow 需要手工同步硬编码
- 工程化增量（2026-05-09 维护性补充）：`backend-e2e` export consistency 摘要新增 `add_warning` 统一告警函数，集中处理 `P0/P1` 计数与告警消息拼装，降低后续阈值项扩展的重复改动成本
- 工程化增量（2026-05-09 工程化重构）：`backend-e2e` export consistency 摘要已从 workflow 内联脚本抽离到 `backend/scripts/ci_export_consistency_summary.sh`，workflow 仅保留脚本调用与 `GITHUB_STEP_SUMMARY` 拼接，提升可维护性与本地复跑便利性
- 工程化增量（2026-05-09 回归护栏补充）：新增 `backend/scripts/test_ci_export_consistency_summary.sh` fixture 自测并接入 `backend-e2e`（`Validate export consistency summary fixture tests`），覆盖成功/缺陷/日志缺失三类诊断语义
- 工程化增量（2026-05-09 机器可读补充）：`backend/scripts/ci_export_consistency_summary.sh` 新增可选 JSON 输出参数，workflow 已产出 `/tmp/e2e-export-consistency-summary.json` 并随 artifact 上传
- 工程化增量（2026-05-09 统一门禁补充）：新增仓库级 `scripts/ci_diag_guard.sh`（含 `scripts/test_ci_diag_guard.sh`），`backend-e2e` 已接入 `Evaluate export diagnostics guard` 步骤；可通过 `BACKEND_EXPORT_DIAG_STRICT_LEVEL=none|p0|any` 控制门禁严格度（默认 `none`）
- 工程化增量（2026-05-09 统一门禁再补充）：`backend-e2e` 默认门禁级别已提升为 `p0`，并在 `GITHUB_STEP_SUMMARY` 追加 `backend-e2e export diagnostics guard` 小节（含 scope/strict/warnings/gate_result），同时归档 `/tmp/backend-e2e-export-guard-summary.md`
- 工程化增量（2026-05-09 门禁策略化补充）：`backend-e2e` 的门禁级别已改为按事件自动决策（`push@main=any`，其余场景 `p0`），并在 summary 输出 `policy + selected_strict_level`，减少“当前门禁为什么生效”为何值的排查成本
- 工程化增量（2026-05-09 门禁 JSON 补充）：`ci_diag_guard` 已支持 `--json-summary-file`，`backend-e2e` 现产出 `/tmp/backend-e2e-export-guard-summary.json` 并上传 artifact，便于后续机器汇总门禁结果
- 工程化增量（2026-05-09 触发覆盖补充）：`backend-e2e` 的 `workflow_dispatch` 新增 `export_diag_strict_level=auto/none/p0/any`，手动触发可覆盖门禁策略；summary 额外输出 `dispatch_override` 与 `policy_source`
- 工程化增量（2026-05-09 总览聚合补充）：新增 `scripts/ci_export_diagnostics_overview.sh` 与 `scripts/test_ci_export_diagnostics_overview.sh`，`backend-e2e` 已接入 overview 生成步骤并产出 `/tmp/backend-e2e-export-overview.md/.json`
- 工程化增量（2026-05-09 策略解析收口）：新增 `scripts/ci_resolve_diag_strict_level.sh` 与 `scripts/test_ci_resolve_diag_strict_level.sh`，`backend-e2e` 的 strict-level 选择逻辑改为调用脚本解析，统一 `event/ref/default/main_push/dispatch_override` 决策口径
- 工程化增量（2026-05-09 fixture 入口收口）：新增 `scripts/test_ci_e2e_tooling.sh` 聚合测试入口，`backend-e2e` 已改为单步骤 `Validate e2e tooling fixtures (backend scope)`，统一执行 common + backend 相关 fixture 测试
- 工程化增量（2026-05-09 流水线收口）：新增 `scripts/ci_export_diag_pipeline.sh` 与 `scripts/test_ci_export_diag_pipeline.sh`，统一执行 strict-level 解析、guard 判定、overview 生成与 summary 拼接；`backend-e2e` 已切换为单步骤 `Run export diagnostics pipeline`
- 工程化增量（2026-05-09 日志降噪补充）：`scripts/ci_diag_guard.sh` 增加 `--quiet`，并在 guard/resolver fixture 中收敛预期失败输出，减少 CI fixture 日志噪音
- 工程化增量（2026-05-09 启动验活收口）：新增 `scripts/ci_start_bg_process.sh` 与 `scripts/ci_wait_http_status.sh`（配套 `scripts/test_ci_service_bootstrap.sh`），`backend-e2e` 的 `:8000/:8010` 后端启动与健康等待已统一为脚本调用，减少 workflow 重复 shell 片段
- 工程化增量（2026-05-09 诊断流程再收口）：新增 `scripts/ci_export_diag_flow.sh` 与 `scripts/test_ci_export_diag_flow.sh`，将 `export consistency` 摘要生成与后续 guard/overview pipeline 合并为单入口；`backend-e2e` 已切换为 `Run export diagnostics flow`
- 工程化增量（2026-05-09 artifact 收口）：新增 `scripts/ci_artifacts_backend.txt` 与统一归集脚本 `scripts/ci_stage_artifacts.sh`（配套 `scripts/test_ci_stage_artifacts.sh`）；`backend-e2e` 新增 `Stage backend e2e artifacts`，上传动作改为 staging 目录，减少 workflow 内长路径清单维护分叉
- 工程化增量（2026-05-09 失败诊断脚本化）：新增 `scripts/ci_collect_backend_failure_diagnostics.sh`（配套 `scripts/test_ci_collect_backend_failure_diagnostics.sh`），`backend-e2e` 的 `Collect diagnostics on failure` 已改为脚本调用，统一时间戳/进程快照/health/导出日志 tail 的输出结构
- 工程化增量（2026-05-09 执行入口收口）：新增 `scripts/ci_run_backend_e2e.sh`（配套 `scripts/test_ci_run_backend_e2e.sh`），`backend-e2e` 的 main/timeout 执行步骤已改为脚本调用；脚本支持 `--phase main|timeout` 与 `--dry-run`，便于本地复跑与参数演进
- 工程化增量（2026-05-09 backend 启动收口）：新增 `scripts/ci_boot_backend_instance.sh`（配套 `scripts/test_ci_boot_backend_instance.sh`），将 `backend-e2e` 的 `:8000/:8010` 启动与健康等待收敛为单入口脚本，降低 workflow 分步维护复杂度
- 工程化增量（2026-05-09 finalize 编排收口）：新增 `scripts/ci_finalize_e2e_scope.sh`（配套 `scripts/test_ci_finalize_e2e_scope.sh`），将 `backend-e2e` 的 diagnostics flow 与 artifact stage 合并为单步骤调用，降低收尾阶段参数分叉风险
- 工程化增量（2026-05-09 失败日志展示收口）：新增 `scripts/ci_print_log_files.sh`（配套 `scripts/test_ci_print_log_files.sh`），`backend-e2e` 的失败日志展示步骤已改为脚本调用，统一文件缺失兜底与输出格式
- 工程化增量（2026-05-09 upload 路径解耦）：`ci_finalize_e2e_scope.sh` 新增 `--github-output-file` 输出，`backend-e2e` 的 upload path 改为读取 `finalize_backend.outputs.artifacts_stage_dir`，减少 YAML 中 stage 目录硬编码
- 工程化增量（2026-05-09 upload 命名解耦）：`backend-e2e` 的 upload `name` 字段改为读取 `finalize_backend.outputs.artifact_name`；artifact 命名与 staging 路径现统一由 finalize 输出驱动
- 工程化增量（2026-05-11 finalize workflow 入口收口）：新增 `scripts/ci_finalize_e2e_for_workflow.sh`（配套 `scripts/test_ci_finalize_e2e_for_workflow.sh`），`backend-e2e` 的 finalize 步骤已改为单入口脚本调用，统一 strict-level 默认值、事件上下文与 artifact 命名参数解析
- 工程化增量（2026-05-11 artifact stage 指标补齐）：`ci_finalize_e2e_scope.sh` 现在会输出 `artifact_included_count/artifact_missing_count/artifact_manifest`，并在 summary 追加 `backend-e2e artifact stage` 小节，便于快速判断 artifact 缺失来源于 staging 还是 upload 阶段
- 工程化增量（2026-05-11 artifact stage 门禁补齐）：新增 `scripts/ci_assert_artifact_stage_health.sh`（配套 `scripts/test_ci_assert_artifact_stage_health.sh`），`backend-e2e` 新增 `Evaluate backend artifact stage guard` 步骤并产出 `/tmp/backend-e2e-artifact-guard-summary.md/.json`，默认 `strict-level=warn` 可在后续按需升级
- 工程化增量（2026-05-11 artifact stage 策略解析收口）：新增 `scripts/ci_resolve_artifact_stage_strict_level.sh`（配套 `scripts/test_ci_resolve_artifact_stage_strict_level.sh`），`backend-e2e` 的 artifact guard strict-level 已改为脚本按事件自动解析，并支持 `workflow_dispatch` 输入覆盖（`auto/none/warn/fail-on-empty/fail-on-missing`）；当前策略为 `push@main=warn`、其余 `warn`
- 工程化增量（2026-05-11 artifact stage 防误伤补丁）：`backend-e2e` 的 artifact guard 改为仅在 `finalize_backend` 成功时执行；当 finalize 失败时写入 `skipped` 摘要而不追加二次失败，便于聚焦首个根因
- 工程化增量（2026-05-12 artifact stage PR 门禁扩展）：`backend-e2e` 的 artifact guard 现支持 `min_included_count` 阈值，并将 `pull_request` 场景扩展为可选 `fail-on-empty` 策略源；当前 workflow 已为 PR/关键分支场景启用 `fail-on-empty + min_included_count=2`，同时保留 `push@main=warn` 以兼容既有单产物路径
- 工程化增量（2026-05-12 artifact upload 防二次报错补丁）：`backend-e2e` 的 upload 步骤改为仅在 `finalize_backend` 成功时执行，避免 finalize 失败后继续触发 `actions/upload-artifact` 的空 path 报错；并新增 `scripts/test_ci_workflow_guards.sh` 静态校验 workflow guard 条件
- 工程化增量（2026-05-12 artifact PR 路径感知扩展）：`backend-e2e` 新增 `ci_resolve_artifact_stage_path_level.sh`、`ci_collect_changed_files.sh` 与 `ci_resolve_artifact_stage_scope_config.sh`，PR 只有在命中 backend/compose/workflow 关键路径时才升级 artifact guard；workflow 已统一通过 scope 配置脚本解析 changed-files 路径、fallback paths 与 path-regex，`actions/checkout` 使用 `fetch-depth: 0`，并在 base diff 不可解析时回退关键路径标记。同时 path-regex 已修正为可命中真实 `backend/...` 改动与关键单文件路径，降低浅克隆、缺失 base SHA 与旧正则过窄带来的误判概率
- 工程化增量（2026-05-11 fixture 稳定性修复）：`scripts/test_ci_finalize_e2e_for_workflow.sh` 的缺失事件上下文断言改为显式清空 `GITHUB_EVENT_NAME/GITHUB_REF` 后执行，修复 CI 环境默认变量导致的 `expected fail but passed` 假阳性
- 工程化增量（2026-05-08 补充）：`backend-e2e` export summary 已新增阈值告警输出（`Threshold alerts`），当计数不满足预期时会打印异常项明细（expected vs actual），便于在 CI Summary 直接识别导出链路回归层级
- 工程化增量（2026-05-08 再补充）：`backend-e2e` 阈值告警已增加严重级别标签（`[P0]/[P1]`）与 `severity` 计数，便于团队按优先级分流处理导出回归
- 工程化增量（2026-05-08 再补充）：`backend-e2e` 告警模板已与 `frontend-e2e` 对齐为 `total_alerts -> severity -> 分级明细`，并采用作用域标签格式（`[P*][backend-export-consistency]`）
- 工程化增量（2026-05-08 再补充）：`backend-e2e` 导出诊断 regex 已收口为变量块（计数规则 + `key lines` 规则），减少 `grep` 模式在多处重复定义带来的维护分叉
- 协同进展：前端可视化回归 CI 首版已接入（`.github/workflows/frontend-e2e.yml` + Playwright 用量统计主路径 smoke），复用后端 `:8000` mock 主链路运行环境
- 协同进展：`frontend-e2e` 工作流已升级 `actions/setup-node@v5`、`actions/upload-artifact@v7`，并设置 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` 以对齐 GitHub Actions Node 24 策略
- 协同修复：Playwright 用例登录态注入从“浏览器上下文直接引用常量”改为“显式透传 storage key”，避免前端回归在未登录页误失败（后端接口无需改动）
- 协同修复（补充）：`usage-dashboard` Playwright 用例新增 UI 登录兜底（发现未进入 Workbench 时自动登录），降低 CI 冷启动状态差异对回归稳定性的影响
- 协同进展（补充）：前端 Playwright 回归已扩展覆盖设置治理入口（审计日志/知识库治理弹窗可见性），并为设置菜单项补充稳定 `data-testid`，后端接口契约无需改动
- 协同进展（补充二次）：前端 Playwright 回归新增 `workbench-main-path` 场景并跑通（对话发送、Trace、RAG ingest/query、任务/会话导出、运行中任务刷新恢复与取消后重发）
- 协同进展（补充三次）：前端 Playwright 回归新增 `workbench-edge-cases` 场景（RAG 空命中可见性 + 缺失任务/会话导出 `404` 语义断言），并抽出 e2e 公共 helper（鉴权注入/Workbench 就绪）；随后新增 remote 错误映射场景并完成本地回归：chromium 全量 `25/25`、smoke 矩阵 `15/15`
- 协同进展（2026-05-08）：前端 `workbench-edge-cases` 新增“导出下载响应头一致性”回归，覆盖 task/session JSON/Markdown `download=true` 的 `Content-Type` 与 `Content-Disposition` 扩展名匹配
- 协同进展（2026-05-08）：前端 `workbench-main-path` 已补“UI 下载 + 同路径 API 响应头”双重断言，主链路导出覆盖 task/session JSON/Markdown 的 `Content-Type` 与附件扩展名一致性
- 协同进展（细粒度断言）：前端 usage/知识库治理/回底按钮回归已补稳定测试锚点（`data-testid`），并覆盖来源筛选请求参数、表头左对齐、治理动作无边框文本按钮、滚动交互显隐等高频回归点
- 协同进展（异常态深化）：前端 `workbench-remote-errors` 已补 remote `503` 错误码映射与“取消后发送冷却恢复”回归；通过本地 mock OpenAI-compatible 流服务验证冷却期阻断重发、冷却结束恢复发送，后端接口契约无需变更
- 协同进展（设置校验异常态）：前端 Playwright 已新增 `settings/validate` 回归，覆盖 `remote_api_key_unauthorized` 与 `remote_preflight_network_error`；并通过 `model-settings-*` 稳定测试标识降低跨语言/提示时序抖动，后端设置接口契约保持不变
- 协同进展（流式异常态）：前端 Playwright 已新增 `remote_provider_stream_invalid_json` 与 `remote_provider_stream_interrupted` 回归，并完成 Context tab 断言稳态修复（重试点击直到 Context 面板可见）；后端 remote 错误码契约保持不变
- 协同进展（导出异常态补齐）：前端 Playwright 已补齐“空会话导出 JSON/Markdown”与“跨用户导出隔离 404（task/session）”回归，后端导出权限隔离与空数据语义已有自动化兜底
- 协同进展（导出错误提示一致性）：前端导出链路已统一走 `ApiError` 映射，导出 404 不再直接暴露后端原始 detail；并新增 UI 回归断言提示与按钮恢复，后端接口契约无需变更
- 协同进展（矩阵）：`frontend-e2e` 工作流新增 smoke 三浏览器（chromium/firefox/webkit）+ chromium 全量分层执行，兼顾反馈速度与兼容性覆盖
- 协同进展（恢复稳态补丁）：前端 `workbench-main-path` 已加固“先确认后端任务进入 running/pending 再刷新”与“等待取消按钮时持续保持 Context 激活”两层断言，规避恢复链路切回 Trace 的时序抖动
- 协同进展（一次性补齐）：前端 `workbench-edge-cases` 新增“取消后同文案立即重发不丢消息”“跨会话流式状态严格隔离且切回可取消”“mock 取消后无重试入口且可快速恢复发送”三条回归；本地全量回归最新为 chromium `25/25`
- 协同进展（六项补齐）：前端一次性补齐“恢复提示三态、trace delta 重试与后台暂停恢复、auth refresh+logout-all、设置弹窗重开状态重置”回归；最新本地结果为 chromium 全量 `30/30`、smoke 矩阵 `15/15`。
- 协同进展（CI 稳定性）：`frontend-e2e` 已新增失败后 `--last-failed` 诊断重跑、`error-context/trace.zip` 失败索引文件与带 `run_id/run_attempt` 的 artifact 命名，便于排障追踪。
- 协同进展（2026-05-08）：`frontend-e2e` 导出断言诊断摘要已扩展覆盖 `workbench-main-path` + `workbench-edge-cases`，按 `error-context` 统计 UI 下载层/响应头层/API 路径/404 语义提示计数并提取关键行，写入 `GITHUB_STEP_SUMMARY` 与 `/tmp/frontend-e2e-export-summary.md` artifact，便于快速定位导出回归类别
- 协同进展（2026-05-09）：`frontend-e2e` 导出诊断摘要新增 `workbench-main-path-shared-kb` 分区，仅对 shared 权限主链路失败上下文统计 `shared_permission_semantic_ok`，用于更快识别 `shared-*` 权限语义回归
- 协同进展（2026-05-09 补充）：`frontend-e2e` 的 `threshold alerts` 已补 shared 分区汇总行（`shared_scope`），即使无告警也能在摘要中直接确认 shared 权限诊断覆盖是否生效
- 协同进展（2026-05-09 再补充）：`frontend-e2e` shared 分区已补 `expected` 语义（有 shared 失败上下文时期望 `>=1`，无上下文时期望 `0`），并在无上下文场景持续输出 shared 计数，便于跨端摘要判读一致
- 协同进展（2026-05-09 稳态补充）：`frontend-e2e` shared 分区的 error-context 匹配已改为正则模式（`workbench-main-path.*shared.*kb`），降低前端测试标题轻微调整引发的诊断漏命中
- 协同进展（2026-05-09 稳态再补充）：`frontend-e2e` shared 分区匹配规则已变量化并收紧为 `SHARED_CONTEXT_PATH_REGEX=workbench-main-path.*(shared-kb-actions-disabled|shared.*kb.*disabled)`，减少无关 main-path 用例误归类
- 协同进展（2026-05-09 维护性补充）：`frontend-e2e` 导出摘要已将 `error-context.md` 扫描收敛为单次 `find` 后分组（main/shared/edge），降低分区统计口径漂移并减少重复扫描开销
- 协同进展（2026-05-09 维护性再补充）：`frontend-e2e` 导出摘要新增 `add_warning` 统一告警函数，集中处理 `P0/P1` 计数与告警消息拼装，后续扩展 shared/main/edge 阈值时变更点更集中
- 协同进展（2026-05-09 准确性补充）：`frontend-e2e` 已将 `workbench-main-path` 分区对 shared 专项上下文做反向过滤（`grep -Ev "${SHARED_CONTEXT_PATH_REGEX}"`），降低 shared 失败导致主链路告警噪音
- 协同进展（2026-05-09 规则收口补充）：`frontend-e2e` 已新增 `MAIN_CONTEXT_PATH_REGEX` / `EDGE_CONTEXT_PATH_REGEX`，并将 main/edge/shared 分区匹配统一为变量化规则，减少 workflow 规则维护分叉
- 协同进展（2026-05-09 维护性三次补充）：`frontend-e2e` 导出摘要已新增 `print_matched_files` / `print_key_lines` 统一输出函数，减少分区内重复 shell 循环并提升展示逻辑一致性
- 协同进展（2026-05-09 可见性补充）：`frontend-e2e` 的 main/shared/edge 导出分区断言计数已补 `context_files_detected` 字段，可在 CI Summary 直接核对“当前计数是否由对应分区上下文样本驱动”
- 协同进展（2026-05-09 工程化补充）：`frontend-e2e` 导出诊断逻辑已从 workflow 内联脚本抽离至 `frontend/scripts/ci_export_diagnostics.sh`，并补齐 Bash 3 兼容（去除 `mapfile` 依赖），方便本地与 CI 共享同一诊断实现
- 协同进展（2026-05-09 回归护栏补充）：`frontend-e2e` 已新增 `frontend/scripts/test_ci_export_diagnostics.sh` fixture 自测步骤（workflow: `Validate export diagnostics fixture tests`），用于在执行主回归前验证导出诊断脚本关键告警语义
- 协同进展（2026-05-09 机器可读补充）：`frontend/scripts/ci_export_diagnostics.sh` 新增可选 JSON 输出参数，`frontend-e2e` 已产出 `/tmp/frontend-e2e-export-summary.json` 并随 artifact 上传
- 协同进展（2026-05-09 统一门禁补充）：`frontend-e2e` 已接入同一 `scripts/ci_diag_guard.sh` 门禁步骤（`FRONTEND_EXPORT_DIAG_STRICT_LEVEL`），前后端导出诊断门禁策略已对齐
- 协同进展（2026-05-09 统一门禁再补充）：`frontend-e2e` 默认门禁级别同样提升为 `p0`，并在 step summary 追加 guard 小节；前后端门禁默认策略与展示格式保持一致
- 协同进展（2026-05-09 门禁策略化补充）：`frontend-e2e` 同步采用 `push@main=any / 其他=p0` 的自动策略并输出 `selected_strict_level`，前后端门禁选择逻辑保持一致
- 协同进展（2026-05-09 门禁 JSON 补充）：`frontend-e2e` 同步产出 `/tmp/frontend-e2e-export-guard-summary.json`，前后端 guard 摘要现同时具备 Markdown + JSON 两种消费形态
- 协同进展（2026-05-09 触发覆盖补充）：`frontend-e2e` 同步接入 `workflow_dispatch` 的 `export_diag_strict_level` 覆盖能力，并在 summary 输出 `dispatch_override/policy_source`，前后端触发策略保持一致
- 协同进展（2026-05-09 总览聚合补充）：`frontend-e2e` 同步接入 overview 聚合并产出 `/tmp/frontend-e2e-export-overview.md/.json`，前后端均支持“诊断 + 门禁”一页总览
- 协同进展（2026-05-09 策略解析收口）：`frontend-e2e` 同步改为调用 `ci_resolve_diag_strict_level.sh` 解析 strict-level，并接入同名 fixture 测试步骤，前后端门禁策略解析逻辑完全一致
- 协同进展（2026-05-09 fixture 入口收口）：`frontend-e2e` 同步改为 `Validate e2e tooling fixtures (frontend scope)`，由 `test_ci_e2e_tooling.sh` 统一调度 common + frontend 相关 fixture 测试，前后端 workflow 测试入口形态一致
- 协同进展（2026-05-08 补充）：`frontend-e2e` 导出摘要新增阈值告警（`threshold alerts`），当关键计数低于预期时输出 expected vs actual 异常项，便于后端与前端在 PR Summary 快速分流导出回归层级
- 协同进展（2026-05-08 再补充）：`frontend-e2e` 阈值告警已增加严重级别标签（当前以 `[P1]` 标注导出诊断缺口）与 `severity` 计数，便于与后端告警视图保持一致
- 协同进展（2026-05-08 再补充）：`frontend-e2e` 已补 `P0` 诊断失真判定（存在 `error-context` 但导出 API 路径提示为 0、或 UI/响应头双计数为 0；edge-cases 额外覆盖 404 语义提示为 0），用于优先暴露高风险诊断盲区
- 协同进展（回归稳态收口，2026-04-22）：前端 `workbench-edge-cases` 对“取消后同文案重发”场景改为基于后端 `POST /api/tasks/{task_id}/cancel` 契约进行稳定验证，并将 Context tab 定位收敛到 Inspector 顶部导航，消除并发运行下的时序抖动；本地 chromium 全量回归复测 `30/30` 通过。
- 协同进展（回归稳态补充，2026-04-22）：前端修复 `workbench-edge-cases` “token 切换后导出 404”用例竞态（切 token 前等待任务详情导出按钮可用），并按 CI 同口径串行回归（`--workers=1`）复测 chromium `30/30` 通过；后端导出契约保持不变。
- 协同稳定性补丁：`mock` provider 新增测试触发慢流标记（`[mock-slow]` / `[mock-slow-ms=30]`），用于稳定复现 running-task-recovery 场景，默认请求行为不变
- 协同进展：前端已接入 `running-task-recovery` 首版（刷新/切回会话自动接管 running/pending 任务流），并补齐恢复中/成功/失败可视化提示，复用现有 running reconnect SSE 能力
- 协同修复：前端流式展示已按 `session_id` 做会话隔离，切换会话时不再短暂串出其他会话任务
- 协同修复：针对任务完成瞬间的状态滞后场景，前端恢复链路已避免误报“恢复失败”（同任务去重 + stream 409 无害收敛）
- 协同修复：前端聊天区流式自动滚动已改为“仅贴底跟随”，用户上滑查看历史时不再被强制拉回底部
- 阶段 5 增量：`rag-kb-governance-lite` 首版后端接口已落地（按用户列出知识库、清空知识库、删除知识库，并输出来源采样统计）
- 协同优化：前端知识库治理页已完成可读性收口（表头左对齐与“操作”列、图标刷新、统一动作按钮、来源采样说明与完整来源悬浮查看），继续复用现有治理接口
- 协同优化：治理接口列表响应补充样本片段（`sample_chunks`）与采样文档标识统计（`top_document_ids`），前端可直接展示“真实内容预览”
- 阶段 5 增量：`usage-dashboard-lite` 首版后端接口已落地（`GET /api/tasks/usage/dashboard`，提供汇总、近 14 天趋势、会话榜与任务榜，支持按 `session_id` 聚合）
- 阶段 5 增量：`provider-usage-alignment` 首版已落地（`done.usage` 优先写入 provider 官方 token 用量，缺失字段自动回退估算，并输出 usage 来源字段）
- 阶段 5 增量：`e2e-main-path` 已补 usage 来源断言（校验 `done.usage` 的 token 数值与 `prompt_tokens_source/completion_tokens_source/usage_source`）
- 阶段 5 增量：usage 聚合接口已补来源统计（`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`），用于前端来源分布展示与历史数据识别
- 阶段 5 增量：`GET /api/tasks/usage/dashboard` 新增 `source_kind` 查询参数（`all/provider/estimated/mixed/legacy`）用于来源维度筛选；`e2e_main_path` 已补按来源筛选一致性断言
- 阶段 5 增量：`GET /api/tasks/usage/dashboard` 的 `trend` 已补来源趋势字段（`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`）；`e2e_main_path` 已补来源筛选下趋势来源一致性断言
- 协同修复：任务取消/超时后即使后端追加 `error(task_cancelled/task_timeout)`，前端也不会误判为 fatal 失败态并展示“重试上次发送”
- 协同修复：流结束后的 `trace/delta` 自动补拉已改为静默，避免底部状态提示被“暂无新的轨迹增量”覆盖
- 协同修复：待发送用户消息去重改为按 `task_id`，取消后再次发送相同文案可即时显示，不再被上一条同文案误隐藏
- 协同修复：发送后前端会立即刷新 `tasks/messages`，并在任务列表回刷前用流式任务兜底展示“当前任务”取消按钮
- 协同修复：前端取消任务成功后会本地中断活动 SSE 流并立即解除“生成中”锁定，发送按钮可快速恢复
- 协同修复：remote 模式在取消后加入短暂发送冷却，避免刚取消即重发触发上游限流
- 协同优化：聊天区“回到底部”按钮锚定在聊天区右下角（脱离滚动内容），并在上滑阅读期间以徽标+脉冲提示新输出，点击可快速回底
- 协同优化：回底按钮定位参数继续微调（上移+右移）以避让底部消息与输入区遮挡
- 协同进展：前端左侧与中栏已完成风格收口（导航层级、runtime strip、输入区动效与密度），继续复用现有接口与字段
- 协同进展：前端已按最新交互要求收敛头部占位（移除会话状态胶囊与输入计数提示），继续复用现有接口与字段
- 协同进展：前端侧栏账户展示已收口到左下角“设置”弹窗顶部，并采用与主题/主题色/语言一致的设置行风格（图标 + 标题 + 值）
- 协同进展：前端流式状态提示已完成 i18n 化（去除硬编码英文，按语言动态切换），后端接口契约无需调整
- 协同进展：前端 store 默认流式文案改为复用 `en.stream`，减少文案漂移风险，后端契约保持不变
- 协同进展：模型设置弹窗元信息补充 `base_url` 展示，并在 `remote` 模式下增加 OpenAI-compatible 协议提示，前后端设置契约保持不变
- 协同进展：模型设置弹窗按模式联动展示；`mock` 固定 `provider/model` 且隐藏 `base_url/api_key`，切换模式时回显逻辑与后端设置保持一致
- 协同进展：模型设置弹窗提示改为 antd 上下文 `message`（通过 `App.useApp()`），消除动态主题下静态 message 警告
- 协同进展：模型设置切换到 `mock` 后保存会显式清空 `api_key/base_url`，避免历史 remote 凭证残留
- 协同进展：当已保存 `remote` 配置时，前端切换回 `remote` 会回显后端已存 `provider/model/base_url`
- 协同进展：前端聊天区已修复“发送消息不即时显示 + assistant 重复显示”问题（用户消息乐观显示，流式回复仅在生成中/失败态展示）
- 状态增强：`/api/tasks*` 响应已补充 `status_normalized`、`status_label`、`status_rank`，统一状态语义并保持向后兼容
- W3 增量：mock 工具链路支持可复现错误语义（`[mock-tool-error]` 可恢复重试，`[mock-tool-fatal]` 致命失败），`tool_end/error/trace.meta.tool` 已输出 `retry_count/error`
- W3 优化：新增本地计算器工具 `calc_eval`（支持 `[calc:1+2*3]` 与“计算 1+2*3”触发），纳入统一工具生命周期事件
- W1 优化：新增 `POST /api/settings/validate`，用于设置保存前的结构/连通性预校验（不落库）
- W1 优化补强：`settings/validate` 在 `HEAD` 失败时自动回退 `GET`，减少远端网关不支持 HEAD 时的误判
- W1 预检修复：`settings/validate` 的远端探测请求补充 `Authorization` 头；`401/403` 返回 `remote_api_key_unauthorized`（不再归类为 network error）
- W1 设置语义收口：`remote` 模式下 `api_key` 留空沿用历史密钥（首次配置仍必填）
- W1 能力补齐：`remote` 模式已接入 OpenAI-compatible provider（`base_url + api_key + model`）
- W1 接口校验补齐：`remote` 模式 `provider/model/base_url` 必填；`api_key` 在未配置历史密钥时必填，已配置时可留空沿用
- W1 接口收口：`POST /api/settings/validate` 新增 `error_code`，并补充 `remote_base_url_required`
- W1/W2 稳定性优化：SSE 流式输出增加周期 heartbeat（长输出保活更稳定）+ trace 持久化写入节流（降低数据库写放大）
- W2 优化：`GET /api/tasks/{task_id}/stream` 支持 `running` 状态重连（回补增量，不重复执行任务）
- W2 重连流优化：`running` 重连返回的 `done/error` 事件补齐 `session_id/step_id` 并标记 `resumed=true`
- W2 重连轮询优化：重连流按“有增量快轮询、无增量退避慢轮询”策略拉取 delta，降低 DB 轮询压力
- W2 后端性能优化：新增 task 快照级 delta 计算，重连流循环复用单次 `get_task` 结果，减少重复查询
- W2 语义优化：`GET /api/tasks/{task_id}/trace/delta` 的 `lag_seq` 改为基于任务快照真实尾游标计算，避免恒零
- W2 重连兼容优化：`GET /api/tasks/{task_id}/stream`（running）支持 `after_seq` 与 `Last-Event-ID` 双游标恢复
- W1 可调优优化：trace 写入节流间隔支持环境变量 `TRACE_PERSIST_MIN_INTERVAL_SEC`
- W1/W2 可调优优化：running 重连流轮询与 heartbeat 参数支持环境变量（`STREAM_RECONNECT_POLL_FAST_SEC` / `STREAM_RECONNECT_POLL_MAX_SEC` / `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`）
- W1 usage 语义优化：`completion_tokens` 改为基于最终输出文本估算（覆盖流式与 fallback 场景）
- P2 usage 对齐进展：OpenAI-compatible provider 已支持提取官方 usage（含流式优先尝试 `stream_options.include_usage`，不支持时自动回退）

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`auth`、`sessions`、`tasks`、`settings`、`rag`、`audit`
- `app/db.py`：PostgreSQL 连接、初始化与索引
- 新增 `auth_sessions` 表：refresh token 哈希持久化、会话过期/撤销管理
- 新增 `audit_logs` 表：最小审计事件持久化（`event_type` + `event_detail_json`）
- `app/providers/`：Provider 抽象 + mock 实现 + OpenAI-compatible provider
- `app/services/chat_execution_service.py`：SSE 任务流（mock 四步 trace）
- 流式阶段已支持最终 `observation` 的批次增量持久化（`seq` 递增，默认每 8 个 chunk 落库一次 + 结束兜底）
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `app/services/chroma_rag_service.py`：用户级 RAG collection 命名、ingest/query/status、knowledge base list/clear/delete
- `app/services/settings_service.py`：用户级模型设置读取/保存与 `api_key` 加密解密
- `app/services/auth_service.py` / `auth_session_service.py`：用户认证、access token、refresh token 轮换与会话撤销
- `app/services/audit_service.py`：审计事件写入、分页查询与筛选
- `tasks.usage_json`：任务完成时持久化 `done.usage`（前端可用于任务列表摘要展示）

## HTTP 接口（摘要）

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- `GET /api/auth/users`（admin only）
- 审计事件：`login`、`logout`、`refresh`、`settings_update`、`settings_validate`、`task_create`、`task_cancel`、`task_timeout`、`task_failed`、`rag_ingest`、`rag_kb_clear`、`rag_kb_delete`
- 审计查询：`GET /api/audit/logs?event_type=&session_id=&task_id=&start_at=&end_at=&limit=&offset=`（前端可按当前页/全量筛选结果导出）
- `GET /api/auth/me`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`（含 `total/has_more`）
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/export/json`
- `GET /api/sessions/{session_id}/export/markdown`
- `GET /api/sessions/{session_id}/memory/status`
- `GET /api/sessions/{session_id}/usage/summary`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=`（含 `total/has_more`）
- `GET /api/tasks*` 相关响应包含状态派生字段：`status_normalized`、`status_label`、`status_rank`
- `GET /api/tasks/usage/summary`（可选 `session_id`）
- `GET /api/tasks/usage/dashboard`（可选 `session_id`，含趋势/会话榜/任务榜）
  - `GET /api/tasks/usage/dashboard` 支持可选 `source_kind`：`all/provider/estimated/mixed/legacy`
  - 两个 usage 聚合接口均包含来源统计字段：`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`
  - `trend` 每日点位包含来源计数：`source_tasks_provider/source_tasks_estimated/source_tasks_mixed/source_tasks_legacy`
- `GET /api/rag/status`
- `POST /api/rag/ingest`
- `POST /api/rag/query`
- `GET /api/rag/knowledge-bases`
- `POST /api/rag/knowledge-bases/{knowledge_base_id}/clear`
- `DELETE /api/rag/knowledge-bases/{knowledge_base_id}`
- RAG 权限语义（2026-05-09）：`knowledge_base_id` 命中 `shared-*` 前缀时进入共享命名空间；`admin` 可执行 ingest/clear/delete，非 admin 仅允许 status/query/list
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `GET /api/tasks/{task_id}/export/json`
- `GET /api/tasks/{task_id}/export/markdown`
- `GET /api/tasks/{task_id}/stream`（`pending/running`；running 为重连回补流）
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`（`limit` 默认 200，最大 500；`has_more` 反映剩余分页或任务仍在运行）
- 除 `/health` 与 `/api/auth/*` 外，其余业务接口均需 `Authorization: Bearer <token>`

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：
- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `cancelled`
- `timeout`
- `done`
- `error`

其中 `event: trace` 的 `data.step` 与 REST TraceStep 同构（`id/type/content/meta/seq?`）。
`tool_start/tool_end` 使用与 action 节点一致的 `step_id`，可与 trace 节点一一对齐。
当输入包含 `[mock-tool-error]` 时，会先触发一次工具错误并发出 `error(fatal=false,retryCount=1)`，随后自动重试并完成；
当输入包含 `[mock-tool-fatal]` 时，会触发工具致命失败并直接结束任务（`status=failed`）。
当输入包含 `[calc:表达式]`（如 `[calc:1+2*3]`）或文本“计算 1+2*3”时，会触发本地计算器工具并在 Trace 中记录 `input/output/status`。
`trace/delta?after_seq=` 现可在任务流式进行中拉取到最终 `observation` 的阶段性刷新内容。
前端已接入流式期间定时拉取、失败退避重试与流结束补拉，后端接口保持幂等增量语义。
前端 Context 摘要会展示 delta 同步状态/重试次数/最近成功时间，便于联调与问题定位。
当前在连续失败场景下也会显示轻提示，后端接口无需额外状态字段。
并会展示下次重试时间、最近错误内容与恢复提示（短时自动消退），重试中还有秒级倒计时，便于确认故障是否恢复。
页面后台时前端会暂停自动 delta 拉取，返回前台后恢复，不影响接口幂等语义。
远端 Provider 异常会由 `ProviderCallError` 归一并在 SSE `error` 中透传稳定 `code`，便于前端做提示映射与排障定位。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- RAG collection 命名：`kb_{user_hash}_{knowledge_base_id}`（按用户隔离）
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 流式 trace 写入节流：`TRACE_PERSIST_MIN_INTERVAL_SEC`（默认 `0.35` 秒）
- running 重连流参数：
  - `STREAM_RECONNECT_POLL_FAST_SEC`（默认 `0.3`）
  - `STREAM_RECONNECT_POLL_MAX_SEC`（默认 `2.0`）
  - `STREAM_RECONNECT_HEARTBEAT_INTERVAL_SEC`（默认 `2.0`）
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：`memory/add`、`memory/query`、`rag/ingest`、`rag/query` 返回 503；任务后的摘要写入为 best-effort

### 通俗分工（后端视角）

- `PostgreSQL`（业务主存储）：
  - 存 `sessions / tasks / messages`，以及任务 `trace_json / usage_json`。
  - 用于会话列表、消息历史、任务状态回放与统计聚合。
- `Chroma Memory`（会话记忆）：
  - collection：`memory_{session_id}`。
  - 存当前会话的可检索记忆片段（含任务完成后的摘要追加）。
  - 目标是低成本召回“这次会话刚刚说过的重要信息”。
- `Chroma RAG`（知识库检索）：
  - collection：`kb_{user_hash}_{knowledge_base_id}`。
  - 存 ingest 后的文档分块与 metadata，用于跨会话复用知识检索。

为什么不合并成一个库：

- `RAG` 主要解决“系统知道什么文档”，不等于“当前会话刚约定了什么”。
- `Memory` 主要解决“当前会话记住什么”，不适合承载大规模知识文档治理。
- `PostgreSQL` 是权威历史账本；Chroma 两类 collection 是检索层索引，不替代业务主数据。

当前实现注意点：

- 删除会话时会级联删除 PostgreSQL 的 tasks/messages，并会 best-effort 删除 Chroma `memory_{session_id}` collection（清理失败不阻塞主删除流程）。

## W4 新增说明

- 执行链路 `mock_retrieve` 已接入真实知识库检索（默认 `kb_{user_hash}_default`，可通过 `[kb:xxx]` 指定）
- `TraceStep.meta.rag` 会记录命中 `chunks` 与 `knowledge_base_id`
- usage 升级为可计算字段：
  - `prompt_tokens`、`completion_tokens`
  - `cost_estimate`（可通过环境变量配置单价）
- 新增环境变量：
  - `RAG_DEFAULT_KNOWLEDGE_BASE_ID`
  - `RAG_DEFAULT_TOP_K`
  - `USAGE_PROMPT_TOKEN_PRICE_PER_1K`
  - `USAGE_COMPLETION_TOKEN_PRICE_PER_1K`

## 阶段 5 增量（full-data-auth 首版）

- 新增用户认证：`register/login/me`，JWT（HS256）签发与校验
- 新增最小会话管理：refresh token（哈希落库）轮换、会话查询与撤销（按 session / 全部）
- 新增 `users` / `user_settings` 表，并将 `sessions/tasks/messages` 写入与查询切为 `user_id` 隔离
- 新增 `auth_sessions` 表（refresh token 哈希、过期时间、撤销时间、UA/IP）
- 设置改为用户级，`api_key` 以服务端主密钥加密后落库（`user_settings.api_key_enc`）
- 新增环境变量：
  - `INSIGHT_AGENT_JWT_SECRET`
  - `INSIGHT_AGENT_ACCESS_TOKEN_TTL_MINUTES`
  - `INSIGHT_AGENT_REFRESH_TOKEN_TTL_DAYS`
  - `INSIGHT_AGENT_SECRET_KEY`

## 阶段 5 增量（PostgreSQL 迁移主线）

- 后端运行时统一使用 PostgreSQL：
  - `INSIGHT_AGENT_DATABASE_URL=postgresql://...`
- `app/db.py` 已收敛为 PostgreSQL 单后端实现（业务 SQL 调用层保持不变）
- 新增迁移脚本：`scripts/migrate_sqlite_to_postgres.py`
  - 平迁表：`users`、`user_settings`、`sessions`、`tasks`、`messages`
  - 策略：幂等 upsert（可重复执行）

## 本地启动

推荐使用 **Python 3.14**（与 `compose.full.yml`、GitHub Actions `backend-e2e` 一致；仓库根 `.python-version` 为 `3.14`，便于 pyenv 等对齐）。若旧版解释器创建过 `backend/.venv`，`pyvenv.cfg` 可能仍指向旧版本且与 `bin/python` 不一致，应**删除 `backend/.venv` 后**用 3.14 重新执行 `python -m venv .venv` 与 `pip install -r requirements.txt`，不要手改 `pyvenv.cfg`。

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需一键拉起依赖并启动前后端（推荐），可在仓库根目录执行：

```bash
./start_insightagent.command
```

该脚本会自动拉起并等待 `postgres/chroma` 就绪，且已兼容 `backend/.env` 缺失场景。
脚本内 Chroma 就绪检查使用 `v2` heartbeat，兼容新版 Chroma 容器；启动前会额外清理旧后端进程，并等待后端健康检查通过。
后端进程由**本机解释器**启动：优先 `backend/.venv/bin/python`，否则回退 `python3`（见脚本内逻辑）；请使用 **Python 3.14** 创建/重建 `.venv`，与仓库根 `.python-version` 及 CI 一致。`compose.full.yml` 中的 `python:3.14-slim` 仅在「用 Compose 跑后端容器」时使用，与一键脚本的本地 uvicorn 路径相互独立。前端 dev 依赖本机 **Node.js 24.x**（与根目录 `.nvmrc`、`frontend/package.json` 的 `engines` 一致；一键脚本里为 `npm run dev`，不经过 `node:24-alpine` 镜像）。

如需将本地 SQLite 数据迁移到 PostgreSQL，可执行：

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../data/sqlite.db \
  --database-url postgresql://insight:insight@127.0.0.1:5432/insightagent
```

最小 e2e 基线（登录/过期/登出/跨账号隔离/发送流）可执行：

```bash
python scripts/e2e_baseline.py --base-url http://127.0.0.1:8000
```

主链路 e2e（登录 -> 设置校验/保存 -> 发送任务并校验 trace -> RAG ingest/query -> 任务/会话导出）可执行：

```bash
python scripts/e2e_main_path.py --base-url http://127.0.0.1:8000

导出稳定性 e2e（任务/会话导出一致性 + 下载头 + 404 语义）可执行：

```bash
python scripts/e2e_export_consistency.py --base-url http://127.0.0.1:8000
```
```

取消/超时链路 e2e 可执行（默认先跑取消；超时链路建议在低超时后端实例验证）：

```bash
# 默认本地后端（通常 TASK_TIMEOUT_SEC 较大）可先验证取消链路
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout

# 单独起一个低超时实例验证 timeout（示例：1 秒）
TASK_TIMEOUT_SEC=1 uvicorn app.main:app --host 127.0.0.1 --port 8010
python scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8010
```

如需 Memory 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

## 后续阶段决策（后端视角）

### 优先做

1. `full-trace-session-lite`：任务详情快照与导出入口已接入；后续补详情视图增强与导出 e2e。
2. `trace-export-json-md`：单任务 JSON/Markdown 导出接口已落地；字段稳定性与导出 e2e 校验首版已补齐（`e2e_export_consistency`），后续补失败快照归档。
3. `session-export-lite`：会话级 JSON/Markdown 导出接口已落地；字段稳定性与导出 e2e 校验首版已补齐（`e2e_export_consistency`），后续补失败快照归档。
4. `remote-provider-hardening`：已完成首轮（错误码归一 + SSE 透传 + 前端映射联动）。
5. `e2e-main-path`：主链路 e2e 脚本已落地（登录、模型配置、任务流、Trace、RAG、导出）并接入后端 CI；后续补失败快照留档。
6. `task-cancel-timeout`：首版已落地（取消接口 + 超时中断 + SSE 事件），并新增 cancel/timeout e2e 脚本；后续补细粒度状态反馈。
7. `running-task-recovery`：前端恢复链路已接入，后续可补失败快照与恢复可观测字段。
8. `usage-dashboard-lite`、`audit-event-expansion` 与 `provider-usage-alignment` 已完成首版并补齐来源趋势联动；前端可视化回归 CI 已扩展至主链路导出、取消恢复与边界异常场景，并接入 smoke 跨浏览器矩阵；后端导出稳定性回归与后端 e2e 失败快照归档均已接入，下一步可细化失败快照内容与视觉断言。

### 暂不做

1. Redis/Kafka/Celery 分布式队列（当前规模不需要）。
2. K8s / 微服务拆分（对当前阶段收益低）。
3. 复杂多跳 RAG 与重排体系（先把最小治理与导出复盘做扎实）。
4. 企业级 SSO/RBAC 全套（保留扩展位，先做轻量 RBAC）。

## 当前限制（W4 生产化前）

- PostgreSQL 已成为默认且唯一运行后端，仍需完成真实环境平迁与回滚演练
- 真实工具调用循环仍以 mock 工具编排为主（RAG 检索已真实接入）
- token 现为“provider 官方 usage 优先，估算值兜底”（并在 `done.usage` 标注来源字段）
- `trace/delta` 当前链路已稳定，后续仅做参数级调优（不影响 W2 已收口）

## 最新同步（2026-04-23）

- 本轮变更聚焦前端任务中心表格交互与样式（头部计数移除、失败置顶移除、筛选/表格视觉优化）。
- 本轮补充调整：任务中心底色与重置按钮样式继续对齐审计日志视觉规范。
- 后端接口、数据库结构与任务流协议本轮无新增变更。
