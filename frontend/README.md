# Frontend

Next.js App Router（React 19）+ Ant Design + TanStack Query + Zustand + React Flow 的 Agent 工作台前端。

**Node.js**：仓库统一为 **24.x**（`frontend/package.json` 的 `engines.node`、`compose.full.yml` 前端服务 `node:24-alpine`、仓库根 `.nvmrc`）。本地可用 nvm/fnm 等按 `.nvmrc` 切换；`@types/node` 与运行时主版本对齐。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3：已完成（mock 范围）
- W4：已完成（RAG 面板 + Token/Cost 展示）
- 阶段 5 增量：已完成登录/注册入口页与 Auth Gate（token 持久化、401 自动回登录）
- 阶段 5 调整：已移除首次引导页，登录后直接进入工作台
- 阶段 5 收口：新增运行态提示条（mock/remote）与“去配置模型”快捷入口
- 阶段 5 收口：`remote` 未配置 `api_key` 时发送前前端直接阻断并引导配置
- 阶段 5 收口：登录页文案与白底可读性优化、退出按钮对齐优化、会话空标题默认展示回退为“新会话”
- 阶段 5 细化：登录区标题文案调整为“账号登录”、提交按钮禁用态可读性优化、退出入口迁移至左下角设置区并避让折叠控件
- 阶段 5 细化（继续）：移除“当前用户：未登录”提示、注册邮箱格式前置校验（替代 422 生硬报错）、登录输入 autofill/已填充态样式优化并适配浅色表单
- 阶段 5 文案收口：登录页左侧说明融合主页叙事（可观测智能体、对话到任务闭环），并补回 SSE/Trace、Memory/RAG、Token/Cost 等关键信息点
- 阶段 5 交互修复：登录密码框显隐图标恢复可见与可点击（支持显示/隐藏切换）
- 阶段 5 协同：后端 PostgreSQL 迁移主线已完成运行时收敛（前端请求统一通过鉴权 API 访问用户级数据）
- 阶段 5 联调排障（2026-04-14）：定位“发会话消息无响应”为后端 `POST /api/tasks` 返回 500（PostgreSQL SQL 类型兼容），后端修复后前端发送与流式恢复
- 阶段 5 国际化补齐：登录页（Auth Gate）接入 i18n，新增 `auth` 文案分组并覆盖中英文登录/注册全链路文案
- 阶段 5 体验补齐：登录页新增轻量设置模块（语言/主题/主题色），并完成登录页样式对深浅主题与主题色的联动适配
- 阶段 5 鉴权增强：接入 refresh token 持久化与自动刷新；401 优先尝试 `/api/auth/refresh` 轮换后重试，失败再回登录
- 阶段 5 账户可见性收口：当前登录用户展示已融合到左下角“设置”弹窗顶部，并采用与主题/主题色/语言一致的“图标 + 标题 + 值”行样式
- 阶段 5 布局重排（2026-04-22）：会话导出迁移到左侧会话行“...”菜单（方案 1）；Memory/RAG 调试迁移到设置弹窗“运行调试”；右侧 Inspector 收敛为运行态核心（概览/同步/当前任务）
- 阶段 5 交互收口（2026-04-22）：运行调试弹窗样式与项目主视觉对齐；任务中心“任务详情”按钮提升可见性；右侧“当前任务”仅保留取消操作（移除“打开任务中心/任务详情”）
- 阶段 5 交互收口（2026-04-22，方案 1）：任务中心从中栏替换模式改为右侧抽屉，聊天中栏保持连续；任务详情入口改为新标签打开 `/tasks/[taskId]`，减少上下文中断
- 阶段 5 交互收口（2026-04-22，方案 1 补充）：任务中心头部移除模式/模型信息，仅保留右侧关闭按钮，降低头部信息密度并提升主操作可见性
- 阶段 5 交互收口（2026-04-23）：任务中心改为审计日志同款信息架构（筛选/搜索工具栏 + 表格 + 分页），提升长列表扫描与定位效率
- 阶段 5 交互收口（2026-04-23 补充）：任务中心顶部筛选/搜索区改为审计日志同款双行布局（主筛选行 + 次筛选行），统一控件高度、间距与重置动作风格
- 阶段 5 交互收口（2026-04-23 再补充）：修复“全局任务条数小于当前会话”问题（改为自动拉取完整分页后本地筛选）；任务中心表格移除“用量来源”列；“任务详情”按钮改为轻量操作样式
- 阶段 5 样式微调（2026-04-22）：运行调试弹窗改为上下单列结构，并移除分区高亮底色，回归主界面统一底色风格
- 阶段 5 兼容性修复（2026-05-08）：`Workbench` 任务中心抽屉已将 Ant Design `Drawer` 的 `width` 属性替换为 `size`，消除 `[antd: Drawer] width is deprecated` 警告且保持原有响应式宽度行为
- 阶段 5 工程收口（2026-05-08）：任务详情页与会话导出入口的下载链路已统一抽取到 `frontend/lib/export-download.ts`，复用鉴权下载、附件文件名解析与 `ApiError` 映射语义，减少导出逻辑重复与回归分叉
- 阶段 5 聊天显示修复：发送后立即展示用户临时消息；assistant 流式卡片仅在生成中/失败态显示，避免切回会话前看到重复回复
- 阶段 5 增量：`remote-provider-hardening` 前端收口已完成首轮；流式 `error` 与设置校验失败已按 `error_code` 做本地化提示映射，并保留错误码用于排障
- 阶段 5 增量：`task-cancel-timeout` 前端首版已落地；Inspector「当前任务」支持取消运行中任务，流式状态接入 `cancelled/timeout` 事件提示
- 阶段 5 协同：后端已补齐 `task-cancel-timeout` e2e 脚本并接入后端 CI（baseline/main-path/cancel/timeout；CI 已升级 `checkout`/`setup-python` 以适配 GitHub Actions Node 24；后端 Python 与 compose/`.python-version` 统一为 3.14）；前端 Node 与 compose/`.nvmrc`/engines 统一为 **24.x**，可继续专注可视化回归与状态细化
- 阶段 5 协同（2026-05-13）：后端 `tool-runtime-productionization` 继续按“内部边界收口、外部行为不变”推进；`chat_execution_service.py` 中单次 tool attempt 的 success/error 分叉、单工具初始化 bundle、单工具执行块、plan-item 级 success/fatal 结果、最终结果访问、完整的 plan-item 处理块、success path 的 trace/observation/output/rag follow-up 后处理、tool success/error 的 step 更新、tool_end/error payload 组装、trace payload 拼装、fatal 失败收尾与 provider prompt 拼接已继续下沉到 `backend/app/services/tool_runtime.py` 的 runtime helper。期间出现过一次 CI 回归：成功流因缺失 `iteration_execution` 透传而走到 `error` 分支、没有发出 `done`，从而同时击穿后端 baseline 与前端 smoke；现已修复，并进一步把 attempt bundle、attempt execution、attempt loop result、attempt loop terminal result、retry loop 最终结果、plan-item 顶层事件访问、success/fatal effects 以及 effects 的顶层透出都收口到 runtime helper，当前前端消费的 SSE/trace 契约保持不变。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 61 条兼容测试；`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-13，retry loop helper）：后端已继续把“单个 tool plan item 的完整 retry loop”下沉为 `backend/app/services/tool_runtime.py` 中的 `execute_tool_plan_item_retry_loop()`，`chat_execution_service.py` 改为消费 helper 产出的事件流与终态结果；当前前端可见的 SSE 发射顺序、trace 结构、fatal failure 收尾与 retrieve 后的 rag follow-up 契约保持不变。focused 回归脚本 `backend/scripts/test_tool_runtime_slice.py` 已扩展到 64 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，loop result flattening）：后端继续把单个 tool loop 的终态消费结果上提到 runtime 顶层，新增 `trace_event/success_effects/terminal_effects/should_return` 这组更扁平的返回字段；`chat_execution_service.py` 因此减少了对嵌套结果对象的直接穿透，但前端可见的 SSE 顺序、trace 结构、fatal failure 收尾与 rag follow-up 契约保持不变。`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，stream effects helper）：后端已继续把单个 tool loop 结束后的后处理 effects 收口到 `build_tool_plan_item_stream_effects()`，统一提供 `trace_steps/trace_events/observation/terminal_effects/should_return`；`chat_execution_service.py` 仅按该结果逐步追加 trace 与持久化，当前前端可见的 trace 事件顺序、rag follow-up 追加节奏与 fatal failure 收尾契约保持不变。focused 回归脚本已扩展到 66 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，terminal return helper）：后端已继续把 terminal failure 的任务状态与失败审计 payload 收口到 `build_tool_plan_item_terminal_return_effects()`，`chat_execution_service.py` 不再直接穿透 `terminal_effects` 去手工拼 `task_failed` 事件；当前前端可见的错误 SSE 语义、`state(error)` payload 与 trace 收尾顺序保持不变。focused 回归脚本已扩展到 67 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，success seq increment）：后端已继续把 success path 中 rag follow-up 对后续 step 序号的影响收口到 `build_tool_plan_item_stream_effects().seq_increment`，`chat_execution_service.py` 不再直接回读 `success_effects.rag_followup` 来维护 `seq_cursor`；当前前端可见的 trace 顺序与 rag follow-up 追加节奏保持不变。focused 回归脚本保持 67 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，observation delta）：后端已继续把 success path 中需要追加到后续 prompt 的 observation 文本收口到 `build_tool_plan_item_stream_effects().tool_observations`，`chat_execution_service.py` 不再手工 append 单条 observation；当前前端可见的 trace/SSE 契约保持不变。focused 回归脚本保持 67 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，service-effects helper）：后端已继续把单个 tool 的高层 service 消费结果归并到 `build_tool_plan_item_service_effects()`，统一承接 trace 追加、observation delta、seq delta 与 terminal return 信息；当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 69 条兼容测试，且交接文档已同步到当前真实状态，便于后续会话延续推进
- 阶段 5 协同（2026-05-14，service-effects follow-up）：后端已继续把单个 tool 的 service 消费结果抬高成更明确的 runtime 指令对象，`build_tool_plan_item_service_effects()` 现已直接暴露 `trace_writes` 与 `continue_update`，前者承接 trace append/SSE/persist 节奏，后者承接 success path 的 observation/seq 增量；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本仍为 69 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，next-action helper）：后端已继续把单个 tool 的“继续流转 / 终止返回”分支选择上提到 `build_tool_plan_item_next_action()`，`chat_execution_service.py` 现通过 `next_action(kind=continue|return)` 统一消费 success/terminal 两种内部路径；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本仍为 69 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，return-action helper）：后端已继续把 terminal path 的三连调用参数拼装收口到 `build_tool_plan_item_return_action()`，`chat_execution_service.py` 不再直接拆 `terminal_return_effects` 来调用 `complete_task / record_failure_event / state(error)`；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 70 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，trace-write-action helper）：后端已继续把 trace path 的执行输入收口到 `build_tool_plan_item_trace_write_action()`，`chat_execution_service.py` 不再直接拆 `trace_writes` 来执行 `trace step append + trace SSE + persist`；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 71 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，next-action-execution helper）：后端已继续把 `next_action` 的执行输入收口到 `build_tool_plan_item_next_action_execution()`，`chat_execution_service.py` 不再同时直接依赖 `next_action` 和 `build_tool_plan_item_return_action()` 来分发 continue/return 两种内部路径；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 73 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，service-effects-execution helper）：后端已继续把 service 最终消费的执行输入收口到 `build_tool_plan_item_service_effects_execution()`，`chat_execution_service.py` 已通过该 helper 统一接收单个 tool 的 `trace_write_actions + next_action_execution` 聚合结果；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 75 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，service-execution helper）：后端已继续把 `loop_execution_result` 到单个 tool 最终执行输入的整条链收口到 `build_tool_plan_item_service_execution()`，`chat_execution_service.py` 已通过该单入口 helper 直接消费最终执行结果；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 77 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，continue-action helper）：后端已继续把 success path 的执行输入收口到 `build_tool_plan_item_continue_action()`，`chat_execution_service.py` 不再直接依赖 `continue_update` 来更新后续 prompt 观测与 step 序号；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 78 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，service-actions helper）：后端已继续把单个 tool 的 service 副作用执行顺序显式化为 `build_tool_plan_item_service_actions()`，`chat_execution_service.py` 现按统一 action 序列消费 `trace_write / continue / complete_task / record_failure_event / emit_state / return`；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 80 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，service-action builders）：后端已继续把 `service_actions` 内部的 trace/continue/return 几类动作收口为显式 helper，`build_tool_plan_item_service_actions()` 不再手拼匿名 dict；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 83 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，service-execution generator）：后端已继续把单个 tool 的高层入口前推到 `execute_tool_plan_item_service_execution()`，`chat_execution_service.py` 不再在 service 侧显式串联 retry loop 结果与 `build_tool_plan_item_service_execution()`；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 85 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，service-actions executor）：后端已继续把 `service_actions` 的实际执行壳子前推到 `execute_tool_plan_item_service_actions()`，`chat_execution_service.py` 只保留 SSE 字符串包装与 return 边界；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 87 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，registry injection seam）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`run_tool / execute_tool_spec / build_tool_runtime_context` 现已支持可选 `registry` 注入；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 90 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，registry builder seam）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `get_default_tool_registry()` 与 `build_tool_registry()`，并让 `get_registered_tool_names()` 也支持可选 `registry`；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 92 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，high-level registry threading）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`execute_tool_plan_item_retry_loop()` 与 `execute_tool_plan_item_service_execution()` 现也支持可选 `registry` 透传；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 94 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，registry loader seam）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `load_tool_registry()`，并让默认 registry 枚举/解析路径实际经过这个 loader；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 96 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，pluggable registry loader）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`load_tool_registry()` 现已接受可插拔 `loader`，并把 `registry_loader` 参数线程化到低层与高层入口；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 99 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，registry provider object）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ToolRegistryProvider` / `StaticToolRegistryProvider`，并让 `load_tool_registry()` 接受可选 `provider`；`registry_provider` 参数也已线程化到低层与高层入口。当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 102 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，default provider path）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `get_default_tool_registry_provider()`，并让默认 `load_tool_registry()` 路径也显式经过 provider object；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 104 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，named default provider）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增具名 `DefaultToolRegistryProvider`，并让 `get_default_tool_registry_provider()` 返回它；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 106 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，configured provider stack）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ConfiguredToolRegistryProvider` 与 `build_tool_registry_provider()`，并让 `chat_execution_service.py` 在 tool loop 外显式预构建并复用 provider；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 110 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，configured provider resolution stack）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `get_configured_tool_registry_provider()` 与 `resolve_tool_registry_provider()`，并让 `chat_execution_service.py` 通过具名 configured provider 入口显式预构建默认 provider；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 113 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，settings-backed registry overrides）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_OVERRIDES_JSON` 与 `build_tool_registry_overrides_from_settings()`，并让默认 configured provider 开始真实消费 settings 中的 tool metadata 覆盖；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 116 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，settings-backed tool disable path）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_settings_config()` 与 `get_disabled_tool_names_from_settings()`，并让默认 configured provider 支持通过 `enabled=false` 过滤已注册 tool；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 119 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，settings-backed registry profiles）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROFILE`、`get_tool_registry_profile_name_from_settings()` 与 `build_tool_registry_profile_settings_config()`，并让默认 configured provider 支持按内建 profile 切换一组 tool 启停，再由 JSON overrides 局部重开；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 123 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-15，settings-backed extra tool aliases）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON` 与 `build_tool_registry_extra_tools_from_settings()`，并让默认 configured provider 能从配置里长出额外 alias registrations，再参与 profile / disable / override 组合链；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 126 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，settings-backed provider sources）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCE`、`INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_SOURCES_JSON`、`get_tool_registry_provider_source_name_from_settings()` 与 `build_tool_registry_provider_sources_from_settings()`，并让默认 configured provider 能从 settings 选择命名基础 registry source，再叠加 profile / disable / override / extra alias 组合链；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 130 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，provider source adapters）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，命名 source 现已支持 `provider/profile/disabled_tool_names/overrides/extra_tools` adapter 形态，并作为默认 configured provider 的基础 registry source；当前前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 133 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，named providers + loader adapters）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_PROVIDERS_JSON`、`build_tool_registry_providers_from_settings()`、`resolve_named_tool_registry_loader()` 与 `build_tool_registry_provider_adapter()`；命名 source 现在既能引用命名 provider，也能直接声明 `loader/profile/disabled_tool_names/overrides/extra_tools`，但前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 137 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，provider factories）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `resolve_named_tool_registry_provider_factory()` 与 `build_profile_tool_registry_provider()`，命名 provider 与命名 source 现在都能直接声明 `provider_factory`，并在内建 profile provider 基础上继续做 `enabled=true` 重开、overrides 与 extra tools 组合；当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 141 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，named loaders）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_LOADERS_JSON`、`build_tool_registry_loaders_from_settings()` 与 `build_tool_registry_loader_adapter()`，命名 provider 与命名 source 现在都能引用配置里的 loader 名；当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 145 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，loader factories）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `resolve_named_tool_registry_loader_factory()` 与 `build_profile_tool_registry_loader()`；named loader 现在可以直接声明 `loader_factory`，并把这套 profile 语义继续传递给消费它的 named provider / source。当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 149 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，settings-backed factory aliases）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `INSIGHT_AGENT_TOOL_REGISTRY_LOADER_FACTORIES_JSON`、`INSIGHT_AGENT_TOOL_REGISTRY_PROVIDER_FACTORIES_JSON`、`build_tool_registry_loader_factories_from_settings()` 与 `build_tool_registry_provider_factories_from_settings()`；命名 loader / provider 现在既能直接引用内建 factory，也能引用配置里的 factory alias，并保留 profile 语义下传。当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 155 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，cycle-safe file manifests）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，为 `build_tool_registry_from_file()` 增加 `_visited_files / _visited_dirs / _visited_sources` 防护；现在 `registry_sources / registry_files / registry_dirs` 三条装配链在遇到自循环、重复文件、重复目录和重复 source 时都会安全忽略已访问项，不再递归炸栈。当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 176 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，file-registry diagnostics artifacts）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_from_file_artifacts()`，把 file-backed registry 装配过程统一收口为 `registry + diagnostics`，并产出 `skipped/missing registry_sources`、`registry_files`、`registry_dirs` 三类内部观测结果。当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 178 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，diagnostics artifact chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，把 diagnostics seam 从底层 file helper 上提到高层 loader/provider/settings source 路径；新增 `build_tool_registry_loader_from_file_artifacts()`、`build_tool_registry_provider_from_file_artifacts()`、`build_tool_registry_loaders_from_settings_artifacts()`、`build_tool_registry_providers_from_settings_artifacts()`、`build_tool_registry_provider_sources_from_settings_artifacts()` 与 `get_configured_tool_registry_provider_artifacts()`。当前前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 183 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，diagnostics runtime artifacts chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_diagnostics_summary()`、`build_tool_registry_diagnostics_runtime_artifacts()` 与 `build_configured_tool_registry_provider_runtime_artifacts()`，把 diagnostics 进一步推进到 runtime 可直接消费的 summary / trace-candidate / audit-candidate；当前 chat 路径已通过这个更高层入口拿 `provider`，但前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 187 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，diagnostics audit wiring）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_diagnostics_audit_event()` 并在 chat 路径里把 `tool_registry_diagnostics` 写入内部 audit；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 189 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，diagnostics audit action chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_diagnostics_audit_service_action()`、`build_configured_tool_registry_provider_runtime_service_actions()` 与 `execute_configured_tool_registry_provider_runtime_service_actions()`，把内部 audit 这条 side-effect 链也收口到了 runtime；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 192 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-18，diagnostics internal trace action chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_tool_registry_diagnostics_trace_service_action()`，并让 configured provider runtime 动作链同时处理 internal trace persist 与 audit；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 193 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，provider preflight service execution chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_service_execution()` 与 `execute_configured_tool_registry_provider_service_execution()`，把 provider 预构建阶段统一成更高层 `service_execution` 入口；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 195 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，provider preflight single-entry chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `execute_configured_tool_registry_provider_preflight()`，把 provider 预构建阶段进一步统一成单入口 helper；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 196 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，provider preflight structured result chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_result()` 与 `build_configured_tool_registry_provider_preflight_summary()`，把 provider preflight 的返回结果进一步统一成结构化形状；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本已扩展到 198 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，provider preflight enriched summary chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，扩展 `build_configured_tool_registry_provider_preflight_summary()`，让 provider preflight 的内部摘要带上更完整的结构化指标，包括 `tool_names` 与 `service_action_kinds`；前端可见的 SSE/trace 契约仍保持不变。focused 回归脚本仍为 198 条兼容测试全绿，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，provider preflight typed model chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ConfiguredToolRegistryProviderPreflightSummaryModel` 与 `ConfiguredToolRegistryProviderPreflightResultModel`，把 preflight 内部承载 typed 化，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 200 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，diagnostics typed model chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ToolRegistryDiagnosticsSummaryModel` 与 `ToolRegistryDiagnosticsRuntimeArtifactsModel`，让 diagnostics 这侧也具备 typed internal 承载，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 202 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，configured runtime artifacts typed model chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ConfiguredToolRegistryProviderRuntimeArtifactsModel`，让 configured provider runtime artifacts 这层也具备 typed internal 承载，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 203 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，service execution typed model chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ConfiguredToolRegistryProviderServiceExecutionModel` 与 `ConfiguredToolRegistryProviderServiceExecutionResultModel`，让 service execution 这层也具备 typed internal 承载，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 205 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，runtime service actions typed model chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `ConfiguredToolRegistryProviderRuntimeServiceActionModel`、`ConfiguredToolRegistryProviderRuntimeServiceActionsModel` 与 `ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel`，让 provider preflight 的内部 trace/audit service actions 这层也具备 typed internal 承载，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 209 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，typed preflight result chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()`、`build_configured_tool_registry_provider_preflight_result_model_from_models()` 与 `execute_configured_tool_registry_provider_preflight_model()`，让 preflight 内部结果链也具备 typed model 直连，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 211 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，typed service_execution execution chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_service_execution_result_model_from_models()` 与 `execute_configured_tool_registry_provider_service_execution_model()`，让 service_execution 内部执行结果链也具备 typed model 直连，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 213 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，typed runtime_service_actions execution chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_runtime_service_action_model_from_dict()`、`build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts()` 与 `execute_configured_tool_registry_provider_runtime_service_actions_model()`，让最底层 runtime service actions 执行器输入也具备 typed model 直连，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 215 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，shared hydration helper chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_runtime_artifacts_model_from_dict()` 与 `build_configured_tool_registry_provider_service_execution_model_from_dict()`，让 runtime artifacts / service execution 的共享 hydration 也具备统一 helper，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 217 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，preflight_result shared bridge chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_result_model_from_dict()`，并让 preflight summary/result 的 dict bridge 统一复用这层共享 helper，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 218 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-19，typed preflight summary builder chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_summary_model_from_models()`，让 preflight typed result 链直接走真实 summary builder，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本维持 218 条兼容测试全绿，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-20，shared preflight summary builder chain）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_summary_model_from_parts()`，让 preflight summary 的两条 typed builder 路径统一复用共享逻辑，同时保持前端可见的 SSE/trace 契约不变。focused 回归脚本已扩展到 219 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight_result dict bridge thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现在会在最小顶层 payload 下从 `service_execution` 继承 `provider/provider_source_name/runtime_artifacts`，并直接复用 typed result builder，前端可见的 SSE/trace 契约保持不变。focused 回归脚本已扩展到 221 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，service_execution_result count bridge thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增共享 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，并让 `service_execution_result` / `preflight_result` 两条计数 hydration 链统一复用；同时 `service_execution_result` 在最小 `execution_result={}` 场景下也会默认回退 `trace_write_count/audit_event_count=0`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 222 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight_summary bridge thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()`，并让 `preflight_summary_model` 直接复用这层 dict bridge；最小顶层 `preflight_result` 仍会从 `service_execution` 继承 provider/runtime_artifacts 默认值。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 223 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight service_execution normalization bridge）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增共享 `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`，把 `preflight_summary` / `preflight_result` 两条 dict bridge 共有的 provider/provider_source_name/runtime_artifacts 归一化统一到单点 helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 224 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight service_execution_result normalization bridge）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增共享 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，把 `preflight_result` 顶层计数与共享 `service_execution` 归一化进一步统一到单点 helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 225 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight execution models shared helper）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增共享 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，把 `preflight_summary` / `preflight_result` 两条 dict bridge 共同依赖的 typed pair 统一到单点 helper，并去掉 `preflight_result` 侧一层多余的 `model -> dict -> model` 往返。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 226 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight execution-result typed helper refinement）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，让 `preflight execution models` 共享 helper 不再重复计算 `service_execution_model`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 227 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，service_execution_result typed helper unification）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，把通用 `service_execution_result` 与 preflight execution-result 两条 typed helper 统一到同一层复用。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 228 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight_result typed helper unification）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，把 `preflight_result` 这条 typed 入口也统一到已有 helper 组合上。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 229 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight_summary typed helper unification）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`，把 `preflight_summary` 这条 typed 入口也统一到已有 helper 组合上。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 230 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight_result dict bridge typed-entry thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现在也已直接走 `service_execution_model -> preflight_result typed helper` 入口，不再经过共享 typed pair helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 231 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight execution-models helper thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在也已直接组合现有 dict helper，不再自己显式串联更深一层的 typed execution-result helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 232 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight execution-models typed helper unification）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，并让 `...from_dict()` 直接复用这层 typed pair 入口，避免重复 hydration `service_execution_model`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 233 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-21，preflight execution-models production reuse）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 与 `...preflight_result_model_from_service_execution_model()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 234 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight service-execution-result bridge thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 235 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight service-execution-result typed-wrapper thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 236 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight summary typed-entry thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 237 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight result typed-entry thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本维持 237 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight execution-models helper thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 现在也已直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，而 `preflight_service_execution_result_model_from_service_execution_model()` 则直接走通用 `service_execution_result` helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 238 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight execution-models dict-helper thinning）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在也已直接走通用 `service_execution_result` helper，而 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 则直接复用它。前端可见的 SSE/trace 契约保持不变，focused 回归脚本维持 238 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight summary-result dict-entry concentration）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现在也已统一复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 239 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight payload-normalization seam）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，并让 `preflight_service_execution_model/result/execution_models` 三层 dict helper 统一复用它。前端可见的 SSE/trace 契约保持不变，focused 回归脚本已扩展到 240 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight payload-to-pair seam）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()`，并让 `preflight_service_execution_model/result/execution_models` 三条 dict 入口统一复用这层 “normalized payload -> typed pair” helper。前端可见的 SSE/trace 契约保持不变，focused 回归脚本维持 240 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-25，preflight dict-shell concentration）：后端已继续把 runtime seam 往“真实 registry 可接入”方向推进，`build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()` 与 `...preflight_service_execution_result_model_from_dict()` 现在也已统一退回到 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 这条公开 dict 入口。前端可见的 SSE/trace 契约保持不变，focused 回归脚本维持 240 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过
- 阶段 5 协同（2026-05-14，design checkpoint）：后端已把 `tool-runtime-productionization` 的 design/handoff 文档同步到当前真实状态，并明确当前 helper 分层已经达到阶段性合理停止点；当前前端消费的 SSE/trace 契约无需调整，后续只有在新需求触发时才建议继续 runtime 抽象
- 新会话交接文档（2026-05-13）：后端已新增 [docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md)，用于在新会话中继续推进 runtime 收口；当前前端消费的 SSE/trace 契约无需调整
- 阶段 5 增量：`running-task-recovery` 前端首版已落地；刷新页面或切回会话时会自动接管该会话下 `pending/running` 任务流，并展示恢复中/成功/失败提示
- 阶段 5 修复：会话切换时的任务串台已修复；流式状态按 `session_id` 绑定并按当前会话隔离渲染，避免短暂显示其他会话任务
- 阶段 5 修复：恢复提示误报已修复；任务结束瞬间若列表状态滞后，自动恢复不再错误提示“任务流恢复失败”
- 阶段 5 修复：聊天区滚动体验已修复；流式输出期间用户主动上滑阅读历史消息时，不再被强制拉回底部
- 阶段 5 修复：任务取消/超时后即使收到 `error(task_cancelled/task_timeout)`，也不再误判为失败态并显示“重试上次发送”
- 阶段 5 修复：流结束后的 `trace/delta` 自动补拉改为静默，不再覆盖底部状态为“暂无新的轨迹增量”
- 阶段 5 修复：待发送用户消息去重改为按 `task_id`，取消后再次发送相同文案会即时显示，不再被上一条同文案误隐藏
- 阶段 5 修复：发送后立即刷新 `tasks/messages`，并在任务列表回刷前用流式任务兜底展示“当前任务”取消按钮
- 阶段 5 修复：取消任务成功后会本地中断活动 SSE 流并立即退出“生成中”状态，发送按钮无需等待长延迟即可恢复
- 阶段 5 修复：remote 模式取消后加入短暂发送冷却，避免“取消后立刻重发”触发远端模型限流
- 阶段 5 交互升级：消息区“回到底部”按钮锚定在聊天区右下角（不随消息内容滚动）；上滑阅读期间若有新增输出，会显示数字徽标与轻脉冲提示
- 阶段 5 交互微调：回底按钮进一步上移+右移，减少对底部消息气泡与输入区的视觉遮挡
- 阶段 5 增量：`usage-dashboard-lite` 首版已落地；设置弹窗新增“用量统计”入口，支持全局/当前会话切换、趋势条形图、会话榜与任务榜
- 阶段 5 增量：`audit-event-expansion` 首版已落地；审计页支持筛选与展示新增事件（设置校验、任务创建/取消/超时/失败、知识库 ingest/清空/删除）
- 阶段 5 协同：`provider-usage-alignment` 后端首版已落地；任务 `done.usage` 改为 provider 官方 usage 优先，缺失字段自动回退估算并带来源标记
- 阶段 5 协同：usage 来源可视化已补齐（当前任务 + 任务中心/任务详情展示 provider/estimated）
- 阶段 5 协同：用量统计弹窗已补“来源分布”展示（provider/estimated/mixed/legacy），并对历史无来源字段数据标记为 legacy
- 阶段 5 协同：用量统计弹窗新增来源筛选（全部/官方/估算/混合/旧数据），按来源拉取并展示 dashboard 数据
- 阶段 5 协同：用量统计弹窗新增“来源趋势”分区，按天展示 provider/estimated/mixed/legacy 任务数，便于排查来源结构变化
- 阶段 5 增量：前端可视化回归 CI 首版已接入（Playwright），新增 `usage-dashboard` 主路径 smoke 用例，并接入 `.github/workflows/frontend-e2e.yml`
- 阶段 5 CI 对齐：`frontend-e2e` 工作流中的 `actions/setup-node` 与 `actions/upload-artifact` 已分别升级到 `v5` 与 `v7`，并启用 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`，避免 Node 20 action 弃用告警
- 阶段 5 修复：Playwright 登录态注入修正为显式透传 `localStorage` key，避免浏览器上下文无法访问测试常量导致未登录态误失败
- 阶段 5 修复（补充）：`usage-dashboard` 用例新增 Workbench 检测与 UI 登录兜底，CI 中即使未命中登录态注入也可稳定继续执行
- 阶段 5 回归扩展：Playwright 用量统计回归升级为双场景（来源趋势可见 + 设置治理入口可见性），并为设置菜单项补充稳定测试标识 `settings-menu-audit/settings-menu-knowledge-base/settings-menu-model`
- 阶段 5 回归扩展（二次）：新增 `workbench-main-path` 用例，覆盖发送消息、Trace 可见、RAG ingest/query、任务与会话导出（JSON/Markdown）、运行中任务刷新恢复与取消后重发
- 阶段 5 回归扩展（三次）：新增 `workbench-edge-cases` 用例，覆盖 RAG 空命中可见性与导出接口缺失资源 `404` 语义
- 阶段 5 回归工程化：抽取 `e2e/helpers/workbench.ts` 统一鉴权注入与 Workbench 就绪逻辑，降低多 spec 重复代码
- 阶段 5 回归矩阵：Playwright 新增 `firefox/webkit` 项目；CI 改为 smoke 三浏览器 + chromium 全量；并新增 remote 错误码映射回归；本地回归已验证 chromium 全量 `25/25` 与 smoke 矩阵 `15/15`
- 阶段 5 回归深化：为 usage dashboard / 知识库治理 / 聊天回底按钮补充稳定测试锚点（`data-testid`），并新增细粒度断言（来源筛选请求参数、表头左对齐、治理动作无边框文本按钮、上滑阅读时回底按钮显隐与回底）
- 阶段 5 回归深化（二次）：`workbench-remote-errors` 新增 remote `503` 错误码映射与“取消后发送冷却恢复”回归（冷却期阻断重复发送、冷却结束恢复发送），并使用本地 mock OpenAI-compatible 流服务稳定复现
- 阶段 5 回归深化（三次）：新增模型设置弹窗 `settings/validate` 异常态回归（`remote_api_key_unauthorized`、`remote_preflight_network_error`），并为模型设置控件补稳定 `data-testid`（`model-settings-*`）以降低多语言文案依赖导致的波动
- 阶段 5 回归深化（四次）：新增流式异常态回归（`remote_provider_stream_invalid_json`、`remote_provider_stream_interrupted`）并将 Context tab 打开逻辑收敛为“重试点击直到 `#inspector-panel-context` 可见”，降低恢复流与 Tabs 自动切换并发导致的抖动
- 阶段 5 回归深化（五次）：`workbench-edge-cases` 补齐导出异常态语义（空会话导出 JSON/Markdown、跨用户 task/session 导出隔离 404），覆盖空数据与权限边界
- 阶段 5 回归深化（2026-05-08）：`workbench-edge-cases` 新增“导出下载响应头一致性”回归，覆盖 task/session JSON/Markdown `download=true` 的 `Content-Type` 与 `Content-Disposition` 扩展名匹配
- 阶段 5 回归深化（2026-05-08 补充）：`workbench-main-path` 导出断言升级为“UI 下载事件 + 同路径 API 响应头”双重校验，覆盖 task/session JSON/Markdown 的 `Content-Type` 与附件扩展名一致性
- 阶段 5 回归深化（六次）：导出错误提示统一走 `ApiError` 映射（避免直接暴露后端原始 detail）；新增 UI 回归验证“切换 token 后导出 404 提示 + 按钮恢复”
- 阶段 5 回归深化（七次）：`workbench-main-path` 恢复取消链路稳态加固，新增“发送后先确认后端 running/pending 再刷新”与“等待取消按钮期间持续维持 Context 激活”断言，修复自动恢复切回 Trace 导致的偶发失败；本地 chromium 全量回归更新为 `22/22`
- 阶段 5 回归深化（八次）：`workbench-edge-cases` 一次性补齐 3 条会话与取消交互回归（取消后同文案即时重发不丢消息、跨会话切换时流式状态不串台且切回可取消、mock 取消后不出现重试入口并可快速恢复发送）；本地 chromium 全量回归更新为 `25/25`
- 阶段 5 回归深化（九次）：一次性补齐剩余 6 项回归覆盖：恢复提示三态（恢复中/成功/失败）、trace delta 重试与后台暂停/前台恢复、auth refresh 自动续期与 `logout-all` 后强制重登、设置弹窗/治理子弹窗重开状态重置；本地 chromium 全量回归更新为 `30/30`。
- 阶段 5 CI 稳定性增强：`frontend-e2e` 新增同分支并发互斥（取消旧运行）、失败后 `--last-failed` 诊断重跑、失败索引文件（`error-context.md`/`trace.zip` 列表）和带 `run_id/run_attempt` 的 artifact 命名，提升失败排查效率。
- 阶段 5 CI 诊断增强（2026-05-08）：`frontend-e2e` 导出断言摘要已扩展覆盖 `workbench-main-path` 与 `workbench-edge-cases`，自动提取 UI 下载层/响应头层/API 路径/404 语义提示计数及关键行，输出到 `GITHUB_STEP_SUMMARY` 与 `/tmp/frontend-e2e-export-summary.md` artifact
- 阶段 5 CI 诊断增强（2026-05-09）：导出断言摘要新增 `workbench-main-path-shared-kb` 分区；当 shared 权限主链路用例出现失败上下文时，会单独统计 `shared_permission_semantic_ok` 并输出关键行，便于快速定位 `shared-*` 权限语义回归
- 阶段 5 CI 告警汇总补齐（2026-05-09）：`threshold alerts` 新增 shared 分区汇总行（`shared_scope: ... contexts=..., shared_permission_semantic_ok=...`），无告警时也可确认 shared 权限诊断覆盖情况
- 阶段 5 CI 摘要语义收口（2026-05-09）：shared 分区新增 `expected` 文案（shared 失败上下文存在时期望 `>=1`，不存在时期望 `0`），并在无上下文场景也输出 `shared_permission_semantic_ok`，降低诊断歧义
- 阶段 5 CI 稳态补充（2026-05-09）：shared 分区的 error-context 归类规则改为正则匹配（`workbench-main-path.*shared.*kb`），降低测试命名微调导致的诊断漏命中
- 阶段 5 CI 稳态补充（2026-05-09 再补充）：shared 分区路径匹配已变量化并收紧为 `SHARED_CONTEXT_PATH_REGEX=workbench-main-path.*(shared-kb-actions-disabled|shared.*kb.*disabled)`，减少主链路其他失败上下文被误归类到 shared 分区
- 阶段 5 CI 维护性补充（2026-05-09）：导出摘要对 `error-context.md` 的扫描已收敛为单次 `find` 后分组（main/shared/edge），减少重复扫描并提升分区计数口径一致性
- 阶段 5 CI 维护性补充（2026-05-09 再补充）：导出摘要新增 `add_warning` 统一告警函数，集中维护 `P0/P1` 计数与提示文案拼装，降低阈值规则扩展的重复改动
- 阶段 5 CI 准确性补充（2026-05-09）：`workbench-main-path` 分区已排除 shared 专项上下文（基于 `SHARED_CONTEXT_PATH_REGEX` 反向过滤），避免 shared 用例失败时把噪音计入主链路导出告警
- 阶段 5 协同说明（2026-05-13）：当前轮进入后端 `tool-runtime-productionization` 连续小切片，已完成运行时最小 registry 化、显式 `ToolInvocation` 归一化边界与带最小元信息（`kind/label/retryable_by_default/default_timeout_ms/requires_user_context/supports_result_preview`）的 `ToolRegistration` 注册项结构收口；同时后端已开始用多个内部 helper 与 `ToolRuntimeContext` 消费这些注册项元信息，并进一步把 action step 初始组装、tool_start payload、tool success/error 元信息、tool_end payload、phase 与执行 policy 一并下沉到 runtime helper，但前端可见行为与现有 Playwright/e2e 契约保持不变
- 阶段 5 CI 规则收口补充（2026-05-09）：新增 `MAIN_CONTEXT_PATH_REGEX` / `EDGE_CONTEXT_PATH_REGEX`，main/edge/shared 三分区匹配统一改为变量化入口，降低后续规则调整时的改动分散度
- 阶段 5 CI 维护性补充（2026-05-09 三次）：导出摘要新增 `print_matched_files` / `print_key_lines` 统一输出函数，收敛 main/shared/edge 分区的重复打印逻辑并提升一致性
- 阶段 5 CI 可见性补充（2026-05-09）：main/shared/edge 三分区断言计数均新增 `context_files_detected`，便于直接比对该分区当前计数是否具备对应失败上下文样本
- 阶段 5 CI 工程化重构（2026-05-09）：导出诊断逻辑已从 `.github/workflows/frontend-e2e.yml` 内联 Bash 抽离为 `frontend/scripts/ci_export_diagnostics.sh`，并补齐 Bash 3 兼容（去除 `mapfile`），支持本地与 CI 共用同一套诊断脚本
- 阶段 5 CI 回归护栏补齐（2026-05-09）：新增 `frontend/scripts/test_ci_export_diagnostics.sh` fixture 自测脚本，并在 workflow 增加 `Validate export diagnostics fixture tests` 步骤，保障导出诊断脚本 counters/alerts 语义在主回归前先被校验
- 阶段 5 CI 机器可读补充（2026-05-09）：`frontend/scripts/ci_export_diagnostics.sh` 新增可选 JSON 输出参数，`frontend-e2e` 已产出 `/tmp/frontend-e2e-export-summary.json` 并随 artifact 上传，便于后续趋势分析与自动告警消费
- 阶段 5 CI 统一门禁补充（2026-05-09）：新增仓库级 `scripts/ci_diag_guard.sh` 并在 `frontend-e2e` 接入 `Evaluate export diagnostics guard`；可通过 `FRONTEND_EXPORT_DIAG_STRICT_LEVEL=none|p0|any` 控制门禁严格度（默认 `none`）
- 阶段 5 CI 统一门禁再补充（2026-05-09）：`frontend-e2e` 默认门禁级别已提升为 `p0`，并将 guard 判定摘要追加到 `GITHUB_STEP_SUMMARY`（同时归档 `/tmp/frontend-e2e-export-guard-summary.md`），便于直接判断门禁失败原因
- 阶段 5 CI 门禁策略化补充（2026-05-09）：`frontend-e2e` 门禁级别已改为按事件自动决策（`push@main=any`、其余场景 `p0`），并在 summary 输出 `policy + selected_strict_level`，提升诊断判读一致性
- 阶段 5 CI 门禁 JSON 补充（2026-05-09）：`ci_diag_guard` 已支持 `--json-summary-file`，`frontend-e2e` 现产出 `/tmp/frontend-e2e-export-guard-summary.json` 并上传 artifact，便于后续自动汇总门禁结果
- 阶段 5 CI 触发覆盖补充（2026-05-09）：`frontend-e2e` 的 `workflow_dispatch` 新增 `export_diag_strict_level=auto/none/p0/any`，支持手动触发覆盖自动策略；summary 已输出 `dispatch_override` 与 `policy_source`
- 阶段 5 CI 总览聚合补充（2026-05-09）：新增 `scripts/ci_export_diagnostics_overview.sh`（配套 `scripts/test_ci_export_diagnostics_overview.sh`），workflow 已接入 `Build export diagnostics overview` 并产出 `/tmp/frontend-e2e-export-overview.md/.json`
- 阶段 5 CI 策略解析收口（2026-05-09）：新增 `scripts/ci_resolve_diag_strict_level.sh`（配套 `scripts/test_ci_resolve_diag_strict_level.sh`），`frontend-e2e` 的 strict-level 选择逻辑改为脚本解析，统一 `event/ref/default/main_push/dispatch_override` 决策口径
- 阶段 5 CI fixture 入口收口（2026-05-09）：新增 `scripts/test_ci_e2e_tooling.sh` 聚合测试入口，`frontend-e2e` 已改为单步骤 `Validate e2e tooling fixtures (frontend scope)`，统一执行 common + frontend 相关 fixture 测试
- 阶段 5 CI 流水线收口（2026-05-09）：新增 `scripts/ci_export_diag_pipeline.sh`（配套 `scripts/test_ci_export_diag_pipeline.sh`），将 strict-level 解析、guard 判定、overview 产物和 step summary 拼接整合为单入口；`frontend-e2e` 已切换为 `Run export diagnostics pipeline`
- 阶段 5 CI 输出降噪（2026-05-09）：`ci_diag_guard` 新增 `--quiet`，并在 guard/resolver fixture 脚本中抑制预期失败分支输出，降低 fixture 校验步骤日志噪音
- 阶段 5 CI 启动验活收口（2026-05-09）：新增 `scripts/ci_start_bg_process.sh` 与 `scripts/ci_wait_http_status.sh`（配套 `scripts/test_ci_service_bootstrap.sh`），`frontend-e2e` 的后端启动与健康等待已切换到统一脚本调用，减少 workflow 内重复 shell 逻辑
- 阶段 5 CI 诊断流程再收口（2026-05-09）：新增 `scripts/ci_export_diag_flow.sh`（配套 `scripts/test_ci_export_diag_flow.sh`），把导出诊断摘要生成与 guard/overview pipeline 合并为单步骤入口；`frontend-e2e` 已切换为 `Run export diagnostics flow`
- 阶段 5 CI artifact 收口（2026-05-09）：新增 `scripts/ci_artifacts_frontend.txt` 与统一归集脚本 `scripts/ci_stage_artifacts.sh`（配套 `scripts/test_ci_stage_artifacts.sh`）；`frontend-e2e` 新增 `Stage frontend e2e artifacts`，上传动作改为 staging 目录，降低 YAML 路径清单维护复杂度
- 阶段 5 CI 失败索引脚本化（2026-05-09）：新增 `scripts/ci_build_frontend_failure_index.sh`（配套 `scripts/test_ci_build_frontend_failure_index.sh`），`frontend-e2e` 的 Playwright 失败索引生成已改为脚本调用，统一输出结构并减少 workflow 内联 shell 体积
- 阶段 5 CI 执行入口收口（2026-05-09）：新增 `scripts/ci_run_frontend_e2e.sh`（配套 `scripts/test_ci_run_frontend_e2e.sh`），`frontend-e2e` 的 smoke/full/rerun 执行步骤已统一为脚本调用；支持 `--phase` 与 `--dry-run`，便于本地语义校验与命令参数维护
- 阶段 5 CI backend 启动收口（2026-05-09）：新增 `scripts/ci_boot_backend_instance.sh`（配套 `scripts/test_ci_boot_backend_instance.sh`），`frontend-e2e` 的 backend 启动与健康等待已合并为单入口脚本调用，减少 workflow 步骤分叉
- 阶段 5 CI finalize 编排收口（2026-05-09）：新增 `scripts/ci_finalize_e2e_scope.sh`（配套 `scripts/test_ci_finalize_e2e_scope.sh`），`frontend-e2e` 的导出诊断与 artifact stage 已合并为单步骤 finalize 调用，降低收尾配置维护成本
- 阶段 5 CI 失败日志展示收口（2026-05-09）：新增 `scripts/ci_print_log_files.sh`（配套 `scripts/test_ci_print_log_files.sh`），`frontend-e2e` 的 backend 失败日志展示已改为脚本调用；同时 `/tmp/frontend-e2e-backend.log` 已纳入 frontend artifact 清单
- 阶段 5 CI upload 路径解耦（2026-05-09）：`ci_finalize_e2e_scope.sh` 新增 `--github-output-file` 输出，`frontend-e2e` 的 upload path 改为读取 `finalize_frontend.outputs.artifacts_stage_dir`，减少 workflow 中 stage 路径硬编码
- 阶段 5 CI upload 命名解耦（2026-05-09）：`ci_finalize_e2e_scope.sh` 新增 `artifact_name` 输出，`frontend-e2e` 的 upload `name` 字段改为读取 `finalize_frontend.outputs.artifact_name`，命名策略集中到 finalize 调用参数
- 阶段 5 CI finalize workflow 入口收口（2026-05-11）：新增 `scripts/ci_finalize_e2e_for_workflow.sh`（配套 `scripts/test_ci_finalize_e2e_for_workflow.sh`），`frontend-e2e` 的 finalize 步骤已改为单入口脚本调用，统一 strict-level 默认值、事件上下文与 artifact 命名组装逻辑
- 阶段 5 CI artifact stage 指标补齐（2026-05-11）：`ci_finalize_e2e_scope.sh` 现会输出 `artifact_included_count/artifact_missing_count/artifact_manifest`，并在 summary 追加 `frontend-e2e artifact stage` 小节，便于快速区分“测试失败导致无产物”与“上传配置异常”
- 阶段 5 CI artifact stage 门禁补齐（2026-05-11）：新增 `scripts/ci_assert_artifact_stage_health.sh`（配套 `scripts/test_ci_assert_artifact_stage_health.sh`），`frontend-e2e` 新增 `Evaluate frontend artifact stage guard` 并产出 `/tmp/frontend-e2e-artifact-guard-summary.md/.json`，默认 `strict-level=warn` 后续可按分支策略上调
- 阶段 5 CI artifact stage 策略解析收口（2026-05-11）：新增 `scripts/ci_resolve_artifact_stage_strict_level.sh`（配套 `scripts/test_ci_resolve_artifact_stage_strict_level.sh`），`frontend-e2e` 的 artifact guard strict-level 改为脚本按事件自动解析并支持 `workflow_dispatch` 覆盖（`auto/none/warn/fail-on-empty/fail-on-missing`）；当前策略为 `push@main=warn`、其余 `warn`
- 阶段 5 CI artifact stage 防误伤补丁（2026-05-11）：`frontend-e2e` 的 artifact guard 改为仅在 `finalize_frontend` 成功时执行；若 finalize 失败则写入 `skipped` 摘要并不追加二次失败，避免掩盖真实首错步骤
- 阶段 5 CI artifact stage PR 门禁扩展（2026-05-12）：`frontend-e2e` 的 artifact guard 现支持 `min_included_count` 阈值，并将 `pull_request` 场景扩展为可选 `fail-on-empty` 策略源；当前 workflow 已为 PR/关键分支场景启用 `fail-on-empty + min_included_count=2`，同时保留 `push@main=warn` 以兼容既有单产物路径
- 阶段 5 CI workflow guard 收口（2026-05-13）：`frontend-e2e` workflow 已移除对 `--guard-markdown-out/--guard-json-out` 的显式传参，artifact/export guard 输出路径统一交由 finalize/scope 脚本解析；`scripts/test_ci_workflow_guards.sh` 同步改为验证“workflow 继续调用统一 guard 脚本，但不再硬编码 guard 输出路径”
- 阶段 5 CI artifact upload 防二次报错补丁（2026-05-12）：`frontend-e2e` 的 upload 步骤改为仅在 `finalize_frontend` 成功时执行，避免 finalize 失败后继续触发 `actions/upload-artifact` 的空 path 报错；并新增 `scripts/test_ci_workflow_guards.sh` 静态校验 workflow guard 条件
- 阶段 5 CI artifact PR 路径感知扩展（2026-05-12）：`frontend-e2e` 新增 `ci_resolve_artifact_stage_path_level.sh`、`ci_collect_changed_files.sh`、`ci_resolve_artifact_stage_scope_config.sh`、`ci_load_artifact_stage_scope_config.sh`、`ci_run_artifact_stage_guard.sh` 与 `ci_write_skipped_artifact_guard_summary.sh`，PR 只有在命中 frontend/backend/compose/workflow 关键路径时才升级 artifact guard；workflow 已将 artifact guard 主逻辑与 finalize 失败时的 skipped summary 下沉到脚本，统一先通过 scope 配置脚本生成规则，再通过 load helper 注入 changed-files 路径、fallback paths、path-regex、`pr_ref_regex` 与 guard 摘要元信息，`actions/checkout` 使用 `fetch-depth: 0`，并在 base diff 不可解析时回退关键路径标记。同时 path-regex 已修正为可命中真实 `frontend/...` / `backend/...` 改动与关键单文件路径，降低浅克隆、缺失 base SHA 与旧正则过窄带来的误判概率
- 阶段 5 CI fixture 稳定性修复（2026-05-11）：`scripts/test_ci_finalize_e2e_for_workflow.sh` 的“缺失事件上下文应失败”断言改为显式清空 `GITHUB_EVENT_NAME/GITHUB_REF` 后执行，修复 GitHub Actions 环境变量导致的假阳性失败
- 阶段 5 CI 告警增强（2026-05-08）：`frontend-e2e` 导出摘要新增 `threshold alerts` 阈值告警；若主链路或边界链路计数低于预期，会直接输出 expected vs actual，便于快速定位“下载层 / 响应头层 / 404 语义层”回归
- 阶段 5 CI 告警分级（2026-05-08）：`frontend-e2e` 导出阈值告警已补严重级别标签（当前为 `[P1]`）与 `severity` 计数，并与 `backend-e2e` 告警视图对齐，便于跨端统一判读
- 阶段 5 CI 告警分级补强（2026-05-08）：`frontend-e2e` 已新增 `P0` 判定规则：若存在 `error-context` 但 `export_api_path_hints=0`，或 UI 下载层/响应头层提示同时为 0（edge-cases 还包含 `export_404_semantic_hints=0`），则升级为 `P0` 告警
- 阶段 5 CI 告警模板统一（2026-05-08）：`frontend-e2e` 与 `backend-e2e` 导出摘要字段顺序已统一为 `total_alerts -> severity -> 分级明细`，并保持一致的分级标签格式，方便跨工作流横向比对
- 阶段 5 CI 规则收口（2026-05-08）：`frontend-e2e` 导出摘要中的 UI/响应头/API/404 语义计数与 `key lines` 提取规则已集中为变量块；并补齐 `total_alerts=0` 时的 `severity: P0=0, P1=0` 输出
- 阶段 5 回归稳态收口（十次，2026-04-22）：修复 `workbench-edge-cases` 并发回归下的偶发失败，Context tab helper 改为仅命中 Inspector 顶部导航；“取消后同文案重发”用例改为“API cancel + UI 去重可见性断言”以规避流式 tab 抢占时序，chromium 全量回归再次验证 `30/30` 通过。
- 阶段 5 回归稳态收口（十一次，2026-04-22）：修复 `workbench-edge-cases` “切换 token 后导出 404”竞态（切 token 前先等待任务详情导出按钮可用），并按 CI 同口径串行回归（`--workers=1`）复测 chromium 全量 `30/30` 通过。
- 阶段 5 稳定性补丁：后端 `mock` provider 新增测试触发慢流标记（`[mock-slow]` / `[mock-slow-ms=30]`），用于稳定复现取消恢复场景，普通请求无行为变化
- 阶段 5 协同：后端 `e2e_export_consistency` 已扩展覆盖跨用户导出隔离 404（task/session），导出稳定性（任务/会话 JSON+Markdown 一致性 + 下载头 + 权限边界）已有自动回归兜底
- 阶段 5 协同（2026-05-08）：后端 `e2e_export_consistency` 已补导出 `Content-Type` 断言（JSON/Markdown + 下载场景），前端导出链路可更早发现 MIME 类型回归
- 阶段 5 协同（2026-05-09）：后端 `e2e_export_consistency` 已补 `shared-*` 跨角色断言（非 admin 写共享库 `403`；admin 写后普通用户可读），可更早发现“共享权限改动影响导出主链路”的回归
- 阶段 5 协同：后端 `backend-e2e` 已新增失败快照归档（日志/health/诊断 artifact），前端联调排障可直接下载复盘
- 阶段 5 协同（2026-05-08）：后端 `backend-e2e` 已新增 export consistency CI Summary 快照与摘要 artifact（`/tmp/e2e-export-consistency-summary.txt`），并补充断言计数统计（steps/ok/pass/task-export/session-export/shared-rag/cross-user/not-found）；失败诊断追加导出一致性日志 tail，便于快速核对导出链路回归
- 阶段 5 协同（2026-05-09）：后端 `backend-e2e` export consistency 摘要阈值已对齐 7 步脚本输出（`steps/ok` 期望值同步更新）并补充 `shared_rag_semantics_ok` 计数，前端联调时可更早识别共享知识库权限语义回归
- 阶段 5 协同（2026-05-09 补充）：后端 `backend-e2e` export consistency 步数阈值已改为动态解析（从日志首条 `[x/N]` 自动提取 `N`），后续脚本步骤调整时前端联调无需再关注硬编码步数漂移
- 阶段 5 协同（2026-05-09 维护性补充）：后端 `backend-e2e` export consistency 摘要已补 `add_warning` 统一告警函数，前后端 CI 告警拼装逻辑风格进一步对齐
- 阶段 5 协同（2026-05-09 工程化补充）：后端 `backend-e2e` export consistency 摘要已抽离为 `backend/scripts/ci_export_consistency_summary.sh` 并接入 workflow 脚本调用，前后端导出诊断均已完成“workflow 轻量化 + 脚本单点维护”收口
- 阶段 5 协同（2026-05-09 回归护栏补充）：后端已新增 `backend/scripts/test_ci_export_consistency_summary.sh` fixture 自测并接入 `backend-e2e`，前后端导出诊断脚本均具备 workflow 前置语义校验
- 阶段 5 协同（2026-05-09 机器可读补充）：后端 `ci_export_consistency_summary.sh` 已支持 JSON 输出并在 CI 产出 `/tmp/e2e-export-consistency-summary.json`，可与前端 JSON 摘要对齐做跨端诊断汇总
- 阶段 5 协同（2026-05-09 统一门禁补充）：后端 `backend-e2e` 已接入同一 `scripts/ci_diag_guard.sh` 门禁步骤（`BACKEND_EXPORT_DIAG_STRICT_LEVEL`），前后端门禁策略统一到 `none|p0|any` 三档
- 阶段 5 协同（2026-05-09 统一门禁再补充）：后端默认门禁级别同步提升为 `p0`，并在 summary 输出同结构 guard 小节，前后端门禁默认值与输出格式保持一致
- 阶段 5 协同（2026-05-09 门禁策略化补充）：后端同步采用 `push@main=any / 其他=p0` 自动策略并输出 `selected_strict_level`，前后端门禁选择逻辑与展示项对齐
- 阶段 5 协同（2026-05-09 门禁 JSON 补充）：后端同步产出 `/tmp/backend-e2e-export-guard-summary.json`，前后端 guard 摘要均支持 Markdown + JSON 双格式消费
- 阶段 5 协同（2026-05-09 触发覆盖补充）：后端同步接入 `workflow_dispatch` 的 `export_diag_strict_level` 覆盖能力，并输出 `dispatch_override/policy_source`，前后端触发策略一致
- 阶段 5 协同（2026-05-09 总览聚合补充）：后端同步接入 overview 聚合并产出 `/tmp/backend-e2e-export-overview.md/.json`，支持跨端统一判读诊断与门禁状态
- 阶段 5 协同（2026-05-09 策略解析收口）：后端同步改为调用 `ci_resolve_diag_strict_level.sh` 并接入解析 fixture 测试，前后端门禁策略解析逻辑保持一致
- 阶段 5 协同（2026-05-09 fixture 入口收口）：后端同步改为 `Validate e2e tooling fixtures (backend scope)` 并由 `test_ci_e2e_tooling.sh` 聚合执行 common + backend 相关测试，前后端 workflow fixture 校验入口一致
- 阶段 5 协同（2026-05-08 补充）：后端 `backend-e2e` export summary 已新增 `Threshold alerts` 阈值告警行；当导出检查计数偏离预期时，CI Summary 会直接给出异常计数项明细，便于前端联调快速判断是否为导出协议/权限语义回归

