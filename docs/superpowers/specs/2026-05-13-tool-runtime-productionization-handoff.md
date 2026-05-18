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
- `build_tool_registry_from_file()`
- `build_tool_registry_loader_from_file()`
- `build_tool_registry_provider_from_file()`
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

[backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py) 当前已经扩展到 **167 条测试**，并全部通过。

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

- focused tests：`167` 条通过
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
