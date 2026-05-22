# Tool Runtime Productionization Design

**Date:** 2026-05-13
**Scope:** InsightAgent backend service layer
**Status:** Phase checkpoint after runtime extraction and service-consumption收口

## Goal

将 `backend/app/services/chat_execution_service.py` 中与 tool 执行相关的内部编排逻辑，持续下沉到
`backend/app/services/tool_runtime.py`，同时保持以下外部契约不变：

- SSE 事件形状不变
- trace 结构不变
- 错误语义不变
- backend/frontend e2e 与 common tooling 回归不变

## Non-Goals

- 不修改 REST API 契约
- 不新增真实 tool 或 provider 能力
- 不引入队列、并发或工作流语义变化
- 不重写最终答案生成链路
- 不为了抽象而抽象到完整 framework

## Success Criteria

- `mock_plan`、`mock_retrieve`、`calc_eval` 的现有行为保持不变
- `[mock-tool-error]` 的 retry 语义保持不变
- `[mock-tool-fatal]` 的 fatal 语义保持不变
- `tool_start/tool_end/error/trace/state/done` 对外事件契约保持不变
- tool 级控制流和大部分后处理字段搬运不再堆在 `chat_execution_service.py`

## Current Architecture

### 1. `tool_runtime.py` 当前已承接的层级

运行时模块现在不仅负责 tool plan 和单 tool 执行，还已经承接了多层内部编排 helper，主要可分为：

- registry / invocation / runtime context
- attempt start / success / error events
- retry decision / transition
- iteration context / iteration execution
- plan-item result / execution result / postprocess
- success effects / terminal effects
- retry loop 最终结果
- service 消费输入的逐层高层 helper

当前关键 helper 包括：

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
- `build_tool_attempt_bundle()`
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
- `build_tool_attempt_execution()`
- `build_tool_attempt_loop_result()`
- `build_tool_attempt_loop_terminal_result()`
- `build_tool_plan_item_retry_loop_result()`
- `build_tool_plan_item_retry_loop_execution_result()`
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

### 2. `chat_execution_service.py` 当前剩余职责

在当前阶段，`chat_execution_service.py` 保留的职责已经更接近“编排副作用执行器”：

- 外层 `tool_plan` 遍历
- SSE 发射时机控制
- 按 `service_actions` 顺序执行 trace / continue / return 副作用
- tool 阶段之后的最终答案生成、超时、取消与任务生命周期治理

当前单个 tool 的 service 壳子已经接近：

1. 调 `execute_tool_plan_item_service_execution()`
2. 直接获取 runtime 产出的 `service_execution`
3. 调 `execute_tool_plan_item_service_actions()`
4. 只保留 SSE 字符串包装与 return 边界

## Why This Is a Reasonable Stopping Point

这一轮之后，继续机械拆小 helper 的边际收益已经明显下降，原因是：

- 单个 tool 的 service 分支已经很薄
- 外部 SSE/trace/e2e 契约已经被多层 focused regression 钉住
- 继续细拆容易把“清晰边界”变成“过度包装”
- 当前系统还没有新真实 tool、并发 runtime、队列执行器等新需求来验证更深抽象是否值得

因此，当前更合理的阶段性结论不是“继续无止境地下沉”，而是：

- 把现有内部 seam 稳定下来
- 把设计文档、handoff 文档和测试基线同步到真实状态
- 等到新真实能力进入时，再以需求倒逼下一轮 runtime 抽象

## Behavioral Compatibility Requirements

以下契约必须继续保持语义兼容：

- tool plan 输出结构
- tool input / output 结构
- retry count 与 fatal/retryable 语义
- `meta.tool` 和 trace step 内容
- `tool_execution_error` code
- `tool_start/tool_end/error/trace/state/done` 事件形状

## Testing and Verification

当前采用严格的 focused compatibility + full regression 验证方式。

### Focused regression baseline