## 当前已有内容

- 三栏布局：会话、消息、轨迹/上下文
- Auth Gate：登录/注册、登录态校验、401 优先 refresh token 轮换并重试；刷新失败后自动回登录；退出入口融合到侧栏左下角设置区
- 登录后默认策略：直接进入 Workbench；运行模式由设置决定，`remote` 配置不完整会被前端阻断并提示
- 审计入口迁移到左下角设置菜单（独立子页）：查看 `login/logout/refresh/settings_update/settings_validate/task_create/task_cancel/task_timeout/task_failed/rag_ingest/rag_kb_clear/rag_kb_delete` 事件，支持事件类型/时间范围/`session_id`/`task_id` 筛选、详情展开与 JSON/CSV 导出（可选“当前页/全部筛选结果”）
- 设置菜单新增“知识库治理”子页：查看当前账号知识库列表、来源采样与文档条数，并支持行级清空/删除
- 设置菜单新增“用量统计”子页：查看 token/成本汇总、趋势、会话榜与任务榜（可切换全局或当前会话）
- 知识库治理页优化：列表表头统一左对齐并补“操作”列、刷新改为图标按钮、清空/删除统一为同类按钮样式；来源标签支持悬浮查看完整值，并新增采样含义说明
- 知识库治理信息增强：新增“样本片段”列，支持悬浮查看完整片段，减少“只看到来源名看不到真实内容”的信息盲区
- 审计页交互收口：改为分页表格主视图；筛选改为双行下拉+输入检索并统一控件尺寸（支持一键重置）；事件类型标签化；总数下置表格左下角、操作区右对齐；会话/任务恢复 ID 展示，并恢复行展开查看明细（无二次展开，分页默认每页 10 条）
- 弹窗状态收口：审计日志弹窗与模型设置弹窗在每次打开时重置筛选/分页/提示与临时输入状态
- 模型设置弹窗：打开时按后端配置回显当前 `mode/provider/model/base_url`，并通过 `autocomplete` 策略禁用浏览器自动填充
- 模型设置弹窗回显修复：解决打开弹窗时默认值覆盖后端配置导致显示 `mock` 的问题
- 模型设置弹窗优化：下方元信息表新增 `base_url` 行；`remote` 模式显示“仅支持 OpenAI-compatible 接口”提示
- 模型设置弹窗模式联动：切换 `mock/remote` 时，表单字段与下方元信息同步切换；`mock` 仅保留固定 `provider/model`，隐藏 `base_url/api_key`
- 模型设置反馈收口：保存/校验成功失败统一使用 message 浮层提示（不再在弹窗顶部堆叠可关闭提示）
- 模型设置密钥语义调整：`remote` 下 `api_key` 留空将沿用已存密钥；仅在首次 remote 配置时必填
- 模型设置表单校验补齐：`remote` 下 `provider/model/base_url` 必填；`api_key` 在无历史密钥时必填
- 模型设置校验反馈优化：当远端返回 `401/403` 时，后端会返回明确鉴权错误（`remote_api_key_unauthorized`），避免展示为网络连通错误
- 模型设置错误提示补充：`validate` 失败时会优先按 `error_code` 映射友好文案，并附带错误码（如 `remote_preflight_network_error`）便于联调
- 模型设置提示修复：改用 `App.useApp().message` 显示保存/校验结果，避免 Ant Design 静态 message 主题上下文告警
- 模型设置展示优化：元信息区 `base_url/database` 改为普通文本展示；切换到 `mock` 时清空当前编辑态并在保存后清空远端凭证
- 模型设置回显修复：若后端当前已保存为 `remote`，切换回 `remote` 时会回显已保存 `provider/model/base_url`
- 聊天消息显示修复：发送后立即显示用户临时消息；assistant 流式消息仅在生成中/失败态显示，避免与落库历史消息重复
- 会话鉴权：登录返回 `access_token + refresh_token + session_id`；退出时调用后端 `/api/auth/logout` 撤销当前会话 refresh token
- 协同进展（2026-05-09）：后端 `auth` 用户摘要已补 `role`（`admin/user`）并新增 admin-only `GET /api/auth/users`，为后续前端角色化入口治理提供契约基础
- 协同进展（2026-05-09）：后端 RAG 已接入 `shared-*` 共享知识库权限语义（admin 可写共享库，普通用户只读），前端后续可按 `role` 补治理入口显隐
- 阶段 5 收口（2026-05-09）：知识库治理弹窗已接入 `currentUser.role`；当知识库 ID 命中 `shared-*` 且当前用户非 admin 时，清空/删除按钮禁用并显示权限提示，避免无效写操作
- 阶段 5 回归补齐（2026-05-09）：Playwright 新增“非 admin 用户在 `shared-*` 知识库行上 clear/delete 按钮禁用”用例，确保前端权限态与后端 `403` 语义一致
- 阶段 5 回归补齐（2026-05-09 补充）：`workbench-main-path` 主链路已补 `shared-*` 权限断言（非 admin 共享库按钮禁用 + 私有库按钮可用），避免权限语义仅在单独治理 spec 覆盖
- 账号切换防串：退出/401/重新登录时会清空 React Query 与流式轨迹状态，避免跨账号显示残留
- 侧栏账户展示收口：用户信息已融合到左下角“设置”弹窗顶部，并采用与“主题/主题色/语言”同款行样式（图标 + 标题 + 值）展示，便于确认当前登录身份
- running task 恢复：持久化当前会话 ID，刷新后自动回到上次会话；若该会话存在 `pending/running` 任务，会自动复用 `/api/tasks/{task_id}/stream` 重连流继续展示，并在聊天区显示恢复状态提示条
- 会话隔离增强：`sseTask/sseTrace/ssePhase/sseUsage` 在 UI 展示层按当前会话过滤；跨会话后台流不会污染当前会话面板
- 恢复链路增强：同任务不重复触发自动恢复；`/stream` 返回 409（已非 pending/running）时按无害收敛处理，不再触发失败提示
- 流式滚动增强：自动跟随输出仅在“当前已贴底”时生效；离底阅读状态下保留当前位置，可通过“回到底部”按钮恢复跟随
- 待发送消息增强：pending user 仅对同 `task_id` 做去重，连续同文案发送可正确展示多条用户消息
- 当前任务增强：当 `tasks` 查询尚未刷新到新任务时，Inspector 使用流式任务兜底，取消按钮可即时点击
- 流式中断增强：新增 `cancelActiveStreamLocal`，取消成功后立即中断活动流读取，避免输入区长时间停留在“正在生成”
- 回底交互增强：滚动按钮移出消息滚动内容并锚定右下角，离底时固定可见，并通过徽标提示累计未读增量（最多 99+）
- 发送冷却增强：`remote` 模式取消成功后进入短暂冷却期，输入区提示“稍后发送”，冷却结束自动恢复发送
- 回底位置微调：按钮定位参数更新为更靠右、更靠上，避让聊天底部高频交互区
- 会话命名体验：空会话在首条消息发送后会自动改名为消息前缀（后端规则驱动）
- 会话：创建、切换、分页加载、重命名、删除
- 轨迹：时间线与流程图双视图（thought/action/observation/tool/rag 区分）
- 流式：SSE 任务状态、token 追加、trace 实时更新
- 回放：`trace` 全量与 `trace/delta` 增量加载（支持流式进行中的 `seq` 递增刷新 + 自动静默轮询 + 失败退避重试）
- `trace/delta` 请求会携带 `limit`（当前 200）控制单次增量拉取规模
- 若接口返回 `has_more=true`，前端会短间隔连续拉取以快速追平积压步骤
- 调度：页面在后台时暂停自动 delta 同步，前台自动恢复
- 观测：Context 摘要展示 delta 自动同步状态、重试次数、最近成功时间、下次重试时间、最近错误与恢复提示（恢复提示短时展示后自动消退）；重试中显示秒级倒计时
- 告警：delta 连续失败时显示轻提示并持续自动重试
- 右侧 Inspector（Context）信息架构已优化为运行态分区：概览 KPI、同步诊断、当前任务与最近任务；用于专注运行态观测与排障
- `full-trace-session` 首步收口：新增任务详情独立页 `/tasks/[taskId]`，复用现有视觉体系展示任务快照、Trace 时间线/流程图回放、任务导出
- `full-trace-session` 重排收口：中间主区域恢复为聊天主视图；任务索引能力（筛选/排序/搜索/失败置顶/分页）迁移到右侧任务中心抽屉；右侧 Inspector 保留运行态观察
- `full-trace-session` 清理收口：Inspector 中已移除旧任务块代码（任务用量/任务快照/任务索引），不再通过样式隐藏保留；任务分析统一走“任务中心 + 任务详情页”
- `full-trace-session` 回归对齐：Playwright 主链路与边界用例已迁移至新入口（`chat-open-task-center` / `task-center-open-task-detail` popup / `task-detail-export-*`），不再依赖已删除的 Inspector 任务导出控件
- `trace-export-json-md` 首版已落地：任务导出入口统一在任务详情页（JSON / Markdown），可一键导出当前任务（task-linked 消息、TraceStep、RAG chunks、usage、元信息）
- `session-export-lite` 首版已落地：会话导出入口迁移到左侧会话行“...”菜单（方案 1，按会话行触发），支持导出当前会话 JSON / Markdown（消息、任务摘要、Trace 预览、RAG 命中统计、会话级 usage）
- 任务索引增强：支持状态筛选（全部/运行中/已完成/失败）、时间排序（最新/最早）与失败置顶
- 任务索引增强：支持按任务标题/ID 搜索，并在失败任务上展示失败摘要提示
- Trace 面板增强：支持步骤类型筛选（全部/思考/行动/观察/工具/RAG/其他）、关键词检索、类型计数统计，且在时间线与流程图视图一致生效
- 右侧面板（Inspector）完成一体化优化：Trace 支持舒适/紧凑密度切换；Context 支持分区快速跳转（概览/同步）；任务状态使用语义徽标统一展示
- 左侧/中栏优化：侧栏会话区强化激活层级；聊天头部改为统一 runtime strip；消息流与输入区补充克制动效并统一节奏
- 交互收敛：已移除会话状态胶囊与输入计数提示，模式/提供方/模型恢复为头部紧凑标签展示，减少纵向占用
- 后端任务接口已提供 `status_normalized/status_label/status_rank`，前端可继续按需切换到后端统一状态语义
- W3 增量：`tool_end` 与 `trace.meta.tool` 已接入 `retry_count/error`，Trace 元信息可展示工具重试次数与错误摘要（配合 `[mock-tool-error]` / `[mock-tool-fatal]` 触发）
- W3 优化：新增计算器工具链路展示（`[calc:1+2*3]` 或“计算 1+2*3”），沿用现有工具状态可视化
- W1 优化：模型设置弹窗新增“校验配置”按钮，先调用 `POST /api/settings/validate` 再决定是否保存
- W2 稳定性优化：SSE + `trace/delta` 合并后的步骤按 `seq` 稳定排序，降低轨迹偶发乱序
- W2 稳定性优化：`trace/delta` 增加任务隔离保护，切换任务时旧请求晚到不会串写当前轨迹
- W2 稳定性优化：SSE 事件增加 `task_id` 活动任务隔离，避免并发/延迟事件污染当前任务
- W2 收敛优化：SSE phase 统一归一（`completed→done`、`failed→error`），并集中流式文案常量，减少状态分支判断
- W2 稳态优化：有活动任务时，缺失 `task_id` 的非 `start` 事件会被忽略，进一步降低串台风险
- W2 性能优化：`trace` 事件处理移除重复 `upsert` 计算，降低高频流式更新开销
- W2 展示优化：phase 映射补齐 `thinking/tool_running/tool_retry`，统一运行态展示
- W1/W2 国际化优化：`chat-stream-store` 流式提示改为 i18n 文案（`stream` 分组），支持中英文动态切换并消除硬编码英文
- W2 稳态优化：`trace/delta` 更新 `traceCursor` 时强制单调递增，避免并发增量请求导致游标回退
- W2 性能优化：`token` 事件改为单次 store 写入（文本 + trace 同步更新），减少高频渲染抖动
- W1/W2 国际化收口：流式“空闲提示”纳入 i18n，语言切换时空闲提示可即时刷新
- W1/W2 国际化维护优化：store 默认流式文案直接复用 `en.stream`，避免与 i18n 文案表双份维护
- W3 稳定性优化：仅在 `error.fatal=true` 时将流状态置为 `error`，可重试工具错误不再误触发全局失败态
- W4+ 稳定性优化：流式 `error` 事件已读取 `code/detail/status_code`，优先展示按错误码映射后的本地化提示，并在消息中附带错误码
- W2 协同优化：后端 `running` 重连流的 `done/error` 事件已补齐关键字段（`session_id/step_id/resumed`），前端消费契约更稳定
- usage 展示：支持当前任务、任务列表摘要；汇总由后端 `GET /api/tasks/usage/summary` 驱动（全局/会话自动切换），并具备 loading/error/empty 状态与统计覆盖率展示
- Memory/RAG 调试：迁移到设置弹窗“运行调试”子页（状态展示 + add/query + ingest/query）
- RAG 治理（设置弹窗）：知识库列表、来源采样、清空/删除（`/api/rag/knowledge-bases*`）
- RAG 交互优化：知识库 ID 采用“输入后应用”模式，避免输入期间频繁触发状态请求
- Trace 元信息：支持展示步骤级 `cost_estimate`
- 设置：主题、主题色、语言、模型与运行模式
- 工程校验：已配置 `.eslintrc.json`，`npm run lint` 可直接运行且当前告警已清零
- 鉴权联动：除 `/health` 与 `/api/auth/*` 外，其余请求统一自动注入 Bearer token

