# Tool Runtime Productionization Handoff

## 背景

当前开发主线是后端 `tool-runtime-productionization`。

目标不是改外部行为，而是持续把 [backend/app/services/chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py) 中与 tool 执行相关的内部编排逻辑，逐步下沉到 [backend/app/services/tool_runtime.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/tool_runtime.py)，同时保持以下外部契约不变：

- SSE 事件形状不变
- trace 结构不变
- 错误语义不变
- backend baseline / frontend smoke / common tooling 回归不变

## 当前真实状态

### 1. 已完成的收口范围

`tool_runtime.py` 已经不仅承接 mock tool registry 与单 tool 执行，还继续上提了多层编排 helper，包含：

- registry / invocation / runtime context
- attempt start / success / error events
- attempt transition / retry decision
- iteration context / iteration execution
- plan-item result / execution result / postprocess
- success effects / terminal effects
- attempt execution
- attempt loop result
- attempt loop terminal result
- retry loop 最终消费结果

当前已经落地的较高层 helper 重点包括：

- `load_tool_registry()`
- `ToolRegistryProvider`
- `StaticToolRegistryProvider`
- `DefaultToolRegistryProvider`
- `ConfiguredToolRegistryProvider`
- `get_default_tool_registry_provider()`
- `get_configured_tool_registry_provider()`
- `build_profile_tool_registry_provider()`
- `build_profile_tool_registry_loader()`
- `resolve_named_tool_registry_loader()`
- `resolve_named_tool_registry_provider_reference()`
- `resolve_named_tool_registry_provider_factory()`
- `resolve_named_tool_registry_loader_factory()`
- `get_tool_registry_provider_source_name_from_settings()`
- `build_tool_registry_extra_tools_from_file()`
- `load_tool_registry_file_payload()`
- `build_tool_registry_from_file_artifacts()`
- `build_tool_registry_loader_from_file_artifacts()`
- `build_tool_registry_provider_from_file_artifacts()`
- `build_tool_registry_from_file()`
- `build_tool_registry_loader_from_file()`
- `build_tool_registry_provider_from_file()`
- `build_tool_registry_loaders_from_settings_artifacts()`
- `build_tool_registry_providers_from_settings_artifacts()`
- `build_tool_registry_provider_sources_from_settings_artifacts()`
- `get_configured_tool_registry_provider_artifacts()`
- `build_tool_registry_diagnostics_summary()`
- `build_tool_registry_diagnostics_runtime_artifacts()`
- `build_configured_tool_registry_provider_runtime_artifacts()`
- `build_tool_registry_diagnostics_audit_event()`
- `build_tool_registry_diagnostics_trace_service_action()`
- `build_tool_registry_diagnostics_audit_service_action()`
- `build_configured_tool_registry_provider_runtime_service_actions()`
- `execute_configured_tool_registry_provider_runtime_service_actions()`
- `build_configured_tool_registry_provider_service_execution()`
- `execute_configured_tool_registry_provider_service_execution()`
- `execute_configured_tool_registry_provider_preflight()`
- `build_configured_tool_registry_provider_preflight_result()`
- `build_configured_tool_registry_provider_preflight_summary()`
- `build_configured_tool_registry_provider_preflight_result_model()`
- `build_configured_tool_registry_provider_preflight_summary_model()`
- `build_tool_registry_diagnostics_summary_model()`
- `build_tool_registry_diagnostics_runtime_artifacts_model()`
- `build_tool_registry_diagnostics_trace_service_action_model()`
- `build_tool_registry_diagnostics_audit_service_action_model()`
- `build_configured_tool_registry_provider_runtime_artifacts_model()`
- `build_configured_tool_registry_provider_runtime_service_actions_model()`
- `build_configured_tool_registry_provider_runtime_service_actions_result_model()`
- `build_configured_tool_registry_provider_service_execution_model()`
- `build_configured_tool_registry_provider_service_execution_result_model()`
- `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()`
- `build_configured_tool_registry_provider_preflight_result_model_from_models()`
- `execute_configured_tool_registry_provider_preflight_model()`
- `build_configured_tool_registry_provider_service_execution_result_model_from_models()`
- `execute_configured_tool_registry_provider_service_execution_model()`
- `build_configured_tool_registry_provider_runtime_service_action_model_from_dict()`
- `build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts()`
- `execute_configured_tool_registry_provider_runtime_service_actions_model()`
- `build_configured_tool_registry_provider_runtime_artifacts_model_from_dict()`
- `build_configured_tool_registry_provider_service_execution_model_from_dict()`
- `build_configured_tool_registry_provider_preflight_result_model_from_dict()`
- `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`
- `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`
- `build_configured_tool_registry_provider_preflight_summary_model_from_models()`
- `build_configured_tool_registry_provider_preflight_summary_model_from_parts()`
- `build_tool_registry_loader_factories_from_settings()`
- `build_tool_registry_provider_factories_from_settings()`
- `build_tool_registry_loaders_from_settings()`
- `build_tool_registry_providers_from_settings()`
- `build_tool_registry_provider_sources_from_settings()`
- `get_tool_registry_profile_name_from_settings()`
- `build_tool_registry_profile_settings_config()`
- `build_tool_registry_extra_tools_from_settings()`
- `build_tool_registry_extra_tools_from_specs()`
- `build_tool_registry_loader_adapter()`
- `build_tool_registry_provider_adapter()`
- `build_tool_registry_settings_config()`
- `build_tool_registry_overrides_from_settings()`
- `get_disabled_tool_names_from_settings()`
- `build_tool_registry_provider()`
- `resolve_tool_registry_provider()`
- `get_default_tool_registry()`
- `build_tool_registry()`
- `get_registered_tool_names(..., registry=...)`
- `get_registered_tool_names(..., registry_provider=...)`
- `get_registered_tool_names(..., registry_loader=...)`
- `resolve_tool_registration(..., registry=...)`
- `resolve_tool_registration(..., registry_provider=...)`
- `ensure_tool_registration(..., registry=...)`
- `ensure_tool_registration(..., registry_provider=...)`
- `build_tool_runtime_context(..., registry=...)`
- `build_tool_runtime_context(..., registry_provider=...)`
- `run_tool(..., registry=...)`
- `run_tool(..., registry_provider=...)`
- `execute_tool_spec(..., registry=...)`
- `execute_tool_spec(..., registry_provider=...)`
- `run_tool(..., registry_loader=...)`
- `execute_tool_spec(..., registry_loader=...)`
- `build_tool_attempt_bundle()`
- `build_tool_attempt_execution()`
- `build_tool_attempt_loop_result()`
- `build_tool_attempt_loop_terminal_result()`
- `build_tool_plan_item_retry_loop_result()`
- `build_tool_plan_item_retry_loop_execution_result()`
- `build_tool_plan_item_execution()`
- `execute_tool_plan_item_retry_loop()`
- `execute_tool_plan_item_service_execution()`
- `execute_tool_plan_item_service_actions()`
- `build_tool_plan_item_stream_effects()`
- `build_tool_plan_item_continue_update()`
- `build_tool_plan_item_continue_action()`
- `build_tool_plan_item_next_action()`
- `build_tool_plan_item_terminal_return_effects()`
- `build_tool_plan_item_return_action()`
- `build_tool_plan_item_trace_write_action()`
- `build_tool_plan_item_next_action_execution()`
- `build_tool_plan_item_service_actions()`
- `build_tool_plan_item_trace_write_service_action()`
- `build_tool_plan_item_continue_service_action()`
- `build_tool_plan_item_return_service_actions()`
- `build_tool_plan_item_service_effects_execution()`
- `build_tool_plan_item_service_execution()`
- `build_tool_plan_item_service_effects()`
- `build_tool_plan_item_success_effects()`
- `build_tool_plan_item_terminal_effects()`

### 2. `chat_execution_service.py` 当前剩余职责

虽然已经明显变薄，但它还保留以下职责：

