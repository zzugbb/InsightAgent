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

- `build_tool_attempt_bundle()`
- `build_tool_attempt_execution()`
- `build_tool_attempt_loop_result()`
- `build_tool_attempt_loop_terminal_result()`
- `build_tool_plan_item_retry_loop_result()`
- `build_tool_plan_item_retry_loop_execution_result()`
- `execute_tool_plan_item_retry_loop()`
- `build_tool_plan_item_stream_effects()`
- `build_tool_plan_item_continue_update()`
- `build_tool_plan_item_continue_action()`
- `build_tool_plan_item_next_action()`
- `build_tool_plan_item_terminal_return_effects()`
- `build_tool_plan_item_return_action()`
- `build_tool_plan_item_trace_write_action()`
- `build_tool_plan_item_next_action_execution()`
- `build_tool_plan_item_service_effects_execution()`
- `build_tool_plan_item_service_execution()`
- `build_tool_plan_item_service_effects()`

### 2. `chat_execution_service.py` 当前剩余职责

在当前阶段，`chat_execution_service.py` 保留的职责已经更接近“编排副作用执行器”：

- 外层 `tool_plan` 遍历
- SSE 发射时机控制
- trace step append 与 trace persistence 调用
- terminal return 下的任务完成/失败副作用调用
- success path 下按 `continue_action` 更新 `tool_observations` 与 `seq_cursor`
- tool 阶段之后的最终答案生成、超时、取消与任务生命周期治理

当前单个 tool 的 service 壳子已经接近：

1. 调 `execute_tool_plan_item_retry_loop()`
2. 获取 `build_tool_plan_item_service_execution()` 产物
3. 发 trace SSE 并持久化
4. 执行 continue/return 两类后续动作

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

`backend/scripts/test_tool_runtime_slice.py` 当前已扩展到 **78 条测试**，覆盖：

- tool plan compatibility
- tool execution compatibility
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
2. 需要把 mock tool runtime 迁移为可扩展 registry
3. 需要复用同一套 runtime seam 到非 chat 执行路径
4. 需要将 trace / audit / state side effects 再统一成更高层执行器