## 关键实现位置

- `app/components/workbench/index.tsx`：工作台主编排
- `app/components/workbench/inspector.tsx`：轨迹与上下文面板
- `app/tasks/[taskId]/page.tsx`：任务详情页与任务导出入口（JSON/Markdown）
- `app/components/workbench/sidebar.tsx`：会话导出入口（左侧会话行“...”菜单，Session JSON/Markdown）
- `app/components/workbench/trace-flow-view.tsx`：轨迹流程图节点渲染
- `app/components/workbench/chat-column.tsx`：消息历史、用户临时消息与流式 assistant 展示
- `app/components/workbench/sidebar.tsx`：会话列表、折叠侧栏与设置入口
- `app/components/workbench/sidebar-settings-menu.tsx`：主题/主题色/语言、当前登录用户、模型设置、审计、用量统计与知识库治理入口
- `app/components/workbench/usage-dashboard-modal.tsx`：用量仪表盘（趋势、会话榜、任务榜）
- `app/components/workbench/model-settings-modal.tsx`：mock/remote 模型设置、校验与保存
- `app/components/workbench/audit-logs-modal.tsx`：审计日志筛选、分页、展开与导出
- `app/components/workbench/knowledge-base-governance-modal.tsx`：知识库列表、来源采样与清空/删除治理
- `app/components/workbench/runtime-debug-modal.tsx`：Memory/RAG 调试子页（设置弹窗入口）
- `e2e/helpers/workbench.ts`：Playwright 公共 helper（注册、登录态注入、Workbench 就绪兜底）
- `lib/stores/chat-stream-store.ts`：SSE 事件分发与 trace 状态
- `lib/types/trace.ts`：前端 TraceStep 类型
- `lib/api-client.ts`：REST 请求封装、Bearer 注入、refresh token 自动续期与 401 失效广播
- `lib/preferences-context.tsx` / `lib/i18n/*`：主题、主题色、语言与中英文文案
- `app/components/auth/auth-gate.tsx`：登录/注册页与鉴权网关