- `for tool_spec in tool_plan` 外层遍历
- SSE 发射时机
  - `tool_start`
  - `state`
  - `tool_end`
  - `error`
  - `trace`
- 调 runtime 侧 `execute_tool_plan_item_service_actions()`，只做最终 SSE 字符串包装与 return 边界

换句话说，当前“单个 tool retry loop 的执行控制”和大部分 success/terminal 字段搬运都已经下沉；`chat_execution_service.py` 里主要剩下 tool 级 SSE 发射、trace 持久化和任务完成/失败这类按序副作用执行。

### 3. 当前 focused regression 状态

[backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py) 当前已经扩展到 **235 条测试**，并全部通过。

已覆盖的关键契约包括：

- `load_tool_registry`
- `get_default_tool_registry`
- `build_tool_registry`
- `get_registered_tool_names(custom registry seam)`
- `get_registered_tool_names(custom registry_provider seam)`
- `load_tool_registry(custom loader seam)`
- `load_tool_registry(custom provider seam)`
- `load_tool_registry(default provider path seam)`
- `DefaultToolRegistryProvider(named default seam)`
- `ConfiguredToolRegistryProvider(composition seam)`
- `get_configured_tool_registry_provider(named configured seam)`
- `build_tool_registry_loaders_from_settings(named loader seam)`
- `build_tool_registry_providers_from_settings(named provider seam)`
- `resolve_named_tool_registry_provider_factory(provider factory seam)`
- `resolve_named_tool_registry_loader_factory(loader factory seam)`
- `build_tool_registry_extra_tools_from_file(file-backed registry seam)`
- `load_tool_registry_file_payload(file payload seam)`
- `build_tool_registry_from_file(file manifest seam)`
- `build_tool_registry_from_file(composed manifest seam)`
- `build_tool_registry_from_file(directory-backed composed manifest seam)`
- `build_tool_registry_from_file(named source reference seam)`
- `build_tool_registry_from_file(cycle/duplicate protection seam)`
- `build_tool_registry_from_file_artifacts(diagnostics seam)`
- `build_tool_registry_loader_from_file_artifacts(loader diagnostics seam)`
- `build_tool_registry_provider_from_file_artifacts(provider diagnostics seam)`
- `build_tool_registry_loaders_from_settings_artifacts(settings loader diagnostics seam)`
- `build_tool_registry_providers_from_settings_artifacts(settings provider diagnostics seam)`
- `build_tool_registry_provider_sources_from_settings_artifacts(settings source diagnostics seam)`
- `get_configured_tool_registry_provider_artifacts(configured provider diagnostics seam)`
- `build_tool_registry_diagnostics_summary(runtime summary seam)`
- `build_tool_registry_diagnostics_runtime_artifacts(runtime candidate seam)`
- `build_configured_tool_registry_provider_runtime_artifacts(configured runtime seam)`
- `build_tool_registry_diagnostics_audit_event(runtime audit seam)`
- `build_tool_registry_diagnostics_trace_service_action(runtime internal trace action seam)`
- `build_tool_registry_diagnostics_audit_service_action(runtime audit action seam)`
- `build_configured_tool_registry_provider_runtime_service_actions(runtime audit action list seam)`
- `execute_configured_tool_registry_provider_runtime_service_actions(runtime audit apply seam)`
- `execute_configured_tool_registry_provider_preflight(configured provider preflight single-entry seam)`
- `build_configured_tool_registry_provider_service_execution(configured provider preflight service_execution seam)`
- `execute_configured_tool_registry_provider_service_execution(configured provider preflight apply seam)`
- `build_configured_tool_registry_provider_preflight_result(configured provider preflight result seam)`
- `build_configured_tool_registry_provider_preflight_summary(configured provider preflight summary seam)`
- `build_configured_tool_registry_provider_preflight_result_model(configured provider preflight typed result seam)`
- `build_configured_tool_registry_provider_preflight_summary_model(configured provider preflight typed summary seam)`
- `build_tool_registry_diagnostics_summary_model(tool registry diagnostics typed summary seam)`
- `build_tool_registry_diagnostics_runtime_artifacts_model(tool registry diagnostics typed runtime seam)`
- `build_tool_registry_diagnostics_trace_service_action_model(tool registry diagnostics typed trace service-action seam)`
- `build_tool_registry_diagnostics_audit_service_action_model(tool registry diagnostics typed audit service-action seam)`
- `build_configured_tool_registry_provider_runtime_artifacts_model(configured provider runtime typed artifacts seam)`
- `build_configured_tool_registry_provider_runtime_service_actions_model(configured provider runtime typed service-actions seam)`
- `build_configured_tool_registry_provider_runtime_service_actions_result_model(configured provider runtime typed service-actions result seam)`
- `build_configured_tool_registry_provider_service_execution_model(configured provider service_execution typed seam)`
- `build_configured_tool_registry_provider_service_execution_result_model(configured provider service_execution typed result seam)`
- `build_configured_tool_registry_provider_preflight_summary_model_from_result_model(configured provider preflight typed summary-from-model seam)`
- `build_configured_tool_registry_provider_preflight_result_model_from_models(configured provider preflight typed result-from-model seam)`
- `execute_configured_tool_registry_provider_preflight_model(configured provider preflight typed execution seam)`
- `build_configured_tool_registry_provider_service_execution_result_model_from_models(configured provider service_execution typed result-from-model seam)`
- `execute_configured_tool_registry_provider_service_execution_model(configured provider service_execution typed execution seam)`
- `build_configured_tool_registry_provider_runtime_service_action_model_from_dict(configured provider runtime service-action typed hydration seam)`
- `build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(configured provider runtime service-actions typed hydration seam)`
- `execute_configured_tool_registry_provider_runtime_service_actions_model(configured provider runtime service-actions typed execution seam)`
- `build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(configured provider runtime artifacts shared hydration seam)`
- `build_configured_tool_registry_provider_service_execution_model_from_dict(configured provider service_execution shared hydration seam)`
- `build_configured_tool_registry_provider_preflight_result_model_from_dict(configured provider preflight_result shared bridge hydration seam)`
- `build_configured_tool_registry_provider_preflight_summary_model_from_models(configured provider preflight typed summary-from-model seam)`
- `build_configured_tool_registry_provider_preflight_summary_model_from_parts(configured provider preflight typed shared summary seam)`
- `build_tool_registry_loader_from_file(file-backed loader seam)`
- `build_tool_registry_provider_from_file(file-backed provider seam)`
- `build_tool_registry_provider_factories_from_settings(factory alias seam)`
- `build_tool_registry_loader_factories_from_settings(factory alias seam)`
- `get_tool_registry_provider_source_name_from_settings(source seam)`
- `build_tool_registry_provider_sources_from_settings(source config seam)`
- `build_tool_registry_provider_sources_from_settings(adapter seam)`
- `build_tool_registry_provider_sources_from_settings(named provider reference seam)`
- `build_tool_registry_provider_sources_from_settings(provider factory seam)`
- `build_tool_registry_provider_sources_from_settings(named loader reference seam)`
- `get_tool_registry_profile_name_from_settings(profile seam)`
- `build_tool_registry_profile_settings_config(profile config seam)`
- `build_tool_registry_extra_tools_from_settings(extra tool seam)`
- `build_tool_registry_settings_config(settings config seam)`
- `build_tool_registry_overrides_from_settings(settings seam)`
- `get_disabled_tool_names_from_settings(disable seam)`
- `resolve_tool_registry_provider(precedence seam)`
- `build_tool_registry_provider(default/loader/provider seam)`
- `run_tool(custom registry seam)`
- `run_tool(custom registry_loader seam)`
- `run_tool(custom registry_provider seam)`
- `execute_tool_spec(custom registry seam)`
- `build_tool_runtime_context(custom registry seam)`
- `build_tool_runtime_context(custom registry_provider seam)`
- `execute_tool_plan_item_retry_loop(custom registry seam)`
- `execute_tool_plan_item_service_execution(custom registry seam)`
- `execute_tool_plan_item_service_execution(custom registry_loader seam)`
- `execute_tool_plan_item_service_execution(custom registry_provider seam)`
- `build_tool_attempt_bundle`
- `build_tool_attempt_execution`
- `build_tool_attempt_loop_result`
- `build_tool_attempt_loop_terminal_result`
- `build_tool_plan_item_retry_loop_result`
- `build_tool_plan_item_retry_loop_execution_result`
- `execute_tool_plan_item_retry_loop`
- `execute_tool_plan_item_service_execution`
- `execute_tool_plan_item_service_actions`
- `build_tool_plan_item_stream_effects`
- `build_tool_plan_item_continue_action`
- `build_tool_plan_item_terminal_return_effects`
- `build_tool_plan_item_return_action`
- `build_tool_plan_item_trace_write_action`
- `build_tool_plan_item_next_action_execution`
- `build_tool_plan_item_service_actions`
- `build_tool_plan_item_trace_write_service_action`
- `build_tool_plan_item_continue_service_action`
- `build_tool_plan_item_return_service_actions`
- `build_tool_plan_item_service_effects_execution`
- `build_tool_plan_item_service_execution`
- `build_tool_plan_item_service_effects`
- `build_tool_plan_item_execution` 继续暴露
  - `iteration_execution`
  - `tool_end_event`
  - `error_event`
  - `retryable`
  - `postprocess`
  - `success_effects`
  - `terminal_effects`