`backend/scripts/test_tool_runtime_slice.py` 当前已扩展到 **234 条测试**，覆盖：

- tool plan compatibility
- tool execution compatibility
- custom registry injection seam compatibility
- registry builder / enumeration seam compatibility
- high-level runtime registry threading compatibility
- default registry loader compatibility
- pluggable registry loader compatibility
- provider-object registry seam compatibility
- default provider-object path compatibility
- named default provider implementation compatibility
- configured provider composition compatibility
- configured provider entrypoint compatibility
- settings-backed registry override compatibility
- settings-backed disabled tool compatibility
- settings-backed registry profile compatibility
- settings-backed extra tool alias compatibility
- settings-backed named provider compatibility
- settings-backed provider source compatibility
- provider source adapter compatibility
- loader-backed provider adapter compatibility
- provider-factory-backed adapter compatibility
- settings-backed named loader compatibility
- loader-factory-backed adapter compatibility
- settings-backed factory alias compatibility
- file-backed registry source compatibility
- file-backed registry manifest compatibility
- composed file-backed manifest compatibility
- directory-backed composed manifest compatibility
- file manifest named source reference compatibility
- file manifest cycle/duplicate protection compatibility
- file manifest diagnostics artifacts compatibility
- settings-backed diagnostics artifact chain compatibility
- runtime diagnostics summary / candidate compatibility
- runtime diagnostics audit event compatibility
- runtime diagnostics audit action chain compatibility
- provider resolution precedence compatibility
- chat-consumed prebuilt provider compatibility
- transient/fatal/unknown tool 行为
- retry loop 最终结果
- stream effects
- continue / return / trace write / service execution 各层 helper shape
- service 单入口消费链

### Required verification commands