## SSE 消费与契约对齐

当前前端按以下事件消费：
- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `done`
- `error`

`trace` 事件中的 `step` 与后端 REST `TraceStep` 同构，`dispatchSseEvent`（`lib/stores/chat-stream-store.ts`）为当前权威消费路径。
`tool_start/tool_end` 会先行驱动 action 节点状态，再由 `trace` 事件补齐持久化快照。
流式任务期间，Workbench 会定时静默拉取 `trace/delta`，失败时按退避策略重试，并在流结束后自动补拉一次，降低 SSE 与持久化快照的短暂偏差。
同步健康度会在 Inspector Context 区域实时展示，便于定位网络抖动或增量拉取异常。
当连续失败达到阈值时会显示非阻塞告警文案，不影响主任务流。
重试中的最近错误信息会直接显示在摘要区，便于快速定位失败原因。

## Memory（会话级）

- collection 规则：`memory_{session_id}`
- 状态读取：`GET /api/sessions/{session_id}/memory/status`
- 写入调试：`POST /api/sessions/{session_id}/memory/add`
- 检索调试：`POST /api/sessions/{session_id}/memory/query`

## RAG（知识库）

- 状态：`GET /api/rag/status?knowledge_base_id=...`
- 写入：`POST /api/rag/ingest`
- 检索：`POST /api/rag/query`
- 默认知识库 ID：`default`
- 实际 collection：`kb_{user_hash}_{knowledge_base_id}`；默认知识库在当前用户下对应 `kb_{user_hash}_default`