## 最近一次关键风险与已知教训

### CI 回归根因

之前曾发生一次真实 CI 回归：

- `build_tool_plan_item_execution()` 收口后没有继续透出 `iteration_execution`
- `chat_execution_service.py` 成功流仍访问 `plan_item_execution["iteration_execution"]`
- 结果触发 `KeyError`
- SSE 没有发出 `done`
- 同时击穿 backend baseline 与 frontend smoke

### 这意味着什么

后续继续抽离时，必须特别小心 helper 返回对象的“消费契约”：

- 不能随手移除已有返回字段
- 如果要替换消费方式，必须先补 focused test
- 任何顶层字段变动都要重新跑：
  - focused tests
  - `compileall`
  - `bash scripts/test_ci_e2e_tooling.sh common`

## 已验证基线

本交接文档生成前，最新已确认通过的命令：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py
bash scripts/test_ci_e2e_tooling.sh common
```

结果：

- focused tests：`192` 条通过
- `compileall`：通过
- `common` tooling + backend/frontend e2e 聚合回归：通过

## 当前建议

### P0: 将当前状态视为阶段性合理停止点

到这一轮为止，`tool-runtime-productionization` 已经完成从：

- 单 tool retry loop
- stream/continue/return effects
- trace/return/next-action 执行输入
- service 最终消费输入

的一整条内部收口链路。

继续机械拆 helper 的收益已经明显下降，而过度包装的风险在上升。因此更推荐的下一步是：

1. 以当前 runtime 边界作为阶段性稳定点
2. 维护 design/handoff 文档与 focused baseline
3. 仅在新需求出现时再继续下一轮抽象

### 什么情况下再继续抽象

只有在以下触发条件出现时，才建议继续推进新一轮 runtime 下沉：

- 引入真实 tool registry
- 增加更多 tool 类型并共享统一 policy
- 将 runtime seam 复用到非 chat 执行路径
- 将 trace/audit/state side effects 再统一成更高层执行器或跨路径执行器

### 继续修改时的固定验证顺序

如果后续仍要修改这条链，继续保持：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py
bash scripts/test_ci_e2e_tooling.sh common
```

## 相关关键文件

- 主运行时收口文件：
  - [backend/app/services/tool_runtime.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/tool_runtime.py)
- 当前编排外壳：
  - [backend/app/services/chat_execution_service.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/app/services/chat_execution_service.py)
- focused 回归：
  - [backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py)
- 设计文档：
  - [docs/superpowers/specs/2026-05-13-tool-runtime-productionization-design.md](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-design.md)
- 本交接文档：
  - [docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/docs/superpowers/specs/2026-05-13-tool-runtime-productionization-handoff.md)
- 实时计划：
  - [.cursor/plans/insightagent_开发计划_306e7915.plan.md](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/.cursor/plans/insightagent_开发计划_306e7915.plan.md)

## 给下一会话的起手建议

如果是新会话直接接手，我建议第一句话就这么定：

1. 先阅读：
   - 本交接文档
   - `tool-runtime-productionization-design.md`
   - `tool_runtime.py`
   - `chat_execution_service.py`
2. 目标：
   - 优先沿现有 `service_actions` 边界继续推进下一阶段 runtime 抽象
3. 约束：
   - 外部 SSE / trace / e2e 契约不变
   - 先补 failing test，再改实现
4. 必跑验证：
   - focused tests
   - `compileall`
   - `common`
当前已经具备的前置条件：

- 默认 registry loader 已显式化，且默认枚举/解析路径都会经过它
- 默认 mock registry 仍保持全局兼容
- 默认 registry 快照与 merge builder 已显式化
- 默认 `load_tool_registry()` 路径现在也会显式经过 `get_default_tool_registry_provider()`
- `chat_execution_service.py` 现在也会在 tool loop 外先显式构造一次 `build_tool_registry_provider()` 再复用到每个 tool plan item
- `run_tool / execute_tool_spec / build_tool_runtime_context` 已支持可选 `registry` 注入
- `run_tool / execute_tool_spec / build_tool_runtime_context` 已支持可选 `registry_provider` 注入
- `run_tool / execute_tool_spec` 已支持可选 `registry_loader` 注入
- 高层 runtime 入口 `execute_tool_plan_item_retry_loop / execute_tool_plan_item_service_execution` 也已支持 `registry` 透传
- 高层 runtime 入口 `execute_tool_plan_item_retry_loop / execute_tool_plan_item_service_execution` 也已支持 `registry_provider` 透传
- `execute_tool_plan_item_service_execution` 也已支持 `registry_loader` 透传
- 后续接真实 registry 时可以先从 provider object 或非默认调用路径逐步接线，而不必先改坏默认行为

## 最新交接补充（2026-05-20）

- `ConfiguredToolRegistryProviderPreflightResult` 这层的 typed internal 链又前推了一步：`build_configured_tool_registry_provider_preflight_result_model()` 现在直接走 hydrated `service_execution_model + service_execution_result_model`，不再先把输入重新拼回顶层 dict 再解析。
- `execute_configured_tool_registry_provider_preflight_model()` 已改成直接消费 typed `execute_configured_tool_registry_provider_service_execution_model()`，减少一层 `model -> dict -> model` 的中转。
- 新增 focused 回归锁定一个真实兼容场景：若 `execution_result` 只带 `trace_write_count/audit_event_count`，preflight result 仍应从 `service_execution` 继承 `provider_source_name/provider/runtime_artifacts`。当前 focused 基线已更新到 `220` 条。
- 下一刀更值得做的是继续压缩 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 这类 outward dict bridge，只保留最薄兼容层；外部 SSE / trace / e2e 契约继续保持不变。

## 最新交接补充（2026-05-21）

- 上一条里提到的“继续压缩 `build_configured_tool_registry_provider_preflight_result_model_from_dict()`”这一刀已经完成：该 helper 现在只做兼容归一化，再直接复用 `build_configured_tool_registry_provider_preflight_result_model()`，减少一层重复的手工 hydration / 组装。
- 本轮新增 focused failing test，锁定另一类最小顶层 payload 兼容场景：当 `preflight_result` 顶层只保留 `trace_write_count/audit_event_count`，而 `provider/provider_source_name/runtime_artifacts` 仅存在于 `service_execution` 时，dict bridge 仍应成功 hydration。
- 当前 focused 基线已更新到 `221` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 相邻一刀建议继续沿 `service_execution_result` 的 outward dict bridge 推进：它和 preflight result 一样，都是 typed internal 旁边还留着一层计数 dict hydration，适合继续按“小 failing test -> 最小 helper 收口”的方式推进。

