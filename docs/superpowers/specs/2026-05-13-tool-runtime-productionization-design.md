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

`backend/scripts/test_tool_runtime_slice.py` 当前已扩展到 **253 条测试**，覆盖：

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

## Latest Sync (2026-05-25)

- `ConfiguredToolRegistryProviderPreflightServiceExecutionResult` 这层 outward dict bridge 也已继续压薄：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()`，而不再自己重复做 `service_execution_model` hydration。
- 本轮 focused failing test 锁定了这层委托方向：`preflight_service_execution_result_model_from_dict()` 应直接通过 shared pair helper 取回 execution-result model，从而让 `preflight` 这条 dict bridge 进一步往共享 pair seam 集中。
- `ConfiguredToolRegistryProviderPreflightServiceExecutionResult` 这层 typed wrapper 也已继续压薄：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()`，而不再自己单独走通用 `service_execution_result` helper。
- 本轮 focused failing test 锁定了这层新的 typed 委托方向：`preflight_service_execution_result_model_from_service_execution_model()` 应直接通过 shared pair helper 取回 execution-result model，从而让 `preflight` 这条 typed seam 进一步往共享单点集中。
- `ConfiguredToolRegistryProviderPreflightSummary` 这层 typed 入口也已继续压薄：`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，而不再自己展开 shared execution-model pair helper。
- 本轮 focused failing test 锁定了这层新的 summary 委托方向：`preflight_summary_model_from_service_execution_model()` 应直接通过对称的 service-execution-result helper 取回 execution-result model，从而让 `preflight` 这条 summary/result typed seam 继续往共享单点集中。
- `ConfiguredToolRegistryProviderPreflightResult` 这层 typed 入口也已继续压薄：`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，而不再自己展开 shared execution-model pair helper。
- 本轮 focused failing test 锁定了这层新的 result 委托方向：`preflight_result_model_from_service_execution_model()` 应直接通过对称的 service-execution-result helper 取回 execution-result model，从而让 `preflight` 这条 summary/result typed seam 继续往共享单点集中。
- `ConfiguredToolRegistryProviderPreflightExecutionModels` 这层 shared pair helper 也已继续压薄：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 现在会直接复用 `build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`，而 `preflight_service_execution_result_model_from_service_execution_model()` 则直接走通用 `service_execution_result` helper。
- 本轮新增 focused failing test 锁定了这层新的 pair-helper 委托方向：`preflight_execution_models_from_service_execution_model()` 应退回为“返回传入 service_execution + 现成 execution-result model”的组合壳，从而让 shared pair seam 不再承担额外的 execution-result 生产职责。
- dict 侧的 `ConfiguredToolRegistryProviderPreflightServiceExecutionResult` / `ConfiguredToolRegistryProviderPreflightExecutionModels` 也已继续压薄：`preflight_service_execution_result_model_from_dict()` 现在会直接走通用 `service_execution_result` helper，而 `preflight_execution_models_from_dict()` 则直接复用前者。
- 本轮把两条既有 focused seam test 改成新的 dict 委托方向，并先看红灯再转绿，锁定 dict 侧也应退回为“共享 service_execution hydration + 现成 execution-result model”的组合壳。
- dict outward 的 `ConfiguredToolRegistryProviderPreflightSummary` / `ConfiguredToolRegistryProviderPreflightResult` 这两个入口也已继续集中到 `preflight_execution_models_from_dict()`：它们现在会直接消费这层组合壳返回的 typed pair，而不再各自重复做 `service_execution` hydration。
- 本轮新增一条 focused failing test，并把既有 `preflight_result_model_from_dict()` seam test 改成新的 pair-helper 委托方向，进一步锁定 dict outward 入口应共同复用同一条 typed pair seam。
- `ConfiguredToolRegistryProviderPreflightServiceExecutionPayload` 这一层也已明确收口成单点 normalization seam：新增 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，统一负责 provider/provider_source_name/runtime_artifacts merge 与缺省值补齐。
- 本轮新增 focused failing test，锁定 `preflight_service_execution_model_from_dict()` 应直接复用这层 payload helper；并把 dict result/pair 两条既有 seam test 进一步收紧为“共享同一份 normalized payload + 单次 typed hydration”方向。
- `ConfiguredToolRegistryProviderPreflightExecutionModelsFromServiceExecutionPayload` 这层也已补成单点 typed-pair seam：新增 `build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()`，统一负责 “normalized payload -> service_execution_model + execution_result_model” 的单次 hydration。
- 本轮把 `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_execution_models_from_dict()` 三条既有 seam test 一起改成锁这层新 helper，从而让 dict inward bridge 明确分成 “payload normalization” 与 “typed pair hydration” 两段。
- `ConfiguredToolRegistryProviderPreflightServiceExecutionModel/Result` 这两个 dict helper 现在也进一步退回为兼容壳：它们会直接从 `build_configured_tool_registry_provider_preflight_execution_models_from_dict()` 取第一/第二个 model，而不再各自直接触碰 payload-to-pair helper。
- 本轮把两条既有 seam test 改成锁这层新的 dict 单点委托方向，从而让 `preflight_execution_models_from_dict()` 更明确地成为 dict inward 的公开主入口。
- `ConfiguredToolRegistryProviderPreflightModels` 这层 total-model seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_models_from_dict()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()`，统一返回 `service_execution_model + execution_result_model + summary_model + result_model`。
- 本轮把 `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_summary_model_from_dict()`、`preflight_result_model_from_dict()` 以及 typed 侧 `preflight_summary/result_model_from_service_execution_model()` 的既有 seam test 一起抬高到锁这层 total-model helper，从而让 outward dict/typed 入口都退回成“取对应 model”的兼容壳。
- `ConfiguredToolRegistryProviderPreflightModelsFromModels` 这层 pair-to-total seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_models_from_models()`，统一负责 `service_execution_model + execution_result_model -> summary_model + result_model`。
- 本轮把 `preflight_execution_models_from_dict()` 的既有 seam test 改成锁这层 total-model 壳方向，同时新增 `preflight_models_from_models()` / `preflight_result_model_from_models()` focused 用例，从而让 dict pair helper 与 result-from-models 这两层都退回成更薄的组合壳。
- `ConfiguredToolRegistryProviderPreflightModelsFromServiceExecutionPayload` 这层 dict payload-to-total seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()`，统一负责 normalized payload 直接派生 `service_execution_model + execution_result_model + summary_model + result_model`。
- 本轮把 `preflight_execution_models_from_dict()` 的 seam test 继续抬高到锁这层 payload-total helper，同时把 typed 侧 `preflight_execution_models_from_service_execution_model()` 改成 total-model 壳方向，从而让 dict/typed 两侧 pair helper 都退回为“只取前两个 model”的兼容层。
- `ConfiguredToolRegistryProviderPreflightExecutionModelsFromServiceExecutionPayload` 这层 payload pair helper 也已进一步退回 total-model 壳：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 取前两个 model。
- 本轮新增 focused failing test 锁定这层 payload pair helper 的新委托方向，并让 `preflight_models_from_service_execution_payload()` 自己直接完成 `service_execution_model` hydration、`execution_result_model` 派生与 total-model 组装，从而把 dict inward 的公开重心进一步集中到 payload-total seam。
- `ConfiguredToolRegistryProviderPreflightServiceExecutionResultFromServiceExecutionModel` 这层 typed result helper 也已进一步退回 total-model 壳：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 取第二个 model。
- 本轮把两条既有 focused seam test 改成新的 typed 委托方向，并让 `preflight_models_from_service_execution_model()` 自己直接走通用 `service_execution_result` helper 完成 execution-result 派生，从而把 typed inward 的公开重心进一步集中到 `service_execution_model -> total models`。
- `ConfiguredToolRegistryProviderPreflightSummaryFromModels/ResultModel` 这条 summary seam 也已进一步退回 total-model 壳：`build_configured_tool_registry_provider_preflight_summary_model_from_models()` 现在会直接从 `build_configured_tool_registry_provider_preflight_models_from_models()` 取第三个 model，而 `build_configured_tool_registry_provider_preflight_summary_model_from_result_model()` 则直接返回已有 `result.summary`。
- 本轮新增 focused failing test 锁定这两层新的 summary 委托方向，并让 `preflight_models_from_models()` 自己直接走 `preflight_summary_model_from_parts()` 组装 summary，再组合 result model，从而把 summary/result 组装权进一步集中到 total-model seam。
- `ConfiguredToolRegistryProviderPreflightModels` 这层高层 raw-input / execute seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_models()` 与 `execute_configured_tool_registry_provider_preflight_models()`，分别统一负责 `service_execution + execution_result` 以及 runtime execute 路径到 total models 的总装。
- 本轮新增 focused failing test 锁定 `build_preflight_result_model()` 与 `execute_preflight_model()` 都应直接复用这两层高层 total-model helper，从而把高层 hydration/执行后组装权进一步集中到单点。
- `ConfiguredToolRegistryProviderPreflightDicts` 这层最外侧 outward seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_dicts_from_models()`、`build_configured_tool_registry_provider_preflight_dicts()` 与 `execute_configured_tool_registry_provider_preflight_dicts()`，统一负责 `summary_dict + result_dict` 的最终 outward 组装。
- 本轮新增 focused failing tests 锁定 `build_preflight_summary()`、`build_preflight_result()`、`execute_preflight()` 都应直接复用这层 outward dict helper，从而把最外层 dict 组装权也集中到单点，并将 focused 基线推进到 `256` 条。
- `ConfiguredToolRegistryProviderPreflightOutputs` 这层高层 outward seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_models()`、`build_configured_tool_registry_provider_preflight_outputs()` 与 `execute_configured_tool_registry_provider_preflight_outputs()`，统一负责 `service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- 本轮新增 focused failing tests 锁定 `build_preflight_result_model()`、`build_preflight_result()`、`build_preflight_result_model_from_service_execution_model()`、`build_preflight_summary_model_from_service_execution_model()`、`execute_preflight_model()` 与 `execute_preflight()` 都应直接复用这层 `outputs` helper，从而把高层 outward model/dict 组装权继续集中到单点，并将 focused 基线推进到 `257` 条。
- `ConfiguredToolRegistryProviderPreflightOutputsFromDict` 这层单参 dict seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_dict()`，统一负责 `preflight_result -> service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- 本轮把 `preflight_service_execution_model_from_dict()`、`preflight_service_execution_result_model_from_dict()`、`preflight_models_from_dict()`、`preflight_summary_model_from_dict()`、`preflight_result_model_from_dict()`、`preflight_dicts()` 与 `preflight_summary()` 的 focused seam tests 一起抬高到锁这层 `outputs_from_dict()`，从而把单参 dict 兼容链也集中到单点，同时维持 focused 基线 `257` 条不回退。
- `ConfiguredToolRegistryProviderPreflightOutputs` 这层现在也已承接 `service_execution_payload + preflight_result` 路径：`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_payload()` 都已退回为从 `build_configured_tool_registry_provider_preflight_outputs()` 取对应 typed 结果的兼容壳。
- 本轮把这两条 payload typed 入口的 focused seam tests 一起抬高到锁 `outputs(service_execution, execution_result)`，从而让 payload 路径也不再重复做 payload -> typed hydration / summary/result 组装，同时维持 focused 基线 `257` 条不回退。
- `ConfiguredToolRegistryProviderPreflightOutputsFromServiceExecutionPayload` 这层 payload total-output seam 也已补成单点：新增 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()`，统一负责 `service_execution_payload + execution_result -> service_execution_model + execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- 本轮把 `preflight_execution_models_from_service_execution_payload()`、`preflight_models_from_service_execution_payload()` 与高层 `build_preflight_outputs()` 的 focused seam tests 一起抬高到锁这层 payload-output helper，从而把 payload total-output 组装权继续集中到单点，并将 focused 基线推进到 `258` 条。
- `ConfiguredToolRegistryProviderPreflightOutputsFromServiceExecutionModel` 这层 typed total-output seam 现在也已承接 `service_execution_model + preflight_result` 路径：`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model()`、`build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model()` 与 `build_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 都已退回为从 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 取对应 typed 结果的兼容壳。
- 本轮把这三条 typed 入口的 focused seam tests 一起抬高到锁 `outputs_from_service_execution_model()`，并新增 keep-fields coverage，从而把 typed total-output 组装权也继续集中到单点，并将 focused 基线推进到 `259` 条。
- `ConfiguredToolRegistryProviderPreflightOutputsFromDict` 这层单参 dict total-output 总出口现在也继续并回到了更高层 `build_configured_tool_registry_provider_preflight_outputs(service_execution, execution_result)`：`build_configured_tool_registry_provider_preflight_outputs_from_dict()` 已退回为只负责提取兼容 `service_execution` payload 再调用高层 outputs helper 的薄壳。
- 本轮补了 `outputs_from_dict()` 的 keep-fields / seam coverage，并把 focused 基线推进到 `261` 条，从而把单参 dict total-output 总装权进一步收敛到高层 `outputs()` 入口。
- `ConfiguredToolRegistryProviderPreflightOutputs` 这层高层 total-output seam 现在也真正承接了 `service_execution_payload + execution_result` 路径：`build_configured_tool_registry_provider_preflight_outputs()` 已改为自己完成 `service_execution` hydration，再直接复用 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`。
- 相应地，`build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` 已退回为从高层 `outputs()` 取总装结果的兼容壳；本轮补了 `outputs()` / `outputs_from_service_execution_payload()` 的 focused seam coverage，并把 focused 基线推进到 `263` 条。
- Execute 侧现在也补齐了对称的 typed total-output seam：新增 `execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()`，统一负责 `service_execution_model + trace_steps/persist/audit -> execution_result_model + summary_model + result_model + summary_dict + result_dict` 的总装。
- 相应地，`execute_configured_tool_registry_provider_preflight_outputs()` 已退回为只负责构造 `service_execution_model` 再委托给这层 typed execute helper；本轮补了 execute 侧的 keep-fields / seam coverage，并把 focused 基线推进到 `265` 条。
- 最外层 summary/result wrapper 这批 outward 入口现在也进一步退回到了最近邻 helper：`build_preflight_summary()` 直接复用 `build_preflight_dicts()`，`build/execute preflight *_model()` 优先复用对应 `models()` helper，`build_preflight_result()` / `execute_preflight_model()` / `execute_preflight()` 也分别退回为复用 `result_model()`、`execute_preflight_models()`、`execute_preflight_dicts()` 的兼容壳。
- 这样 outward wrapper 不再平行直连更深的 `outputs()` seam，层级职责更集中；本轮通过改严既有 seam tests 完成收口，focused 基线维持 `265` 条不回退。
- `service_execution/execution_models` 这组 wrapper 现在也进一步退回到了最近邻 helper：`build_preflight_service_execution_model_from_dict()` 与 `build_preflight_service_execution_result_model_from_dict()` 直接复用 `build_preflight_execution_models_from_dict()`，typed `...service_execution_result_model_from_service_execution_model()` 复用 `...execution_models_from_service_execution_model()`，而 `execution_models_from_service_execution_payload()` / `...from_service_execution_model()` 也都退回为从对应 `models()` helper 取前两个结果。
- 进一步地，`build_preflight_models()`、`...models_from_service_execution_payload()`、`...models_from_dict()` 与 typed `...models_from_service_execution_model()` 现在也都直接走 `models_from_models()` 主链，不再先穿过 `outputs()` 再回到 typed preflight models。
- 这样 `service_execution/execution_models` 与 `models` 这两层 wrapper 都不再平行直连更深的 `outputs()` seam；本轮同样通过改严既有 seam tests 完成收口，并把 focused 基线推进到 `267` 条。
- `dicts` 这一层 outward wrapper 现在也进一步退回到了最近邻 `models()` helper：`build_preflight_dicts_from_models()` 直接复用 `build_preflight_models_from_models()` 再做 `to_dict()`，`build_preflight_dicts()` 直接复用 `build_preflight_models_from_dict()`，而 `execute_preflight_dicts()` 直接复用 `execute_preflight_models()` 后统一走 `dicts_from_models()`。
- 这样 `dicts` 这一层也不再平行直连更深的 `outputs()` seam，summary/result 的字典投影职责被压回到 typed `models` 主链之上；本轮新增三条 focused seam tests 后把基线推进到 `270` 条。
- `outputs` 这一组 build/execute wrapper 现在也进一步退回到了 `models + dict projection` 主链：build 侧 `build_preflight_outputs()` / `...from_service_execution_payload()` / `...from_service_execution_model()` / `...from_dict()` 都先走各自最近邻的 `models` helper，再统一通过共享的 `outputs_from_resolved_models()` 做 dict 投影。
- execute 侧也补齐了对称的 typed seam：新增 `execute_configured_tool_registry_provider_preflight_models_from_service_execution_model()`，并让 `execute_preflight_outputs_from_service_execution_model()` 与 `execute_preflight_outputs()` 都退回到 `execute_models` 主链之后再统一做 dict 投影；本轮新增五条 focused seam tests 后把基线推进到 `272` 条。
- `service_execution` 内核层这轮也去掉了两处显式的 model/dict 往返：新增 `build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model()`，让 `build_service_execution_model()` 直接从 typed `runtime_artifacts` 派生 typed `service_actions`；同时 `execute_service_execution_model()` 现在直接把 `service_execution.service_actions` 组装成 typed actions model 再执行。
- 这样这两条 build/execute 内部链不再分别绕 `runtime_artifacts.to_dict()` 与 `[action.to_dict()] -> execute_*_result_model()`，typed internal 主链又向内收了一层；本轮新增两条 focused seam tests 后把基线推进到 `274` 条。
- 相邻的 `service_execution result + dict` 这一层这轮也开始按同样模式补成 `outputs` 单点：新增 `build_service_execution_outputs()`、`...outputs_from_service_execution_model()`、`...outputs_from_models()` 与 `execute_service_execution_outputs()`、`...outputs_from_service_execution_model()`。
- 这样 build/execute 两侧都可以先统一走 `service_execution outputs` seam，再按需取 typed result model 或 dict；`build_service_execution_result_model()`、`...from_service_execution_model()` 与 `execute_service_execution()` 不再各自平行组装 result+dict，本轮新增三条 focused seam tests 后把基线推进到 `277` 条。
- `runtime_service_actions` 这一层这轮也继续按同样模式补成 `outputs` 单点：新增 `build_runtime_service_actions_outputs()`、`...outputs_from_runtime_artifacts_model()`、`...outputs_from_models()` 与 `execute_runtime_service_actions_outputs()`、`...outputs_from_models()`。
- 这样 build/execute 两侧都可以先统一走 `runtime_service_actions outputs` seam，再按需取 typed actions/result model 或 dict；`build_runtime_service_actions()`、`build_runtime_service_actions_model()`、`execute_runtime_service_actions()`、`execute_runtime_service_actions_result_model()` 不再各自平行组装，而 `build_service_execution_model()` 与 `execute_service_execution_model()` 也同步退回到这层最近邻 helper。本轮新增七条 focused seam / keep-fields tests 后把基线推进到 `284` 条。
- `runtime_service_actions` 这一层这轮继续把 typed-from-artifacts 和 dict-from-dicts 两条入口也收回到最近邻 `outputs` seam：新增 `build_runtime_service_actions_outputs_from_dicts()`。
- 这样 `build_runtime_service_actions_model_from_runtime_artifacts_model()`、`build_runtime_service_actions_model_from_dicts()`、`build_service_execution_model_from_dict()`、`execute_runtime_service_actions_outputs()` 也都退回为从 `...outputs_from_runtime_artifacts_model()` / `...outputs_from_dicts()` 取 typed model 或 dict，不再额外保留平行的组装逻辑。本轮新增四条 focused seam / keep-fields tests 后把基线推进到 `288` 条。
- `runtime_service_actions result` 这一支这轮也补成了对称的 build-side `outputs` seam：新增 `build_runtime_service_actions_result_outputs_from_models()` 与 `...outputs_from_dict()`。
- 这样 `build_runtime_service_actions_result_model_from_dict()` 不再自己做 dict→typed count hydration，而是退回为从这层 `result outputs` seam 取 typed result model；同时 `build_service_execution_outputs_from_service_execution_model()` 也同步退回为先走这层 seam，再统一进入 `service_execution outputs` 主链。本轮新增四条 focused seam / keep-fields tests 后把基线推进到 `292` 条。
- `preflight` 这边 build-side 的 `service_execution_result` 兼容入口这轮也一起并回了 `service_execution outputs` 主链。
- 这样 `build_preflight_service_execution_result_model_from_dict()` 不再通过 `preflight_execution_models_from_dict()` 间接拿结果，而是先走 `build_preflight_service_execution_payload_from_dict()` 再直接复用 `build_service_execution_outputs()`；`build_preflight_service_execution_result_model_from_service_execution_model()` 也同步退回为直接复用 `build_service_execution_outputs_from_service_execution_model()`。本轮通过改严两条既有 seam tests 完成收口，focused 基线维持 `292` 条。
- 最新一轮补充后，build-side `preflight execution_models / models` 也已经明确统一到 `service_execution outputs` 主链：`dict` / `payload` / typed `service_execution_model` 三条入口都先单次完成 `service_execution_model` hydration 或直接复用既有 typed model，再统一通过 `service_execution outputs` 产出 typed `execution_result_model`，最后只由 `preflight_models_from_models()` 负责 `summary/result` 总装。
- 再往上一层，raw `service_execution + execution_result` 入口也已经退回到 payload seam：raw wrapper 只保留参数命名兼容，真正的 build-side 总装边界现在稳定地落在 `...from_service_execution_payload()` 与其下方的 `service_execution outputs` 主链。
- 在 outward dict 层，build/execute 两侧现在也都进一步统一到 `outputs` seam：`summary/result dict` 的导出不再先走 typed `models` 再二次 `to_dict()`，而是直接从最近邻 `outputs` helper 取最后两个 dict。
- 在 outward model 层，这轮也继续统一到 `outputs` seam：`build_preflight_summary_model_from_dict()`、`build_preflight_result_model_from_dict()`、typed `...from_service_execution_model()`，以及 `execute_preflight_model()` 现在都直接从对应 `outputs` helper 取 typed `summary/result` model，不再平行依赖更深一层的 `models` / `execute_models` seam。
- 在 `outputs` wrapper 自身这一层，这轮也继续收口到更少的公开边界：raw / payload / dict 三条 build-side 入口现在都统一先落到 typed `service_execution_model` 再复用 `...outputs_from_service_execution_model()`，而 build/execute 的 typed `outputs_from_service_execution_model()` 则统一退回为从 `build_preflight_outputs_from_models()` 取总装结果。
- 在 `...from_models()` 这组 outward wrapper 上，这轮也继续收口到 `outputs_from_models`：`build_preflight_dicts_from_models()`、`build_preflight_summary_model_from_models()`、`build_preflight_result_model_from_models()` 与 raw `build_preflight_result_model()` 现在都直接从最近邻 `outputs` seam 取 outward dict / typed result，不再平行依赖更深的 `models` seam。
- 在 `preflight models_from_dict / ...payload / ...service_execution_model` 这组 typed 总装入口上，这轮也继续收口到 `preflight_execution_models_*`：三条 `models_from_*` helper 现在都先复用对应的 execution-model pair helper，再统一进入 `build_preflight_models_from_models()`，避免再次重复 `service_execution outputs` hydration。
- 在 dict/typed `service_execution_model/result_model` 这组 wrapper 上，这轮也继续收口到 `preflight_execution_models_*`：dict path 的 typed pair 装配现在优先统一落到 `preflight_execution_models_from_service_execution_payload()`，typed path 的 result wrapper 则统一落到 `preflight_execution_models_from_service_execution_model()`。
- 在 `preflight_execution_models_from_service_execution_payload()` 这一层，这轮也继续收口到 typed helper：payload seam 现在先 hydrate typed `service_execution_model`，再统一复用 `preflight_execution_models_from_service_execution_model()`，避免继续平行持有一条 raw `service_execution_outputs` 委托路径。
- 在 typed `preflight_execution_models_from_service_execution_model()` 这一层，这轮也继续收口到通用 `service_execution_result_model_from_service_execution_model()`：typed path 现在统一先拿到通用 typed result model，再按需组装 `preflight` pair，不再平行保留 outputs-level 委托链。
- 最新一轮继续把这段残留 wrapper 成片并回 `outputs_from_*` seam：`build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()`、`...service_execution_result_model_from_dict()`、`...execution_models_from_dict()` 与 `...models_from_dict()` 现在都直接从 `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 取对应 typed 结果。
- 同时，payload / typed 两侧的 `execution_models`、`models` 与 typed `service_execution_result_model` wrapper 也同步退回到了最近邻 `build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload()` / `...outputs_from_service_execution_model()`，不再分散依赖旧的 `preflight_execution_models_*` 或 generic typed seam。
- 这样 `preflight` 这段当前更接近阶段性最终边界：`payload normalization -> service_execution outputs -> preflight outputs_from_models` 负责真实总装，其余 dict/payload/typed outward wrapper 基本都只保留“取对应 typed result / dict”的兼容壳职责。
- execute 侧的 `preflight models` 平行总装链随后也已一起并回 `execute_preflight_outputs*`：`execute_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 现在直接从 `...outputs_from_service_execution_model()` 取前四个 typed 结果，`execute_configured_tool_registry_provider_preflight_models()` 则直接从 `execute_configured_tool_registry_provider_preflight_outputs()` 取值。
- 这样 build / execute 两侧在 `preflight` 这段更加对称：`outputs*` 成为最近邻 total-output seam，而 `models` / `execution_models` 这批 outward wrapper 继续退回成“从 total-output seam 取前若干结果”的兼容壳。
- `service_execution` execute 侧随后也已补成与 build 侧对称的共享总装 seam：`execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 现在先执行 typed `runtime_service_actions_outputs_from_models()`，再统一复用 `build_configured_tool_registry_provider_service_execution_outputs_from_models()` 组装 typed result+dict。
- 相应地，`execute_configured_tool_registry_provider_service_execution_model()` 也退回为直接从这层 `outputs_from_service_execution_model()` 取 result model；这样 execute 侧不再平行保留“runtime actions execute -> result_model”和“runtime actions execute -> outputs”两条逻辑几乎相同的总装链。
- execute-side 的 `preflight outputs_from_service_execution_model()` 随后也已补齐到同一层最近邻 seam：它现在直接复用 `execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 取 typed `execution_result_model`，不再平行直连 `execute_configured_tool_registry_provider_service_execution_model()`。
- 这样 execute 侧 `preflight` 这段与 build 侧更加对称：两边都会先通过 `service_execution outputs` seam 归一化出 typed `execution_result_model`，再统一进入 `preflight outputs_from_models()` 补齐 summary/result。
- 更内层的 `runtime_service_actions / service_execution` 这段随后也继续收口了三条还直接切 `outputs()[0]` 的链：`build_configured_tool_registry_provider_service_execution_model_from_dict()`、`build_configured_tool_registry_provider_service_execution_model()` 与 `execute_configured_tool_registry_provider_runtime_service_actions_outputs()` 现在都直接复用最近邻 `*_model_*` helper，而不再自己从 `outputs_*()[0]` 取 model。
- 这样这三条链的职责更清晰：`*_outputs*` 继续负责 total output，`*_model_*` 负责 typed model，而上层 wrapper 只依赖最近邻 seam，不再跨层切 total-output helper 的第一个返回值。
- 更靠内层的 raw build/result seam 这轮也继续做了同样的“最近邻 typed model”收口：`build_configured_tool_registry_provider_runtime_service_actions_outputs()` 现在先把 raw `runtime_artifacts` hydrate 成 typed `ConfiguredToolRegistryProviderRuntimeArtifactsModel`，再统一复用 `...outputs_from_runtime_artifacts_model()`。
- 同时，`build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 改为直接复用 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，`execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 改为直接复用 `execute_configured_tool_registry_provider_runtime_service_actions_model()`；也就是说，这两条 `service_execution` result 链不再为“只需要 typed result model”额外绕经 runtime-action `outputs` helper。
- 在 `*_result_model` 这组 wrapper 上，这轮也进一步把“先走 outputs 再拆 model”收掉了：`build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()` 现在直接复用 `build_configured_tool_registry_provider_runtime_service_actions_result_model()`。
- 同时，`build_configured_tool_registry_provider_service_execution_result_model()` 改为先 hydrate typed `service_execution_model` 再复用 `...service_execution_result_model_from_service_execution_model()`；后者直接组合 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()` 与 `build_configured_tool_registry_provider_service_execution_result_model_from_models()`。`execute_configured_tool_registry_provider_service_execution_model()` 也同步改为直接组合 `execute_configured_tool_registry_provider_runtime_service_actions_model()` 与 `build_configured_tool_registry_provider_service_execution_result_model_from_models()`，从而把 `*_result_model` wrapper 的职责压回 typed result seam。
- raw dict `outputs` wrapper 这一批这轮也继续做了同样的收口：`build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict()` 现在直接复用 `build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict()`，而 `execute_configured_tool_registry_provider_runtime_service_actions()` 直接复用 `execute_configured_tool_registry_provider_runtime_service_actions_result_model()`。
- 同时，`build_configured_tool_registry_provider_service_execution_outputs()` 直接复用 `build_configured_tool_registry_provider_service_execution_result_model()`，`execute_configured_tool_registry_provider_service_execution()` 与 `execute_configured_tool_registry_provider_service_execution_outputs()` 则都直接复用 `execute_configured_tool_registry_provider_service_execution_model()`；也就是说，这批 raw wrapper 现在只保留 typed hydration 与 `to_dict()` 职责，不再平行持有额外总装链。
- `preflight` 最外层 raw wrapper 这轮也继续做了同样的收口：`build_configured_tool_registry_provider_preflight_summary()` 现在直接复用 `build_configured_tool_registry_provider_preflight_summary_model_from_dict()`，`build_configured_tool_registry_provider_preflight_result()` 则直接复用 `build_configured_tool_registry_provider_preflight_result_model()`。
- 同时，`build_configured_tool_registry_provider_preflight_dicts()` 改为直接从 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 取 `summary/result` dict，`execute_configured_tool_registry_provider_preflight()` 与 `execute_configured_tool_registry_provider_preflight_dicts()` 则都直接复用 `execute_configured_tool_registry_provider_preflight_model()`；这样 `preflight` 最外层入口现在也退回到了最薄的 `to_dict()` 投影职责，不再平行持有额外 `outputs` 总装链。
- 最新一轮继续把 `preflight` 剩下的 typed `summary/result model` wrapper 也收回到了更直接的 typed seam：`build_configured_tool_registry_provider_preflight_summary_model_from_dict()`、`...from_service_execution_model()`、`...from_models()` 现在都直接复用对应 `result_model` helper 再取 `summary`。
- 同时，`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 改为先通过通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()` 归一化出 typed `execution_result_model`，再统一进入 `build_configured_tool_registry_provider_preflight_result_model_from_models()`；后者与 `build_configured_tool_registry_provider_preflight_result_model_from_dict()` 也分别退回到了 `build_configured_tool_registry_provider_preflight_models_from_models()` 和 `build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()`。
- 这样 `preflight` 这段现在更接近阶段性最终边界：`outputs*` 负责 total-output，`result_model/models` 负责 typed `summary/result` 组装，而这批 wrapper 只保留最近邻取值兼容壳职责。
- 最新一轮又把 execute-side 的 `preflight models/model` wrapper 收回到了更直接的 typed seam：`execute_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 现在先统一复用 `execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 拿到 typed `execution_result_model`，再进入 `build_configured_tool_registry_provider_preflight_models_from_models()`。
- 相应地，`execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model()` 不再自己平行做 execute-side preflight 总装，而是从这条 `models` helper 取 resolved models 再统一走 `build_configured_tool_registry_provider_preflight_outputs_from_resolved_models()`；`execute_configured_tool_registry_provider_preflight_models()` 与 `execute_configured_tool_registry_provider_preflight_model()` 也同步退回为最近邻 typed helper 的兼容壳。
- 这样 build / execute 两侧在 `preflight` 这段的最终边界更一致：`service_execution outputs` 负责 execute/build 侧 typed `execution_result`，`preflight models_from_models` 负责 typed `summary/result`，`outputs*` 只负责 outward dict 投影。
- 最新一轮又把 build-side 的 `preflight service_execution_model/result_model/execution_models/models` wrapper 成片收回到了更直接的 typed seam：`build_configured_tool_registry_provider_preflight_service_execution_model_from_dict()` 现在先统一复用 `build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict()`，再进入通用 `build_configured_tool_registry_provider_service_execution_model_from_dict()`。
- 相应地，`build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict()` 与 typed `...from_service_execution_model()` 现在都统一退回到通用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`；三条 `build_configured_tool_registry_provider_preflight_execution_models_from_*()` 则统一只保留“拿 typed pair”的职责。
- 再往上一层，三条 `build_configured_tool_registry_provider_preflight_models_from_dict()/...from_service_execution_payload()/...from_service_execution_model()` 也都统一退回到“先复用 execution-model pair，再进入 `build_configured_tool_registry_provider_preflight_models_from_models()`”；这样 build-side `preflight` 这段不再继续从 `outputs` seam 反向拆 typed 结果，内部边界进一步稳定在 `payload normalization -> service_execution_result_model -> preflight_models_from_models` 主链。
- 最新一轮又把 build-side 的 `preflight summary/result/dicts` wrapper 成片收回到了 `preflight_models_*` 主链：`build_configured_tool_registry_provider_preflight_summary_model_from_dict()/...from_service_execution_model()/...from_models()` 现在都直接从对应 `preflight_models_*` helper 取第三个 `summary_model`，不再分别绕 `result_model` helper。
- 同时，`build_configured_tool_registry_provider_preflight_result_model()`、`...result_model_from_service_execution_model()`、`...result_model_from_dict()` 与 `build_configured_tool_registry_provider_preflight_dicts()` 也都统一改成从 `preflight_models_*` helper 取第四个 `result_model` 或最后两个 dict，不再平行绕 `outputs` seam 或通用 `service_execution_result_model` seam。
- 这样 build-side `preflight` 这段当前更接近阶段性最终边界：`payload normalization -> execution_models -> preflight_models_from_models` 负责 typed 总装，summary/result/dicts outward wrapper 只保留最近邻取值与 `to_dict()` 的兼容壳职责。
- 最新一轮又把 build-side 的 `preflight outputs*` wrapper 成片收回到了 `preflight_models_* + outputs_from_resolved_models()` 主链：`build_configured_tool_registry_provider_preflight_outputs()`、`...outputs_from_service_execution_payload()`、`...outputs_from_service_execution_model()` 与 `...outputs_from_dict()` 现在都先复用对应 `preflight_models_*` helper 拿到 typed `service_execution/execution_result/summary/result`。
- 然后这四条 `outputs*` wrapper 统一只保留一层 `build_configured_tool_registry_provider_preflight_outputs_from_resolved_models()` dict 投影，不再平行绕 `service_execution_outputs` seam 或更高层 `outputs` wrapper。
- 这样 build-side `preflight` 这段的边界又收紧了一层：typed 总装稳定在 `payload normalization -> execution_models -> preflight_models_from_models` 主链，而 `outputs*` wrapper 现在也退回到了纯 outward dict 兼容壳职责。
- 最新一轮又把 execute-side 的 `preflight outputs/dicts` wrapper 成片收回到了 `execute_preflight_models*` 主链：`execute_configured_tool_registry_provider_preflight_outputs()` 现在先复用 `execute_configured_tool_registry_provider_preflight_models()` 拿到 typed `service_execution/execution_result/summary/result`，再统一进入 `build_configured_tool_registry_provider_preflight_outputs_from_resolved_models()` 做 dict 投影。
- 同时，`execute_configured_tool_registry_provider_preflight_dicts()` 也改成直接从 `execute_preflight_models()` 取 `summary_model/result_model` 再做 `to_dict()`，不再平行绕 `execute_preflight_model()`。
- 这样 execute-side `preflight` 这段也进一步拉直到和 build-side 更接近的边界：`execute_preflight_models*` 负责 typed 总装，`outputs/dicts` wrapper 只保留 outward dict 兼容壳职责。
- 最新一轮又把 execute-side 的 typed `execution_result_model` 获取路径再拉直了一层：`execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 现在直接复用 `execute_configured_tool_registry_provider_service_execution_model()`，不再中间绕一层 `build_configured_tool_registry_provider_service_execution_outputs_from_models()`。
- 同时，`execute_configured_tool_registry_provider_preflight_models_from_service_execution_model()` 也同步直接复用 `execute_configured_tool_registry_provider_service_execution_model()`，再统一进入 `build_configured_tool_registry_provider_preflight_models_from_models()`；这样 execute-side `service_execution -> preflight` typed seam 更接近 build-side 当前稳定下来的 `service_execution_result_model -> preflight_models_from_models` 边界。
- 最新一轮又把 `runtime_service_actions` 这组 raw build/execute wrapper 收回到了更直接的 `model/result_model` seam：`build_configured_tool_registry_provider_runtime_service_actions()` 现在直接复用 `build_configured_tool_registry_provider_runtime_service_actions_model()`，后者统一先 hydrate typed `runtime_artifacts_model` 再进入 `...model_from_runtime_artifacts_model()`。
- 同时，`build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model()` 与 `...outputs_from_dicts()` 也都退回成“model helper + to_dict()”的 outward 薄壳；`execute_configured_tool_registry_provider_runtime_service_actions_outputs()` 则直接复用 `execute_configured_tool_registry_provider_runtime_service_actions_result_model()`，而 `execute_configured_tool_registry_provider_runtime_service_actions_model()` 则直接复用 `...result_model_from_models()`。这样 `runtime_service_actions` 这段的 raw outward 与 typed inward 边界都进一步拉直，不再为了拿 typed model 或 result 中间绕经 `outputs`。
- 最新一轮又把 build-side `service_execution/preflight` 这条最近邻 typed seam 再拉直了一层：`build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model()` 现在直接复用 `build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model()`，不再自己平行组装 runtime-result model 再走 outputs seam。
- 同时，`build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model()` 也改成先统一拿到 typed `service_execution_result_model`，再进入 `build_configured_tool_registry_provider_preflight_result_model_from_models()`；`build_configured_tool_registry_provider_preflight_summary_model_from_service_execution_model()` 则直接复用这条 `preflight_result_model` seam。这样 build-side `service_execution -> preflight` 当前也更接近 execute-side 已经稳定下来的“result-model 主链 + outward 兼容壳”边界。
- 最新一轮又把 build-side 两参 `preflight` raw wrapper 成片收回到了单参 `preflight_result dict` seam：新增 `build_configured_tool_registry_provider_preflight_result_payload()` 之后，`build_configured_tool_registry_provider_preflight_models()`、`...outputs()`、`...outputs_from_service_execution_payload()`、`...result_model()` 与 `...result()` 现在都统一先合成 outward `preflight_result` payload。
- 相应地，这批 raw wrapper 随后都直接复用对应的 `build_configured_tool_registry_provider_preflight_*_from_dict()` helper，不再平行保留一组“`service_execution + execution_result` 自己再拆 typed `execution_result/summary/result`”的链路；这进一步把 build-side raw 边界压回到了 `payload -> from_dict -> typed seam` 的单点入口。
- 最新一轮又把 build/execute 最外层 `preflight` dict outward wrapper 收回到了 `dicts` / `outputs_from_dict` seam：`build_configured_tool_registry_provider_preflight_summary()` 现在直接复用 `build_configured_tool_registry_provider_preflight_dicts()` 取 summary dict，`build_configured_tool_registry_provider_preflight_result()` 也直接复用同一层取 result dict。
- 同时，`build_configured_tool_registry_provider_preflight_dicts()` 本身改成直接从 `build_configured_tool_registry_provider_preflight_outputs_from_dict()` 取最后两个 dict；execute 侧的 `execute_configured_tool_registry_provider_preflight_dicts()` 则直接复用 `execute_configured_tool_registry_provider_preflight_outputs()`，而 `execute_configured_tool_registry_provider_preflight()` 也退回成直接复用 `execute_configured_tool_registry_provider_preflight_dicts()`。这样 build/execute 两侧最外层 dict outward 边界都进一步拉直到了“最近邻 dict seam”。