## PostgreSQL / Memory / RAG 怎么看（前端通俗版）

- 聊天记录来源（左侧会话 + 中栏消息 + 任务历史）：
  - 来自后端 `PostgreSQL` 的会话/消息/任务数据。
- Memory 面板（会话级）：
  - 面向当前 `session_id` 的语义记忆（`memory_{session_id}`）。
  - 适合查看“本次对话中需要记住的约束和结论”是否被写入/检索到。
- RAG 面板（知识库级）：
  - 面向 `knowledge_base_id` 的知识库（后端落库为 `kb_{user_hash}_{knowledge_base_id}`）。
  - 适合管理手册、FAQ、文档片段的 ingest 与检索命中。

可用一句话理解：

- `PostgreSQL` 管完整历史；
- `Memory` 管会话便签；
- `RAG` 管外部知识库。

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

说明：`npm run dev` / `npm run start` 已固定监听 `127.0.0.1:3001`，与 Playwright `webServer` 探测地址对齐，减少本地与 CI 的端口探测抖动。

默认通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端（未设置时使用 `http://127.0.0.1:8000`）。

前端 e2e 命令约定：

```bash
# 默认快速回归（chromium 全量）
npm run test:e2e

# smoke 跨浏览器矩阵（chromium/firefox/webkit）
npm run test:e2e:smoke:matrix
```