## 最新交接补充（2026-05-21，续）

- 上一条里提到的 `service_execution_result` 这刀也已经完成：新增 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，并让 `build_configured_tool_registry_provider_service_execution_result_model()` 与 `build_configured_tool_registry_provider_preflight_result_model()` 统一复用这层计数 hydration。
- 本轮新增 focused failing test，锁定最小 `execution_result={}` 兼容场景：`service_execution_result` 应默认回退 `trace_write_count=0`、`audit_event_count=0`，而不是要求调用方显式重复零值。
- 当前 focused 基线已更新到 `222` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀更适合继续沿 `preflight_summary` 这条相邻 outward dict bridge 推进：当前 `build_configured_tool_registry_provider_preflight_summary_model()` 还只是从整份 `preflight_result` hydration 后再取 `.summary`，适合继续按“小 failing test -> 单独 helper 收口”的方式推进。

## 最新交接补充（2026-05-21，续二）

- 上一条里提到的 `preflight_summary` 这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()`，并让 `build_configured_tool_registry_provider_preflight_summary_model()` 直接复用这层 dict bridge。
- 本轮新增 focused failing test，锁定 summary 侧的最小顶层 payload 兼容场景：当顶层 `preflight_result` 只保留计数，而 `provider/provider_source_name/runtime_artifacts` 仅存在于 `service_execution` 时，summary bridge 仍应成功 hydration。
- 当前 focused 基线已更新到 `223` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀更自然的是把 `preflight_summary` / `preflight_result` 两边重复的 `service_execution` 归一化真正抽成共享 helper，避免 provider/provider_source_name/runtime_artifacts merge 逻辑继续复制两份。

## 最新交接补充（2026-05-21，续三）

- 上一条里提到的共享归一化 helper 这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 统一复用。
- 本轮新增 focused failing test，锁定这层共享归一化的优先级语义：顶层 `runtime_artifacts` 应覆盖 `service_execution.runtime_artifacts`，同时保留 `service_execution` 的 `provider_source_name` 与 action 列表。
- 当前 focused 基线已更新到 `224` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀自然会落在 `preflight_result` 顶层计数与共享 `service_execution` 组合出来的 `service_execution_result` 归一化上：这层现在也适合抽成单点 helper，进一步让 summary/result 两条 dict bridge 只保留最薄兼容壳。

## 最新交接补充（2026-05-21，续四）

- 上一条里提到的 `service_execution_result` 共享归一化 helper 这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 统一复用。
- 本轮新增 focused failing test，锁定这层 helper 会保留 `service_execution` 继承出的 provider/provider_source_name/runtime_artifacts，并正确携带 `trace_write_count/audit_event_count`。
- 当前 focused 基线已更新到 `225` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀更自然的是把 `preflight_summary` / `preflight_result` 共同依赖的 typed pair 再抽成共享 helper，彻底去掉 `preflight_result_model_from_dict()` 这边残留的 `model -> dict -> model` 往返。

## 最新交接补充（2026-05-21，续五）

- 上一条里提到的 typed pair 共享 helper 这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，统一返回 `service_execution_model + execution_result_model`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 共同复用。
- `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现已直接调用 `build_configured_tool_registry_provider_preflight_result_model_from_models()`，不再先把 `service_execution_model` 降回 dict 再走一遍 builder。
- 当前 focused 基线已更新到 `226` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀更自然的是继续把 `preflight_execution_models_from_dict()` 内部对 `service_execution_model` 的重复使用显式化成单点 helper，这样 typed pair helper 自身也不再重复构建 execution-result 依赖。

## 最新交接补充（2026-05-21，续六）

- 上一条里提到的 typed helper 细化这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，让 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 在已有 `service_execution_model` 时直接派生 execution-result，而不再重复计算。
- 本轮新增 focused failing test，锁定这层 helper 会保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确携带顶层 `trace_write_count/audit_event_count`。
- 当前 focused 基线已更新到 `227` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀自然会落在通用 `service_execution_result` 这条 typed helper 上：把“已有 `service_execution_model` 时如何补齐 execution-result”也统一成共享入口，减少 preflight/helper 与通用 helper 之间的平行实现。

## 最新交接补充（2026-05-21，续七）

- 上一条里提到的通用 typed helper 统一这刀也已经完成：新增 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_service_execution_result_model()` 与 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 共同复用。
- 本轮新增 focused failing test，锁定这层通用 helper 会保留传入 `service_execution_model` 的 provider/provider_source_name/runtime_artifacts，同时正确携带 `trace_write_count/audit_event_count`。
- 当前 focused 基线已更新到 `228` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀自然会落在 `preflight_result` 这条 typed 入口上：它还可以继续统一到“已有 `service_execution_model` 时如何补齐 result”的 helper 组合，进一步减少手工拼接。

## 最新交接补充（2026-05-21，续八）

- 上一条里提到的 `preflight_result` typed 入口统一这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_preflight_result_model()` 共同复用。
- 本轮新增 focused failing test，锁定这层 helper 会保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确产出 summary 与计数字段。
- 当前 focused 基线已更新到 `229` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-21，续九）

- 相邻的 `preflight_summary` typed 入口统一这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 直接复用。
- 本轮新增 focused failing test，锁定这层 helper 会保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确产出 `tool_names`、`service_action_kinds` 与计数字段。
- 当前 focused 基线已更新到 `230` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 是否还有保留价值；现在 summary/result 两条 dict bridge 已各自有了对称 typed 入口，可以考虑继续压缩这层共享 pair helper，或者把这段 preflight outward bridge 视为阶段性收口完成。

## 最新交接补充（2026-05-21，续十）

- 上一条里提到的 `preflight_result` dict bridge 继续压薄这刀也已经完成：`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现已直接复用 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，不再经过 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`。
- 本轮新增 focused failing test，直接锁定了这层委托方向，避免 `preflight_result_model_from_dict()` 又回到“先拼 typed pair 再转 result”的实现路径。
- 当前 focused 基线已更新到 `231` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是直接评估 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 这层共享 pair helper 是否还能为生产代码提供价值；如果没有，就可以考虑把它降为测试覆盖对象，或者把这段 preflight outward bridge 视为阶段性收口完成。

## 最新交接补充（2026-05-21，续十一）

- 上一条里提到的 `preflight_execution_models_from_dict()` 继续压薄这刀也已经完成：它现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，不再自己显式串联 `...preflight_service_execution_result_model_from_service_execution_model()`。
- 本轮新增 focused failing test，锁定这层 shared pair helper 至少要退化为“组合现有 dict helper”的 compatibility shell，而不再带新的中间逻辑。
- 当前 focused 基线已更新到 `232` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是重新评估这层 pair helper 现在是否还值得保留在生产代码里；如果没有明确消费方，可以考虑把它降为测试/兼容辅助，或者把这段 preflight outward bridge 视为阶段性收口完成。

## 最新交接补充（2026-05-21，续十二）

- 上一条里提到的重复 hydration 这刀也已经完成：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，并让 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 直接复用这层 typed pair helper。
- 本轮新增 focused failing test，锁定这层 helper 会直接复用传入的 `service_execution_model` 本身，同时正确产出 `trace_write_count/audit_event_count` 与归一化 runtime artifacts 对应的 execution-result model。
- 当前 focused 基线已更新到 `233` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是重新判断这层 pair helper 现在是否还属于“值得保留的生产入口”，还是已经可以视为测试/兼容辅助层。

## 最新交接补充（2026-05-21，续十三）

- 上一条里提到的“让 pair helper 重新成为真实生产入口”这刀也已经完成：`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 现已共同复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`。
- 本轮新增 focused failing test，直接锁定 `preflight_result_model_from_service_execution_model()` 的委托方向，避免 summary/result 两条 typed 入口再次各自平行补 execution-result。
- 当前 focused 基线已更新到 `234` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是重新判断这层 pair helper 现在已经成为单点后，是否还需要额外保留 `preflight_service_execution_result_model_from_dict()` 这层外侧桥接，还是可以进一步往 typed 入口集中。