每轮继续修改该链路时，固定执行：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py
bash scripts/test_ci_e2e_tooling.sh common
```

## Risks and Guardrails

### Risk: contract drift

如果 helper 返回 shape 改动但 service 消费未同步，可能造成：

- 丢失 `done`
- trace 顺序漂移
- terminal return 收尾丢字段
- backend/frontend e2e 同时击穿

Guardrails:

- 任何 helper shape 变化先补 focused failing test
- 兼容字段不要随手删除
- 每轮必须跑 focused + compileall + common

### Risk: over-abstraction

如果没有新需求支撑，继续机械拆 helper 容易让代码：

- 多一层间接性
- 减少可读性
- 提高未来接手成本

Guardrails:

- 优先在“减少真实 service 胶水”时再抽象
- 若新 helper 只是换名转发、没有明显消费收益，就应停止

## Recommended Next Step

当前更推荐的下一步不是继续硬拆内部 helper，而是：

1. 维持当前 runtime 边界作为阶段性稳定点
2. 将 design/handoff 文档视为“当前真实架构说明”
3. 等到以下需求出现时再继续下一轮抽象：
   - 引入真实 tool registry
   - 支持更多 tool 类型或 runtime policy
   - 引入并发/队列/workflow 执行模型
   - 将最终答案生成链也纳入更统一的 runtime seam

## Future Work Triggers

只有在这些触发条件出现时，继续深入抽象才更合理：

1. 需要新增真实 tool 并共享统一 policy
2. 需要把当前 `registry / loader / provider` seam 接到真实 registry provider
3. 需要复用同一套 runtime seam 到非 chat 执行路径
4. 需要将 trace / audit / state side effects 再统一成更高层执行器

## Latest Sync (2026-05-20)

- `ConfiguredToolRegistryProviderPreflightResult` 这层又去掉了一段 dict outward 兼容桥接：`build_configured_tool_registry_provider_preflight_result_model()` 不再把 `service_execution + execution_result` 重新拼成顶层 dict 后再回灌，而是先 hydration 成 `ConfiguredToolRegistryProviderServiceExecutionModel` 与 `ConfiguredToolRegistryProviderServiceExecutionResultModel`，再直接走 `build_configured_tool_registry_provider_preflight_result_model_from_models()`。
- `execute_configured_tool_registry_provider_preflight_model()` 也已切到直接调用 typed `execute_configured_tool_registry_provider_service_execution_model()`；当前 preflight typed 链路已变成 `runtime_artifacts -> runtime_service_actions -> service_execution -> preflight_result` 的连续 model 内部通路，dict 仅保留在 outward 兼容层。
- 顺手补平了一个真实兼容缺口：当 dict `execution_result` 只提供 `trace_write_count/audit_event_count` 时，preflight result 现在会从 `service_execution` 继承 `provider/provider_source_name/runtime_artifacts`，不再要求顶层 dict 再重复一份。

## Latest Sync (2026-05-21)

- `ConfiguredToolRegistryProviderPreflightResult` 的 dict outward bridge 又继续收薄了一步：`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现在只负责最薄的兼容归一化，再直接复用 `build_configured_tool_registry_provider_preflight_result_model()`，不再在这层重复手工 hydration `service_execution_model + execution_result_model`。
- 本轮 focused failing test 锁定了另一个真实兼容场景：若顶层 `preflight_result` 只保留 `trace_write_count/audit_event_count`，而 `provider/provider_source_name/runtime_artifacts` 仅存在于 `service_execution`，dict bridge 仍应成功 hydration 并产出与现有外部契约一致的 summary/result。
- 当前 preflight 这段内部链路已经变成 “typed builder 为主、dict bridge 只保留 outward compatibility shell” 的形态；外部 SSE / trace / e2e 契约继续保持不变。
- 相邻的 `ConfiguredToolRegistryProviderServiceExecutionResult` seam 也已按同样方向继续收口：新增共享 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，把 `trace_write_count/audit_event_count` 的 dict hydration 统一下沉到单点 helper，再让 `build_configured_tool_registry_provider_service_execution_result_model()` 与 `build_configured_tool_registry_provider_preflight_result_model()` 复用。
- 顺手补平了一个最小 payload 兼容缺口：当 dict `execution_result` 为空时，`service_execution_result` 现在会默认回退 `trace_write_count=0`、`audit_event_count=0`，不再要求 outward dict bridge 调用方显式重复零值。
- 相邻的 `ConfiguredToolRegistryProviderPreflightSummary` seam 也已继续收口：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()`，把 summary 这层的 dict bridge 单独抽成 helper，再让 `build_configured_tool_registry_provider_preflight_summary_model()` 直接复用。
- 本轮 focused failing test 锁定了 summary 侧的最小顶层 payload 兼容场景：即使 `preflight_result` 顶层只保留计数，summary bridge 仍应从 `service_execution` 继承 `provider/provider_source_name/runtime_artifacts`，并保持外部 summary 形状不变。
- `ConfiguredToolRegistryProviderPreflightSummary` 与 `ConfiguredToolRegistryProviderPreflightResult` 两条 dict bridge 之间共享的 `service_execution` 归一化也已进一步收口：新增 `build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`，单点承接 provider/provider_source_name 回退与顶层 `runtime_artifacts` 覆盖 merge。
- 本轮 focused failing test 锁定了这层共享归一化的优先级语义：顶层 `runtime_artifacts` 需要覆盖 `service_execution.runtime_artifacts`，但 `service_execution` 自带的 `provider_source_name` 与 action 列表仍应保留。
- 相邻的 execution-result 归一化也已继续收口：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，单点把 `preflight_result` 顶层计数 hydration 与共享 `service_execution` 归一化组合起来，再让 summary/result 两条 dict bridge 复用。
- 本轮 focused failing test 锁定了这层 helper 的兼容语义：在最小顶层 payload 下，它仍应保留 `service_execution` 继承出的 provider/provider_source_name/runtime_artifacts，同时正确携带 `trace_write_count/audit_event_count`。
- `ConfiguredToolRegistryProviderPreflightSummary` 与 `ConfiguredToolRegistryProviderPreflightResult` 共同依赖的 typed pair 也已继续收口：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，统一返回 `service_execution_model + execution_result_model`，再让两条 dict bridge 直接复用。
- 本轮 focused failing test 锁定了这层共享 helper 的组合语义：顶层 `runtime_artifacts` 覆盖 merge、`service_execution` 自带 `provider_source_name` 与 action 列表保留、同时 `execution_result_model` 正确携带计数字段。
- 相邻的 execution-result typed helper 也已继续细化：新增 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，让“已有 `service_execution_model` 时如何补齐 preflight execution-result”成为单点逻辑。
- 本轮 focused failing test 锁定了这层 helper 的兼容语义：它需要保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确携带顶层计数字段。
- 通用 `ConfiguredToolRegistryProviderServiceExecutionResult` 这层也已按同样方向继续统一：新增 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，让“已有 `service_execution_model` 时如何补齐 execution-result”成为共享 typed helper。
- 本轮 focused failing test 锁定了这层通用 helper 的兼容语义：它需要保留传入 `service_execution_model` 的 provider/provider_source_name/runtime_artifacts，并正确携带 `trace_write_count/audit_event_count`。
- `ConfiguredToolRegistryProviderPreflightResult` 这层也已按同样方向继续统一：新增 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，让“已有 `service_execution_model` 时如何补齐 preflight result”成为共享 typed helper 组合入口。
- 本轮 focused failing test 锁定了这层 helper 的兼容语义：它需要保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确产出 summary 与计数字段。
- `ConfiguredToolRegistryProviderPreflightSummary` 这层也已按同样方向补齐对称 typed 入口：新增 `build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()`，让“已有 `service_execution_model` 时如何补齐 preflight summary”成为共享 typed helper 组合入口。
- 本轮 focused failing test 锁定了这层 helper 的兼容语义：它需要保留传入 `service_execution_model` 已经归一化好的 provider/provider_source_name/runtime_artifacts，同时正确产出 summary 中的 `tool_names`、`service_action_kinds` 与计数字段。
- `ConfiguredToolRegistryProviderPreflightResult` 的 dict outward bridge 也已继续压薄：`build_configured_tool_registry_provider_preflight_result_model_from_dict()` 现已直接复用 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`，不再经过共享的 `preflight_execution_models_from_dict()` pair helper。
- 本轮 focused failing test 锁定了这层委托方向：`preflight_result_model_from_dict()` 应直接走 `service_execution_model -> preflight_result typed helper`，同时继续保留既有 summary/计数字段兼容语义。
- `ConfiguredToolRegistryProviderPreflightExecutionModels` 这层 shared pair helper 也已继续压薄：`build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 现已直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()`，不再自己显式串联更深一层的 typed execution-result helper。
- 本轮 focused failing test 锁定了这层 helper 的委托方向：它现在应退化为“共享 service_execution hydration + 现有 dict execution-result helper”的组合壳，而不再携带额外中间逻辑。
- `ConfiguredToolRegistryProviderPreflightExecutionModels` 这层随后又补齐了对称 typed 入口：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，统一承接“已有 `service_execution_model` 时如何补齐 execution-model pair”。
- 本轮 focused failing test 锁定了这层新 helper 的兼容语义：它需要复用传入的 `service_execution_model` 本身，并正确产出带有 `trace_write_count/audit_event_count` 与归一化 runtime artifacts 的 execution-result model。
- `ConfiguredToolRegistryProviderPreflightSummary` 与 `ConfiguredToolRegistryProviderPreflightResult` 这两个 typed 入口随后也已真正切到复用上述 pair helper：`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 与 `...preflight_result_model_from_service_execution_model()` 不再各自平行补 execution-result。
- 本轮 focused failing test 锁定了这层新的生产复用方向：`preflight_result_model_from_service_execution_model()` 现在应直接走 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，从而让 pair helper 真正成为共享单点。