如需一键拉起依赖并启动前后端（推荐），可在仓库根目录执行：

```bash
./start_insightagent.command
```

脚本会先确保 `postgres/chroma` 就绪，再启动 backend/frontend，适合本地联调直接使用。
其中 Chroma 就绪检查已切换为 `v2` heartbeat，兼容新版镜像；并会在启动前清理旧 `next dev` 进程且等待前端可访问。

## 后续阶段决策（前端与部署视角）

### 优先做

1. `full-trace-session-lite`：任务详情抽屉/页面（任务快照 + 回放）已接入；相关 Playwright 与主链路 e2e 当前轮收口已完成，后续按开发主线补更深的回放体验。
2. `trace-export-json-md`：单任务 JSON/Markdown 导出入口与 Playwright 回归已接入；空数据/404/权限语义断言与前端导出错误提示一致性已补齐，当前轮 e2e 收口已完成。
3. `session-export-lite`：当前会话 JSON/Markdown 导出入口与 Playwright 回归已接入；空会话/404/跨用户隔离语义断言已补齐，当前轮 e2e 收口已完成。
4. `remote-provider-hardening`：真实模型错误提示、重试建议与设置入口联动。
5. `e2e-main-path`：后端主链路 e2e 脚本已落地；前端 Playwright 已覆盖主链路（登录态注入 + Workbench 兜底、任务流、Trace、RAG、导出），当前轮 e2e 收口已完成。
6. `task-cancel-timeout`：首版已落地（取消按钮 + 状态提示）；后端 e2e/CI 已补齐，前端 Playwright 已补刷新恢复 + 取消后重发闭环，当前仅需随功能变更做小步回归。
7. `running-task-recovery`：前端首版与恢复状态提示已落地（刷新/切回会话自动恢复 running 任务流）；当前 e2e 收口已覆盖恢复主闭环，后续按主线需要再加细粒度可观测指标。
8. `usage-dashboard-lite`：用户/会话/任务维度成本统计增强。