## 最新交接补充（2026-05-25）

- 上一条里提到的 `preflight_service_execution_result_model_from_dict()` 这刀也已经完成：它现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，不再自己先 hydration `service_execution_model` 再补 execution-result。
- 本轮新增 focused failing test，锁定了这层 dict bridge 的新委托方向，避免它又回到单独平行拼 execution-result 的实现路径。
- 当前 focused 基线已更新到 `235` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续评估 `preflight_service_execution_result_model_from_dict()` 与 `preflight_execution_models_from_dict()` 之间是否还有必要同时保留两个 outward bridge 入口。

## 最新交接补充（2026-05-25，续）

- 上一条里提到的 `preflight_service_execution_result_model_from_service_execution_model()` 这刀也已经完成：它现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，不再自己单独走通用 `service_execution_result` helper。
- 本轮新增 focused failing test，锁定了这层 typed wrapper 的新委托方向，避免 shared pair helper 已成为生产单点后又出现平行 execution-result 补齐逻辑。
- 当前 focused 基线已更新到 `236` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续评估 `preflight_service_execution_result_model_from_service_execution_model()` 与 `preflight_execution_models_from_service_execution_model()` 之间是否还有必要同时保留两个 typed 入口。

## 最新交接补充（2026-05-25，续二）

- 上一条里提到的 typed 入口对称化也继续向前推了一刀：`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，不再自己展开 shared execution-model pair helper。
- 本轮新增 focused failing test，直接锁定 `preflight_summary_model_from_service_execution_model()` 的委托方向，避免 summary typed 入口又回到平行解 pair 的实现路径。
- 当前 focused 基线已更新到 `237` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_execution_models_from_service_execution_model()` 现在是否还需要保留成独立生产入口，还是已经可以更多退回为共享兼容辅助层。

## 最新交接补充（2026-05-25，续三）

- 上一条里提到的对称 typed 入口继续向前推了一刀：`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 现在也会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，不再自己展开 shared execution-model pair helper。
- 本轮把既有 focused seam test 改成新的委托方向，再先看红灯，锁定 `preflight_result_model_from_service_execution_model()` 不应再平行解 pair。
- 当前 focused 基线仍为 `237` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_execution_models_from_service_execution_model()` 现在是否还值得保留为独立生产入口。

## 最新交接补充（2026-05-25，续四）

- 上一条里提到的判断这次已经落地：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，而后者改成直接走通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`。
- 本轮先补了 focused failing test，锁定 pair helper 应直接复用 preflight result typed helper；同时把既有 `preflight_service_execution_result_model_from_service_execution_model()` 的 seam test 改成锁定它直走通用 `service_execution_result` helper。
- 当前 focused 基线已更新到 `238` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_execution_models_from_dict()` 是否也该进一步退回为纯组合壳。

## 最新交接补充（2026-05-25，续五）

- 上一条里提到的 dict 侧判断这次也已经落地：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在会直接走通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，而 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`。
- 本轮把两条既有 focused seam test 改成新的 dict 委托方向，再先看红灯，锁定 dict pair helper 也不应再平行生产 execution-result。
- 当前 focused 基线仍为 `238` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_service_execution_model_from_dict()` 这一层是否还值得继续单独保留。

## 最新交接补充（2026-05-25，续六）

- 上一条里提到的 dict outward 入口集中也继续向前推了一刀：`build_configured_tool_registry_provider_preflight_summary_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现在都直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，不再各自重复做 `service_execution` hydration。
- 本轮新增一条 focused failing test，并把既有 `preflight_result_model_from_dict()` seam test 改成新的 pair-helper 委托方向，再先看红灯后转绿。
- 当前 focused 基线已更新到 `239` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_service_execution_model_from_dict()` 是否还值得继续保留为独立 helper，还是应进一步退回 payload-normalization 辅助层。

## 最新交接补充（2026-05-25，续七）

- 上一条里提到的 payload-normalization 判断这次也已经落地：新增 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，统一负责 `preflight` 顶层和 `service_execution` 子 payload 的 provider/provider_source_name/runtime_artifacts merge。
- `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`、`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`、`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在都会直接复用这层 payload helper，dict 侧不再重复做 `service_execution` hydration。
- 当前 focused 基线已更新到 `240` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_service_execution_model_from_dict()` 现在是否值得继续保留为公共入口，还是可以进一步退回“测试/兼容友好壳”。

## 最新交接补充（2026-05-25，续八）

- 上一条里提到的“payload normalization 之后的单次 hydration”这刀也已经落地：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()`，统一负责把 normalized payload 转成 `service_execution_model + execution_result_model`。
- `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`、`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`、`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在都直接复用这层新 helper，而不再各自单独做 typed hydration。
- 当前 focused 基线仍为 `240` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_service_execution_model_from_dict()` 现在是否还值得作为公共 helper 暴露，还是可以更多退回测试/兼容友好壳。

## 最新交接补充（2026-05-25，续九）

- 上一条里提到的“退回成测试/兼容友好壳”这刀也继续向前推了一步：`build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在都直接从 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 取第一/第二个 model。
- 本轮把两条既有 seam test 改成新的 dict 单点委托方向，再先看红灯后转绿，锁定这两个 helper 不再各自直接触碰 payload-to-pair helper。
- 当前 focused 基线仍为 `240` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按当前节奏推进，更自然的是继续判断 `preflight_execution_models_from_dict()` 是否值得继续保留为公开 helper，还是把 dict inward 的公开重心进一步压到 payload-normalization + typed summary/result 入口。

## 最新交接补充（2026-05-25，续十）

- 上一条里提到的“把 dict inward 的公开重心进一步上移”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_models_from_dict()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()`，统一产出 `service_execution_model + execution_result_model + summary_model + result_model`。
- `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`、`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`、`build_configured_tool_registry_provider_preflight_summary_model_from_dict()`、`build_configured_tool_registry_provider_preflight_result_model_from_dict()`，以及 typed 侧 `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` / `...result_model_from_service_execution_model()` 现在都直接从这层 total-model helper 取各自结果，不再平行展开 pair/result 链路。
- 当前 focused 基线已更新到 `244` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` / `...from_service_execution_model()` 这两层 pair helper 是否还值得继续作为公开 seam 保留，还是可以进一步退到 total-model helper 的内部组合层。

## 最新交接补充（2026-05-25，续十一）

- 上一条里提到的“让 pair helper 继续退到 total-model 内部组合层”这刀已经开始落地：新增 `build_configured_tool_registry_provider_preflight_models_from_models()`，统一负责从 typed `service_execution/execution_result` 派生 `summary/result`。
- `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现在已直接从 `build_configured_tool_registry_provider_preflight_models_from_dict()` 取前两个 model，`build_configured_tool_registry_provider_preflight_result_model_from_models()` 也改为直接复用 `preflight_models_from_models()`；这样 dict pair helper 与 result-from-models 都进一步退回为组合壳。
- 当前 focused 基线已更新到 `246` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 是否也该仿照 dict 侧进一步退到 total-model helper 之下，或者把它保留成 typed 基础 seam。

## 最新交接补充（2026-05-25，续十二）

- 上一条里提到的“让 typed pair helper 也仿照 dict 侧退到 total-model helper 之下”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()`，统一负责 normalized payload 直接派生 `service_execution/execution_result/summary/result` 四个 typed model。
- `build_configured_tool_registry_provider_preflight_models_from_dict()` 现在已直接复用这层 payload-total helper，而 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 也改为直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 取前两个 model；这样 dict/typed 两侧 pair helper 都退回为 total-model 兼容壳。
- 当前 focused 基线已更新到 `247` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 是否也该进一步退回到 total-model helper 之下，或者把它保留成 dict inward 的最小 typed hydration seam。

## 最新交接补充（2026-05-25，续十三）

