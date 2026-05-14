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

- `build_tool_attempt_bundle()`
- `build_tool_attempt_execution()`
- `build_tool_attempt_loop_result()`
- `build_tool_attempt_loop_terminal_result()`
- `build_tool_plan_item_retry_loop_result()`
- `build_tool_plan_item_retry_loop_execution_result()`
- `build_tool_plan_item_execution()`
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
- tool 级 `trace_write_actions` 执行与持久化副作用
- `next_action_execution(kind=return)` 下执行 runtime 已组装好的 return action：
  - `complete_task(...)`
  - `record_failure_event(...)`
  - `yield state(error)`
  - `return`
- `next_action_execution(kind=continue)` 下对 `continue_action` 的高层消费：
  - `tool_observations.extend(...)`
  - `seq_cursor += ...`

换句话说，当前“单个 tool retry loop 的执行控制”和大部分 success/terminal 字段搬运都已经下沉；`chat_execution_service.py` 里主要剩下 tool 级 SSE 发射、trace 持久化和任务完成/失败这类编排副作用。

### 3. 当前 focused regression 状态

[backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py) 当前已经扩展到 **78 条测试**，并全部通过。

已覆盖的关键契约包括：

- `build_tool_attempt_bundle`
- `build_tool_attempt_execution`
- `build_tool_attempt_loop_result`
- `build_tool_attempt_loop_terminal_result`
- `build_tool_plan_item_retry_loop_result`
- `build_tool_plan_item_retry_loop_execution_result`
- `execute_tool_plan_item_retry_loop`
- `build_tool_plan_item_stream_effects`
- `build_tool_plan_item_continue_action`
- `build_tool_plan_item_terminal_return_effects`
- `build_tool_plan_item_return_action`
- `build_tool_plan_item_trace_write_action`
- `build_tool_plan_item_next_action_execution`
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

- focused tests：`78` 条通过
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
- 将 trace/audit/state side effects 再统一成更高层执行器

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
   - 继续把“单个 tool plan item retry loop”整体封装成 runtime helper
3. 约束：
   - 外部 SSE / trace / e2e 契约不变
   - 先补 failing test，再改实现
4. 必跑验证：
   - focused tests
   - `compileall`
   - `common`