### 暂不做

1. 大规模 UI 重构或炫技动效重写（当前可用性已满足演示）。
2. 过早做复杂多模型编排面板（先把稳定性与治理打牢）。
3. PDF/视频/GIF 自动导出（先用 JSON/Markdown 导出服务回放与演示）。

### 部署建议

1. 前端优先部署到 Vercel 免费版。
2. 后端/FastAPI 与数据服务独立部署，不与前端运行环境绑定。

## 下一步（W4+）

- 历史任务详情/Trace 回放已进入开发：任务快照、单任务导出、会话导出已完成。
- 下一步聚焦异常态覆盖深化与更细节的视觉一致性回归（当前本地已验证 Chromium 全量 30/30 与 smoke 跨浏览器矩阵 15/15）。
- `rag-kb-governance-lite`、`usage-dashboard-lite`、`audit-event-expansion` 与 `provider-usage-alignment` 首版已完成。

## 最新同步（2026-04-23）

- 任务中心表格头部汇总计数文案已移除（含分页 `showTotal`），避免出现 `17 / 17` 展示。
- 任务中心“失败置顶”筛选已移除，保留状态筛选 + 时间排序（最新/最早）作为统一行为。
- 表格与筛选区样式优化：筛选控件高度统一、重置按钮改为轻量文本动作、表头层级强化、操作按钮可见性提升并与整体风格对齐。
- 视觉补充修正：任务中心表格去除偏蓝底色并恢复中性底色；重置筛选按钮改为审计日志同款默认按钮样式。

## 最新同步（2026-05-20）

- 本轮 `tool-runtime-productionization` 继续集中在后端 runtime 内部 typed 收口；前端外部 SSE / trace / e2e 契约未变，Workbench 与任务详情页无需额外协议适配。
- provider preflight 现已去掉一层内部 `dict` 往返，兼容行为继续保持稳定；当前前端仍可按既有任务/trace 展示链路工作。

## 最新同步（2026-05-25）