- 上一条里提到的“让 payload pair helper 也退回到 total-model helper 之下”这刀已经落地：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 取前两个 model。
- 同时 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 本身也改为直接完成 `service_execution_model` hydration、`execution_result_model` 派生和 total-model 组装，不再绕回 payload pair helper；这样 dict inward 的主 seam 已进一步集中到 `payload -> total models`。
- 当前 focused 基线已更新到 `249` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 是否也值得进一步退到 `preflight_models_from_service_execution_model()` 之下，还是保留为 typed execution-result 的基础 seam。

## 最新交接补充（2026-05-25，续十四）

- 上一条里提到的“让 typed result helper 也退回到 total-model helper 之下”这刀已经落地：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 取第二个 model。
- 同时 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 本身也改为直接走通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()` 派生 execution-result，不再绕回 typed preflight result helper；这样 typed inward 的主 seam 已进一步集中到 `service_execution_model -> total models`。
- 当前 focused 基线仍为 `249` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_summary_model_from_models()` 是否值得也退到 `preflight_models_from_models()` 之下，或者保留为 `summary` 基础 seam。

## 最新交接补充（2026-05-25，续十五）

- 上一条里提到的“让 summary seam 也退回到 total-model helper 之下”这刀已经落地：`build_configured_tool_registry_provider_preflight_summary_model_from_models()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_models()` 取第三个 model，而 `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()` 则直接返回已有 `result.summary`。
- 同时 `build_configured_tool_registry_provider_preflight_models_from_models()` 本身也改为直接走 `build_configured_tool_registry_provider_preflight_summary_model_from_parts()` 组装 summary，再组合 result model，不再反向依赖 `summary_model_from_models()`；这样 summary/result 的核心装配权已进一步集中到 total-model seam。
- 当前 focused 基线已更新到 `251` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` / `...from_dict()` 这两层 outward result 壳是否还有值得继续共用的更高层入口，或者当前这条 total-model seam 已经足够稳定。

## 最新交接补充（2026-05-25，续十六）

- 上一条里提到的“给 outward result 壳补更高层共用入口”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_models()` 与 `execute_configured_tool_registry_provider_preflight_models()`，统一负责 raw `service_execution/execution_result` 和 runtime execute 两条高层路径到 total models 的总装。
- `build_configured_tool_registry_provider_preflight_result_model()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models()` 取第四个 model，`execute_configured_tool_registry_provider_preflight_model()` 则会直接从 `execute_configured_tool_registry_provider_preflight_models()` 取第四个 model，不再各自重复做 hydration/执行后组装。
- 当前 focused 基线已更新到 `253` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是继续判断 `build_configured_tool_registry_provider_preflight_summary()` / `build_configured_tool_registry_provider_preflight_result()` 这两个 `.to_dict()` outward 壳是否还值得再共享一个更高层 helper，或者当前边界已经足够薄。

## 最新交接补充（2026-05-25，续十七）

- 上一条里提到的“给 outward summary/result 壳补更高层 dict helper”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_dicts_from_models()`、`build_configured_tool_registry_provider_preflight_dicts()` 与 `execute_configured_tool_registry_provider_preflight_dicts()`，统一负责最终 `summary_dict + result_dict` outward 组装。
- `build_configured_tool_registry_provider_preflight_summary()` 现在会直接从 `build_configured_tool_registry_provider_preflight_dicts()` 取第一个 dict，`build_configured_tool_registry_provider_preflight_result()` 则会直接从 `build_configured_tool_registry_provider_preflight_dicts_from_models()` 取第二个 dict，`execute_configured_tool_registry_provider_preflight()` 也直接从 `execute_configured_tool_registry_provider_preflight_dicts()` 取第二个 dict，不再各自重复做 typed hydration、result 组装或执行后 dict 转换。
- 当前 focused 基线已更新到 `256` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_result_model()` / `build_configured_tool_registry_provider_preflight_result()` 与 `execute_configured_tool_registry_provider_preflight_model()` / `execute_configured_tool_registry_provider_preflight()` 这两组 model/dict outward 入口是否还值得继续共存，还是可以把当前边界视为阶段性稳定点。

## 最新交接补充（2026-05-25，续十八）

- 上一条里提到的“把高层 model/dict outward 入口也继续合并”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_outputs_from_models()`、`build_configured_tool_registry_provider_preflight_outputs()` 与 `execute_configured_tool_registry_provider_preflight_outputs()`，统一负责 `service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的高层总装。
- `build_configured_tool_registry_provider_preflight_models()`、`build_configured_tool_registry_provider_preflight_result_model()`、`build_configured_tool_registry_provider_preflight_result()`、`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`、`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`、`execute_configured_tool_registry_provider_preflight_models()`、`execute_configured_tool_registry_provider_preflight_model()` 与 `execute_configured_tool_registry_provider_preflight()` 现在都退回为从这层 `outputs` helper 取对应 model/dict 的兼容壳，不再重复做高层 outward 组装。
- 当前 focused 基线已更新到 `257` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `preflight_summary_model_from_dict()` / `preflight_result_model_from_dict()` / `preflight_summary()` 这几条仅剩的 dict 兼容壳是否也值得进一步并回更少的公开入口，或者把当前 `outputs` 边界视为阶段性稳定点。

## 最新交接补充（2026-05-25，续十九）

- 上一条里提到的“把单参 `preflight_result` 的 dict 兼容壳也继续并回更少入口”这刀已经落地：新增 `build_configured_tool_registry_provider_preflight_outputs_from_dict()`，统一负责 `preflight_result -> service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`、`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`、`build_configured_tool_registry_provider_preflight_models_from_dict()`、`build_configured_tool_registry_provider_preflight_summary_model_from_dict()`、`build_configured_tool_registry_provider_preflight_result_model_from_dict()`、`build_configured_tool_registry_provider_preflight_dicts()` 与 `build_configured_tool_registry_provider_preflight_summary()` 现在都退回为从这层 `outputs_from_dict()` 取对应结果的兼容壳，不再各自重复串联单参 dict hydration / outward 组装。
- 当前 focused 基线维持 `257` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` / `build_configured_tool_registry_provider_preflight_models_from_dict()` 与 `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 这组三层 dict 入口是否还值得同时保留，还是可以把当前 `outputs_from_dict()` 边界视为阶段性稳定点。

## 最新交接补充（2026-05-25，续二十）

- 在上一条单参 dict seam 收口基础上，这轮又把 `service_execution_payload + preflight_result` 这条 payload typed 链也并回到了高层 `outputs` seam：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 现在都直接从 `build_configured_tool_registry_provider_preflight_outputs()` 取对应 typed 结果。
- 这样 payload 路径也不再各自重复做 payload -> typed hydration / summary/result 组装，`outputs(service_execution, execution_result)` 继续成为这段 `preflight` outward/inward 兼容链的核心总装入口。
- 当前 focused 基线维持 `257` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`、`build_configured_tool_registry_provider_preflight_models_from_dict()`、`build_configured_tool_registry_provider_preflight_outputs_from_dict()` 这组三层 dict 入口，和 `...from_service_execution_payload()` 两层 payload 入口里，是否还有值得继续减薄的公开壳。

## 最新交接补充（2026-05-25，续二十一）

- 在上一条 payload typed 链收口基础上，这轮又把 `service_execution_payload + execution_result` 这条 payload total-output seam 本身也补成了单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()`，统一负责 `service_execution_payload + execution_result -> service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- `build_configured_tool_registry_provider_preflight_outputs()` 现在退回为从这层 payload helper 取结果的兼容壳，而 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 也一起退回为只取对应 typed 结果的兼容壳。
- 当前 focused 基线已更新到 `258` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_outputs()` / `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` / `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 这三层 total-output 入口是否还值得同时保留。

## 最新交接补充（2026-05-25，续二十二）

- 在上一条 payload total-output seam 收口基础上，这轮又把 typed `service_execution_model + preflight_result` 这条链也并回到了 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`、`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 现在都直接从这层 helper 取对应 typed 结果。
- 这样 `service_execution_model` 路径也不再各自重复做 `execution_result_model` 派生与 summary/result 组装，typed total-output 组装权继续集中到单点。
- 当前 focused 基线已更新到 `259` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`、`build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 与 `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 这三层 total-output 入口是否还值得同时保留。

## 最新交接补充（2026-05-25，续二十三）

- 这轮继续把单参 dict total-output 总出口也并回到了更高层 `build_configured_tool_registry_provider_preflight_outputs(service_execution, execution_result)`：`build_configured_tool_registry_provider_preflight_outputs_from_dict()` 现在只负责提取兼容 `service_execution` payload，再直接调用高层 outputs helper，不再自己显式指向 `outputs_from_service_execution_payload()`。
- 这样 `preflight_result -> total outputs` 这条 dict 总出口又少了一层固定委托方向，单参 dict total-output 总装权进一步收敛到高层 `outputs()` 入口。
- 当前 focused 基线已更新到 `261` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_outputs()` 与 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 这两层 total-output 入口是否还值得继续并存。

## 最新交接补充（2026-05-25，续二十四）

- 这轮继续把 `service_execution_payload + execution_result` 这条 total-output 入口也并回到了高层 `build_configured_tool_registry_provider_preflight_outputs()`：高层 `outputs()` 现在自己承担 `service_execution` hydration，再直接复用 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`。
- 相应地，`build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 已退回为从高层 `outputs()` 取总装结果的兼容壳，不再自己固定承担 payload -> typed hydration。
- 当前 focused 基线已更新到 `263` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 是否也该进一步并回更少的公开 total-output 入口。

## 最新交接补充（2026-05-25，续二十五）

- 这轮继续把 execute 侧也补成了对称的 typed total-output seam：新增 `execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`，统一负责 `service_execution_model + trace/persist/audit -> execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- 相应地，`execute_configured_tool_registry_provider_preflight_outputs()` 已退回为只负责构造 `service_execution_model`，再直接委托给这层 typed execute helper，不再自己同时承担 execute 和 outputs 总装。
- 当前 focused 基线已更新到 `265` 条；本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
- 下一刀如果继续按现在这个“大一点”的节奏推进，更自然的是评估 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 与 `execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 之间，是否还值得继续抽更共享的 typed total-output seam。

## 最新交接补充（2026-05-26，续二十六）

- 这轮没有再增加新的总装 helper，而是把最外层 summary/result wrapper 这批 outward 入口整体退回到了最近邻 helper：`build_configured_tool_registry_provider_preflight_summary()` 直接复用 `build_configured_tool_registry_provider_preflight_dicts()`，`build_configured_tool_registry_provider_preflight_summary_model_from_dict()` / `...from_service_execution_model()` 与 `build_configured_tool_registry_provider_preflight_result_model()` / `...from_dict()` / `...from_service_execution_model()` 现在都优先复用对应 `models()` helper。
- 同时，`build_configured_tool_registry_provider_preflight_result()` 现在退回为复用 `build_configured_tool_registry_provider_preflight_result_model()`，`execute_configured_tool_registry_provider_preflight_model()` 退回为复用 `execute_configured_tool_registry_provider_preflight_models()`，`execute_configured_tool_registry_provider_preflight()` 退回为复用 `execute_configured_tool_registry_provider_preflight_dicts()`。
- 这样 outward wrapper 层不再平行依赖更深的 `outputs()` seam，职责边界更清楚；当前 focused 基线保持 `265` 条，本轮通过的是既有 seam tests 改严而不是新增 helper 数量。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续二十七）

- 这轮继续把 `service_execution/execution_models` 这组 wrapper 也退回到了最近邻 helper：`build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`；typed `...service_execution_result_model_from_service_execution_model()` 退回为复用 `...execution_models_from_service_execution_model()`。
- 同时，`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 与 `...from_service_execution_model()` 也都退回为从对应 `models()` helper 取前两个结果，不再平行直连更深的 `outputs()` seam。
- 进一步地，`build_configured_tool_registry_provider_preflight_models()`、`...models_from_service_execution_payload()`、`...models_from_dict()` 与 typed `...models_from_service_execution_model()` 现在也都直接走 `models_from_models()` 主链，不再先经过 `outputs()`。
- 当前 focused 基线已更新到 `267` 条；本轮同样是把既有 seam tests 改严后收口实现，没有新增 helper 数量。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续二十八）

- 这轮继续把 `dicts` 这一层 outward wrapper 也退回到了最近邻 `models()` helper：`build_configured_tool_registry_provider_preflight_dicts_from_models()` 现在直接复用 `build_configured_tool_registry_provider_preflight_models_from_models()` 再做 `to_dict()`。
- 同时，`build_configured_tool_registry_provider_preflight_dicts()` 已退回为先走 `build_configured_tool_registry_provider_preflight_models_from_dict()`，再统一交给 `dicts_from_models()`；`execute_configured_tool_registry_provider_preflight_dicts()` 也已退回为先走 `execute_configured_tool_registry_provider_preflight_models()`，再统一交给同一层 `dicts_from_models()`。
- 这样 `dicts` 这一层不再平行直连更深的 `outputs()` seam，summary/result 的 dict outward 投影职责进一步集中到 typed `models` 主链之上。
- 本轮新增了三条 focused seam tests，分别锁定 `dicts_from_models()`、`build_preflight_dicts()`、`execute_preflight_dicts()` 的新委托方向；focused 基线已更新到 `270` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续二十九）

- 这轮继续把 `outputs` 这一组 build/execute wrapper 也退回到了 `models + dict projection` 主链：build 侧 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`、`build_configured_tool_registry_provider_preflight_outputs()`、`...outputs_from_service_execution_payload()`、`...outputs_from_dict()` 现在都先走各自最近邻的 `models` helper，再统一通过共享 `build_configured_tool_registry_provider_preflight_outputs_from_resolved_models()` 组装 `summary/result` dict。
- execute 侧也补齐了对称的 typed seam：新增 `execute_configured_tool_registry_provider_preflight_models_from_service_execution_model()`，统一负责 `service_execution_model + trace/persist/audit -> service_execution_result_model + summary_model + result_model`，然后让 `execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 与 `execute_configured_tool_registry_provider_preflight_outputs()` 都退回到这条 `execute_models` 主链之后再统一做 dict 投影。
- 这样 build/execute 两侧的 `outputs` 入口都不再保留平行的总装路径，而只是 typed `models` 主链上的 outward compatibility shell。
- 本轮把既有 build/execute seam tests 一起改严，并新增两条 focused seam tests，分别锁定 `build_preflight_outputs_from_service_execution_model()` 和 `execute_preflight_outputs_from_service_execution_model()` 的新委托方向；focused 基线已更新到 `272` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十）

- 这轮继续把 `service_execution` 内核层的两处 typed seam 也收紧了：新增 `build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model()`，让 `build_configured_tool_registry_provider_service_execution_model()` 直接从 typed `runtime_artifacts` 派生 typed `service_actions`，不再先走 `runtime_artifacts.to_dict()`。
- execute 侧则让 `execute_configured_tool_registry_provider_service_execution_model()` 直接把 `service_execution.service_actions` 组装成 `ConfiguredToolRegistryProviderRuntimeServiceActionsModel` 后调用 typed `execute_configured_tool_registry_provider_runtime_service_actions_model()`，不再先做 `[action.to_dict()] -> execute_*_result_model()` 这段 dict 往返。
- 这样 `service_execution` 这一层在 build/execute 两侧都更集中地停留在 typed model 内部流转，进一步缩小了 dict bridge 的使用面。
- 本轮新增两条 focused seam tests，分别锁定 `build_service_execution_model()` 与 `execute_service_execution_model()` 的新委托方向；focused 基线已更新到 `274` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十一）