- 本轮 `tool-runtime-productionization` 继续集中在后端 `preflight` 的 total-model 收口，新增 `build_configured_tool_registry_provider_preflight_models_from_dict()` 与 `...from_service_execution_model()`；前端外部 SSE / trace / e2e 契约仍未变化。
- provider preflight 的 `service_execution / execution_result / summary / result` typed hydration 现在已经在后端单点汇总，前端仍可沿用既有任务、trace、summary 展示链路；focused 回归脚本已扩展到 `244` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端又把 `service_execution/execution_result -> summary/result` 的 typed 总装进一步抽成 `build_configured_tool_registry_provider_preflight_models_from_models()`，并让 dict pair helper 继续退回兼容壳；前端外部 SSE / trace / e2e 契约依旧不变。
- 当前前端无需任何协议调整；focused 回归脚本已扩展到 `246` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 dict 侧的 `payload -> total models` 也收成 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()`，同时把 typed pair helper 再往外退成 total-model 兼容壳；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；focused 回归脚本已扩展到 `247` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。

## 最新同步（2026-06-01）

- 本轮 `tool-runtime-productionization` 继续集中在后端 `service_execution / preflight` 内部 wrapper 收薄：`service_execution` 的 build/execute `outputs` 壳已统一退回最近邻 typed `result_model` seam，相邻 `preflight_service_execution_result` typed 壳也同步挂回通用 `service_execution_result` 主链。
- 前端外部 SSE / trace / e2e 契约仍未变化，Workbench 与任务详情页无需任何协议适配；focused 回归脚本维持 `303` 条兼容测试，`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py` 与 `bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 同轮续推又把 dict 侧 `preflight_result -> service_execution/execution_result pair` 入口再收薄一层：`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在直接复用 `...preflight_service_execution_model_from_dict()` 与 `...preflight_service_execution_result_model_from_dict()`。
- 前端外部 SSE / trace / e2e 契约依旧不变，当前仍无需任何协议调整；focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端又把 payload 侧 pair helper 也退成了 total-model 兼容壳，`payload -> total models` 现在已经成为 dict inward 的主单点；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；focused 回归脚本已扩展到 `249` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 typed 侧 `service_execution_model -> execution_result_model` 的 preflight wrapper 也退成 total-model 兼容壳，typed inward 的主单点进一步集中到 `preflight_models_from_service_execution_model()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；focused 回归脚本维持 `249` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `summary` 的 typed seam 也退成 total-model 兼容壳，并让 `result.summary` 成为 summary 复用单点；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；focused 回归脚本已扩展到 `251` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把高层 raw-input / execute 入口也退成 total-model 兼容壳，`build_preflight_result_model()` 与 `execute_preflight_model()` 现在都只负责从统一 helper 取 `result_model`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；focused 回归脚本已扩展到 `253` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把最外层 outward dict seam 也收成单点：新增 `build_configured_tool_registry_provider_preflight_dicts_from_models()`、`build_configured_tool_registry_provider_preflight_dicts()` 与 `execute_configured_tool_registry_provider_preflight_dicts()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_summary()`、`build_preflight_result()`、`execute_preflight()` 现在都只会从共享 dict helper 取 summary/result，focused 回归脚本已扩展到 `256` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把高层 outward `models + dicts` 也统一到 total-output seam：新增 `build_configured_tool_registry_provider_preflight_outputs_from_models()`、`build_configured_tool_registry_provider_preflight_outputs()` 与 `execute_configured_tool_registry_provider_preflight_outputs()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_models()`、`build_preflight_result_model()`、`build_preflight_result()`、`execute_preflight_models()`、`execute_preflight_model()` 与 `execute_preflight()` 现在都只会从共享 `outputs` helper 取对应结果，focused 回归脚本已扩展到 `257` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把单参 `preflight_result` 的 dict 兼容链也统一到 total-output seam：新增 `build_configured_tool_registry_provider_preflight_outputs_from_dict()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`preflight_summary()`、`preflight_dicts()` 和几条 `...from_dict()` typed 兼容入口现在都只会从共享 `outputs_from_dict()` 取对应结果，focused 回归脚本维持 `257` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution_payload + preflight_result` 这条 payload typed 链也统一到 total-output seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`preflight_execution_models_from_service_execution_payload()` 与 `preflight_models_from_service_execution_payload()` 现在都只会从共享 `outputs` helper 取对应 typed 结果，focused 回归脚本维持 `257` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution_payload + execution_result` 这条 payload total-output seam 本身也明确收成单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_outputs()` 现在也只是这层 payload helper 的兼容壳，focused 回归脚本已扩展到 `258` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 typed `service_execution_model + preflight_result` 这条链也统一到 total-output seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`...from_service_execution_model()` 这几条 typed 兼容入口现在都只会从共享 `outputs_from_service_execution_model()` 取对应结果，focused 回归脚本已扩展到 `259` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把单参 dict total-output 总出口也并回更高层 `build_configured_tool_registry_provider_preflight_outputs()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_configured_tool_registry_provider_preflight_outputs_from_dict()` 现在只会从共享 `build_configured_tool_registry_provider_preflight_outputs(service_execution, execution_result)` 取总装结果，focused 回归脚本已扩展到 `261` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution_payload + execution_result` 这条 total-output 入口也并回更高层 `build_configured_tool_registry_provider_preflight_outputs()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；高层 `build_configured_tool_registry_provider_preflight_outputs()` 现在自己承担 `service_execution` hydration，而 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 退回为兼容壳，focused 回归脚本已扩展到 `263` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute 侧也补成对称的 typed total-output seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`execute_configured_tool_registry_provider_preflight_outputs()` 现在只负责构造 `service_execution_model`，其余总装都交给新的 typed execute helper，focused 回归脚本已扩展到 `265` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把最外层 summary/result wrapper 这批 outward 入口退回到最近邻 helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；summary/result outward 入口现在更多只是从现成 `dicts()/models()` helper 取结果，不再平行依赖更深的 `outputs()` seam，focused 回归脚本维持 `265` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution/execution_models` 这组 wrapper 也退回到最近邻 helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`service_execution/execution_models` outward 入口现在更多只是从现成 `execution_models()/models()` helper 取结果，不再平行依赖更深的 `outputs()` seam，而 `models` 这一层本身也已直接走 `models_from_models()` 主链，focused 回归脚本已扩展到 `267` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `dicts` 这一层 outward wrapper 也退回到最近邻 `models()` helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_dicts_from_models()` / `build_preflight_dicts()` / `execute_preflight_dicts()` 现在都只是在现成 `models()` 主链之上做字典投影，不再平行依赖更深的 `outputs()` seam，focused 回归脚本已扩展到 `270` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `outputs` 这一组 build/execute wrapper 也退回到 `models + dict projection` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；build/execute 两侧的 `outputs` 入口现在都只是从现成 `models()` 主链取 typed 结果，再统一做 dict 投影，不再保留平行的总装路径，focused 回归脚本已扩展到 `272` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution` 内核层的两处 model/dict 往返拿掉；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`service_execution` 现在在 build/execute 两侧都更多停留在 typed model 内部流转，不再额外做 `runtime_artifacts.to_dict()` 或 `[action.to_dict()]` 这种中转，focused 回归脚本已扩展到 `274` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把相邻的 `service_execution result + dict` 这一层也补成 `outputs` 单点；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`service_execution` 现在在 build/execute 两侧都可以先统一走 `outputs` seam，再取 typed result 或 dict，不再保留平行的 result+dict 组装路径，focused 回归脚本已扩展到 `277` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `runtime_service_actions` build/execute wrapper 也补成 `outputs` 单点；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`runtime_service_actions` 现在在 build/execute 两侧都可以先统一走 `outputs` seam，再取 typed actions/result 或 dict，而 `service_execution` build/execute 也同步退回到这层最近邻 helper，focused 回归脚本已扩展到 `284` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `runtime_service_actions` 的 typed-from-artifacts 和 dict-from-dicts 两条入口也并回到最近邻 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`runtime_service_actions` 现在不仅 build/execute 两侧统一走 `outputs` seam，连 typed-from-artifacts、dict-from-dicts 和 `service_execution_model_from_dict()` 这几条兼容入口也都回到同一条最近邻 helper，focused 回归脚本已扩展到 `288` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `runtime_service_actions result` 也补成了对称 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`runtime_service_actions result` 的 dict→typed 投影现在也走单点 `outputs` seam，`service_execution` build-side result 组装同步退回到这层最近邻 helper，focused 回归脚本已扩展到 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight` 这边两条 build-side `service_execution_result` wrapper 也并回了 `service_execution outputs` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`preflight` build-side 的 `service_execution_result` 兼容入口现在也复用同一条 `service_execution outputs` 主链，不再单独绕一层 `preflight_execution_models`，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `preflight models / execution_models` 三条入口一起并回 `service_execution outputs` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`dict` / `payload` / typed `service_execution_model` 三条 `preflight` build-side 入口现在都统一走“`service_execution_model` 归一化 + `service_execution outputs` + `preflight_models_from_models()`”这条总装路径，但前端消费到的 `preflight summary/result` dict outward 形状、SSE 事件载荷和 trace/e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把最外层 raw `service_execution + execution_result` 的 build wrapper 也退回到了 payload seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_models()/outputs()/result_model()` 只是进一步退回为更薄的兼容壳，前端消费到的 `preflight summary/result` outward 形状、SSE 事件与 trace/e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build/execute 的 dict outward wrapper 也统一退回 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_dicts()/result()` 和 `execute_preflight_dicts()/execute_preflight()` 只是进一步改成直接从 `outputs` seam 取 dict 结果，前端看到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把剩余的 preflight model outward wrapper 也统一退回 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_summary_model_*()`、`build_preflight_result_model_*()` 和 `execute_preflight_model()` 只是进一步改成直接从 `outputs` seam 取 typed model，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight outputs` 这组 wrapper 本身也往最近邻 seam 收了一层；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_outputs*()` 和 `execute_preflight_outputs*()` 只是进一步改成在更高层统一先落到 typed `service_execution_model` / `outputs_from_models()` 主链，再取 outward dict，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight ...from_models()` 这组 outward wrapper 也并回 `outputs_from_models` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_dicts_from_models()`、`build_preflight_summary_model_from_models()`、`build_preflight_result_model_from_models()` 与 `build_preflight_result_model()` 只是进一步改成从 `outputs_from_models` / `outputs_from_service_execution_payload` 直接取 outward dict 或 typed result，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight models_from_dict / ...payload / ...service_execution_model` 三条 typed 总装入口也统一并回 `preflight_execution_models_*` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把后端内部的 typed 总装边界进一步压到更少 helper 上，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 dict/typed `service_execution_model/result_model` wrapper 也统一并回 `preflight_execution_models_*` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次仍然只是进一步压缩后端内部的 seam 数量，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight_execution_models_from_service_execution_payload()` 也退回到 typed helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 payload 层也统一先落到 typed `service_execution_model` 再派生 `execution_result_model`，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 typed `preflight_execution_models_from_service_execution_model()` 也退回到通用 `service_execution_result_model` helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是进一步压缩 typed path 内部的 seam 数量，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight` 剩余的 dict/payload/typed wrapper 成片并回 `outputs_from_*` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；`build_preflight_service_execution_model/result_model/execution_models/models` 这几组 wrapper 只是进一步改成从最近邻 `outputs_from_dict()` / `...outputs_from_service_execution_payload()` / `...outputs_from_service_execution_model()` 取 typed 结果，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `292` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 的 `preflight models` 平行总装链也并回 `execute_preflight_outputs*` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 execute 侧 `models` 入口也直接从最近邻 `execute outputs` seam 取 typed 结果，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本已扩展到 `294` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution` execute 侧也补成了和 build 侧对称的共享总装 seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 execute 侧 `service_execution` 也统一通过共享的 typed result+dict 总装 helper 出口，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本已扩展到 `296` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 的 `preflight outputs_from_service_execution_model()` 也并回 `service_execution outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 execute-side preflight 总装链也优先通过最近邻 `service_execution outputs` seam 取 typed 执行结果，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `296` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把三条还直接切 `outputs()[0]` 的 `runtime_service_actions / service_execution` wrapper 一起退回到最近邻 `*_model_*` helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是继续压缩后端内部 helper 之间的委托层次，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本已扩展到 `297` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把一条 raw build 链和两条 `service_execution` result 链一起退回到最近邻 typed model helper；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是继续压缩后端内部 result/helper 的委托层次，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本已扩展到 `299` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `*_result_model` 这组 wrapper 成片退回到 typed result seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是继续压缩后端内部 result-model helper 之间的委托层次，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `299` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 raw dict `outputs` wrapper 这一批也并回到最近邻 `result_model` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是继续压缩后端内部 raw wrapper 与 result-model helper 之间的委托层次，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本已扩展到 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight` 最外层 raw wrapper 也并回到 `summary/result model` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是继续压缩后端最外层 preflight outward helper 的委托层次，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `preflight` 剩下的 typed `summary/result model` wrapper 成片并回到 `result_model/models` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 `summary_model_from_*` 与 `result_model_from_*` 这批内部 helper 从 `outputs` seam 收回到更直接的 typed `result_model/models` 边界，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 的 `preflight models/model` wrapper 成片并回到 `service_execution outputs + models_from_models` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 execute 侧内部 typed 总装边界从 `outputs` 反拆改成“先统一拿 typed `execution_result_model`，再组装 `summary/result`”，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `preflight service_execution_model/result_model/execution_models/models` wrapper 成片退回到更直接的 typed seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧内部 typed hydration 与 `execution_result_model` 派生边界进一步压回 `service_execution_result_model` 与 `preflight_models_from_models()` 主链，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `preflight summary/result/dicts` wrapper 成片退回到 `preflight_models_*` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `summary/result` outward wrapper 统一改成从 typed `preflight_models_*` helper 取值，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `preflight outputs*` wrapper 成片退回到 `preflight_models_*` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `outputs*` wrapper 统一改成先拿 typed `preflight models` 再做 dict 投影，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 的 `preflight outputs/dicts` wrapper 成片退回到 `execute_preflight_models*` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 execute 侧 `outputs/dicts` wrapper 统一改成先拿 typed `preflight models` 再做 dict 投影，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 的 `service_execution/preflight` typed wrapper 再拉直一层；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 execute 侧 typed `execution_result_model` 的内部拿取路径统一压回 `execute_service_execution_model()` 主链，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `302` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `runtime_service_actions` 的 raw build/execute wrapper 退回到更直接的 `model/result_model` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 `runtime_service_actions` 内部拿取 typed model / result 的路径统一压回最近邻 `model/result_model` 主链，并把两条 `outputs_from_*` outward wrapper 一起退回成 `to_dict()` 薄壳，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本现在是 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 的 `service_execution/preflight` 最近邻 helper 再拉直一层；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 typed `service_execution_result_model` 与 `preflight_result_model` 的内部拿取路径统一压回最近邻 result-model 主链，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side 两参 `preflight` raw wrapper 成片收回到单参 `preflight_result dict` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `preflight models/outputs/result` 这批 raw 入口统一改成“先合成 outward `preflight_result` payload，再复用 `...from_dict()` helper”，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build/execute 最外层 `preflight` dict outward wrapper 收回到 `dicts` / `outputs_from_dict` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `summary/result` dict outward 和 execute 侧 `result/dicts` outward 一起统一改成复用更近一层的 `dicts` / `outputs` helper，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution` 最外层 raw wrapper 收回到 `outputs_from_service_execution_model()` / `outputs()` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 `service_execution` build/execute 两侧的最外层 raw outward wrapper 统一改成复用更近一层的 typed `outputs` helper，前端消费到的 provider/runtime_artifacts/计数 outward 形状与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 `service_execution_result` 与 `preflight_service_execution_result` 这批 wrapper 收回到最近邻 `service_execution outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把内部 typed result 的拿取路径统一压回最近邻 `service_execution outputs` helper，前端消费到的 provider/runtime_artifacts/summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build/execute 最外层 `preflight` dict outward wrapper 收回到 `summary_model/result_model` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `summary/result/dicts` outward 与 execute 侧 `result/dicts` outward 统一改成直接复用最近邻 typed `summary/result model` helper，再做 `to_dict()` 投影，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 payload 侧 `preflight execution-model pair` 入口也收回到 dict seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 build-side `preflight` 的 payload inward 入口改成“先合成单参 `preflight_result`，再复用 dict pair helper”，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 build-side typed `preflight` 的 3 条 `...from_service_execution_model()` wrapper 成片收回到通用 `service_execution_result_model` 主链；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 build-side typed `preflight` inward 入口统一先拿 typed `service_execution_result_model`，再分别组装 `models/result/outputs`，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side `preflight` 的相邻 outward wrapper 成片收回到更直接的 typed seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 execute-side `preflight outputs*` 更早落到 typed `execution_result_model` 主链，再做最近邻 dict 投影，前端消费到的 summary/result outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端继续把 execute-side 顶层 `preflight` 的 `models/model/dicts` 三层 wrapper 也收回到统一的 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 execute-side 顶层 `preflight` 更统一地从同一条 total-output seam 取 typed 结果或 summary/result dict，前端消费到的 outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 前端 e2e workflow 修复（2026-05-28）：`.github/workflows/frontend-e2e.yml` 已为 Playwright 浏览器目录增加 `~/.cache/ms-playwright` 缓存，并把安装步骤从 `npx playwright install --with-deps chromium firefox webkit` 调整为更轻的 `npx playwright install chromium firefox webkit`；同时 job 超时从 `35` 分钟放宽到 `45` 分钟，减少冷启动浏览器安装把整条前端 e2e job 卡死的风险。对应 workflow guard 与 `common` fixture 已通过。
- 前端 e2e workflow 跟进修复（2026-05-28）：在缓存与超时放宽之后，前端 smoke matrix 仍提示 Playwright 缺系统依赖，因此 workflow 已进一步拆成“缓存浏览器目录 + `npx playwright install-deps chromium firefox webkit` + `npx playwright install chromium firefox webkit`”三段式安装。当前既能利用浏览器缓存，也能保证 `chromium/firefox/webkit` 三项目在 Ubuntu runner 上具备完整依赖；对应 workflow guard 与 `common` fixture 已再次通过。
- 本轮后端继续把 build-side `preflight` 的 `summary/result/dicts/models` wrapper 成片收回到统一的 `outputs` seam；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是把 build 侧 `summary/result` typed/dict outward wrapper 进一步统一成从最近邻 `preflight_outputs*()` helper 取值，前端消费到的 `summary/result` outward 形状、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
- 本轮后端还把 payload 侧两条 `preflight` inward wrapper 一起并回到了 `outputs_from_service_execution_payload()`；前端外部 SSE / trace / e2e 契约仍未变化。
- 当前前端仍无需任何协议调整；这次只是让 build-side payload inward 入口和 dict / typed 两侧共用同一条 total-output seam，前端消费到的 outward 协议、SSE 事件与现有 e2e 断言继续保持不变，focused 回归脚本维持 `303` 条兼容测试，`bash scripts/test_ci_e2e_tooling.sh common` 已再次通过。