- 这轮继续把相邻的 `service_execution result + dict` 这一层也补成了 `outputs` 单点：新增 `build_configured_tool_registry_provider_service_execution_outputs()`、`...outputs_from_service_execution_model()`、`...outputs_from_models()` 与 `execute_configured_tool_registry_provider_service_execution_outputs()`、`...outputs_from_service_execution_model()`。
- 相应地，`build_configured_tool_registry_provider_service_execution_result_model()` 与 `...result_model_from_service_execution_model()` 现在都退回为从 `build_service_execution_outputs*` 取 typed result model；`execute_configured_tool_registry_provider_service_execution()` 则退回为从 `execute_service_execution_outputs*` 取 result dict。
- 这样 `service_execution` 这层的 build/execute 两侧都不再保留平行的 result+dict 组装路径，而是先统一走 `outputs` seam，再按需取 typed result 或 dict。
- 本轮新增三条 focused seam tests，分别锁定 `build_service_execution_result_model()`、`build_service_execution_result_model_from_service_execution_model()`、`execute_service_execution()` 的新委托方向；focused 基线已更新到 `277` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十二）

- 这轮继续把更内层的 `runtime_service_actions` build/execute wrapper 也补成了 `outputs` 单点：新增 `build_configured_tool_registry_provider_runtime_service_actions_outputs()`、`...outputs_from_runtime_artifacts_model()`、`...outputs_from_models()` 与 `execute_configured_tool_registry_provider_runtime_service_actions_outputs()`、`...outputs_from_models()`。
- 相应地，`build_configured_tool_registry_provider_runtime_service_actions()` 与 `build_configured_tool_registry_provider_runtime_service_actions_model()` 现在都退回为从 `build_runtime_service_actions_outputs*` 取 dict / typed actions model；`execute_configured_tool_registry_provider_runtime_service_actions()` 与 `execute_configured_tool_registry_provider_runtime_service_actions_result_model()` 则退回为从 `execute_runtime_service_actions_outputs*` 取 result dict / typed result model。
- 同时，`build_configured_tool_registry_provider_service_execution_model()` 已改成直接复用 `build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model()`，`execute_configured_tool_registry_provider_service_execution_model()` 也改成直接复用 `execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models()`，让 `service_execution` 这一层也不再平行直连更深的 `runtime_service_actions` 核心执行逻辑。
- 本轮新增七条 focused seam / keep-fields tests，分别锁定 `build_runtime_service_actions()`、`build_runtime_service_actions_model()`、`build_runtime_service_actions_outputs_from_models()`、`build_runtime_service_actions_outputs_from_runtime_artifacts_model()`、`execute_runtime_service_actions()`、`execute_runtime_service_actions_model()`、`execute_runtime_service_actions_outputs_from_models()` 的新边界；focused 基线已更新到 `284` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十三）

- 这轮继续把 `runtime_service_actions` 的 typed-from-artifacts 和 dict-from-dicts 两条入口也并回到了最近邻 `outputs` seam：新增 `build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts()`。
- 相应地，`build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model()` 现在退回为从 `build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model()` 取 typed actions model；`build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts()` 则退回为从 `...outputs_from_dicts()` 取 typed actions model。
- 同时，`build_configured_tool_registry_provider_service_execution_model_from_dict()` 已改成直接复用 `build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts()`，而 `execute_configured_tool_registry_provider_runtime_service_actions_outputs()` 也改成先走 `...outputs_from_dicts()` 再统一进入 typed execute seam。
- 这样 `runtime_service_actions` 这一层的 typed-from-artifacts、dict-from-dicts、dict execute 与 `service_execution_model_from_dict()` 不再各自保留平行的组装逻辑，而是都退回到更少的最近邻 helper。
- 本轮新增四条 focused seam / keep-fields tests，分别锁定 `build_runtime_service_actions_model_from_runtime_artifacts_model()`、`build_runtime_service_actions_model_from_dicts()`、`build_runtime_service_actions_outputs_from_dicts()`、`build_service_execution_model_from_dict()` 的新边界；focused 基线已更新到 `288` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十四）

- 这轮继续把 build-side 的 `runtime_service_actions result` 也补成了对称 `outputs` seam：新增 `build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models()` 与 `...outputs_from_dict()`。
- 相应地，`build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()` 现在退回为从 `build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict()` 取 typed result model，不再自己做 dict→typed count hydration。
- 同时，`build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 已改成先复用这层 `runtime_service_actions result outputs` seam，再统一进入既有 `service_execution outputs` 主链，从而让 build-side count result 与上层 `service_execution` result 组装之间也只保留一条最近邻委托路径。
- 本轮新增四条 focused seam / keep-fields tests，分别锁定 `build_runtime_service_actions_result_model_from_dict()`、`build_runtime_service_actions_result_outputs_from_models()`、`build_runtime_service_actions_result_outputs_from_dict()`、`build_service_execution_outputs_from_service_execution_model()` 的新边界；focused 基线已更新到 `292` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十五）

- 这轮继续把 `preflight` 这边两条 build-side `service_execution_result` wrapper 也并回到了 `service_execution outputs` 主链。
- 相应地，`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在退回为先走 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，再直接复用 `build_configured_tool_registry_provider_service_execution_outputs()`；`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 则退回为直接复用 `build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()`。
- 这样 `preflight` build-side 的 `service_execution_result` 兼容入口不再单独绕一层 `preflight_execution_models` 主链，而是和更底层的 `service_execution result outputs` 统一到同一条最近邻委托路径上。
- 本轮通过改严两条既有 focused seam tests 完成收口，没有新增测试条数；focused 基线维持 `292` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十六）

- 这轮继续把 build-side 的 `preflight models / execution_models` 三条入口一起并回了 `service_execution outputs` 主链。
- 相应地，`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` / `...from_service_execution_payload()` / `...from_service_execution_model()` 现在都会先复用 `build_configured_tool_registry_provider_service_execution_outputs()` 或 `...outputs_from_service_execution_model()` 产出 typed `execution_result_model`，再只保留一层最薄的 `service_execution_model` hydration / 透传。
- 同时，`build_configured_tool_registry_provider_preflight_models_from_dict()` / `...from_service_execution_payload()` / `...from_service_execution_model()` 也统一退回为“单次 `service_execution_model` hydration + `service_execution outputs` + `build_configured_tool_registry_provider_preflight_models_from_models()`”的总装路径，不再混用早前的 raw `build_preflight_models()` 或平行的 result-model 组装。
- 这让 `preflight` build-side 的 `dict` / `payload` / typed 三条入口现在都落在同一条更稳定的 typed seam 上：`service_execution_model` 负责输入归一化，`service_execution outputs` 负责 typed `execution_result_model`，`preflight_models_from_models()` 负责最上层 `summary/result`。
- 本轮主要通过改严 6 条既有 focused seam tests 完成收口，没有新增测试条数；focused 基线仍维持 `292` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。

## 最新交接补充（2026-05-26，续三十七）

- 这轮继续把最外层 raw `service_execution + execution_result` 的 build wrapper 也退回到了 payload seam。
- 相应地，`build_configured_tool_registry_provider_preflight_models()` 现在直接复用 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()`；`build_configured_tool_registry_provider_preflight_outputs()` 直接复用 `...outputs_from_service_execution_payload()`；`build_configured_tool_registry_provider_preflight_result_model()` 则直接复用 `...models_from_service_execution_payload()` 再取第四个 result model。
- 这样 raw 输入层不再自己做 `service_execution_model` hydration、`execution_result_model` 派生或 helper 选路，而是只保留参数命名兼容壳；真正的 build-side 总装边界进一步稳定到 `payload -> service_execution outputs -> preflight_models_from_models()` 这条链上。
- 本轮主要通过改严 3 条既有 focused seam tests 完成收口，没有新增测试条数；focused 基线仍维持 `292` 条。
- 本轮校验仍然是 `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py`、`python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py`、`bash scripts/test_ci_e2e_tooling.sh common` 全通过。
