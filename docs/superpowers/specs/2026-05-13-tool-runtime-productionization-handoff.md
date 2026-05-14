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
- `next_action_execution(kind=continue)` 下对 `continue_update` 的高层消费：
  - `tool_observations.extend(...)`
  - `seq_cursor += ...`

换句话说，当前“单个 tool retry loop 的执行控制”和大部分 success/terminal 字段搬运都已经下沉；`chat_execution_service.py` 里主要剩下 tool 级 SSE 发射、trace 持久化和任务完成/失败这类编排副作用。

### 3. 当前 focused regression 状态

[backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py) 当前已经扩展到 **77 条测试**，并全部通过。

已覆盖的关键契约包括：

- `build_tool_attempt_bundle`
- `build_tool_attempt_execution`
- `build_tool_attempt_loop_result`
- `build_tool_attempt_loop_terminal_result`
- `build_tool_plan_item_retry_loop_result`
- `build_tool_plan_item_retry_loop_execution_result`
- `execute_tool_plan_item_retry_loop`
- `build_tool_plan_item_stream_effects`
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

- focused tests：`69` 条通过
- `compileall`：通过
- `common` tooling + backend/frontend e2e 聚合回归：通过

## 推荐的新会话第一优先级

### P0: 继续压薄 `chat_execution_service.py` 中单个 tool 的最终编排副作用

当前最自然的下一刀，已经不再是 retry loop 本身，而是继续把 service 里“执行 runtime 已经准备好的副作用指令”的部分再上提一层。

#### 建议目标

优先考虑在 `tool_runtime.py` 中新增一层更高层的“tool service effects” helper，直接把当前 service 里还在手工做的内容再统一一点，例如：

- trace append / persist 所需的高层动作序列
- terminal failure 的最终任务副作用输入
- success/terminal 分支选择所需的高层 `next_action`
- `next_action` 对应的执行输入
- service 最终消费所需的聚合执行输入
- `loop_execution_result` 直达 service 最终消费输入
- 需要继续兼容的旧字段（若 service 仍依赖）

#### 理想返回内容

建议该 helper 直接返回一个更接近 service 最终消费形态的对象，例如：

- `trace_write_actions`
- `trace_writes`
- `next_action`
- `next_action_execution`
- `service_effects_execution`
- `service_execution`
- `continue_update`
- `return_action`
- `should_return`
- `terminal_return_effects`

#### 收益

完成后，`chat_execution_service.py` 中单个 tool 的部分会进一步缩成：

1. 调 runtime helper 得到 loop 执行结果
2. 发 SSE
3. 按统一 effects 执行 trace / observation / task side effects
4. 继续向最终答案流转或失败返回

也就是让 service 更接近“编排副作用执行器”，而不是继续做 tool 级字段拼装。

## 建议执行方式

### 仍然保持当前节奏

继续用“小切片成组推进”的方式，不要大改。

建议一轮只推进 2-3 个紧邻小切片，例如：

1. 先补 focused failing tests
2. 再加一层更高层 service-effects helper
3. 再把 service 切到消费这个 helper

### 推荐固定验证顺序

每一轮都保持：

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
python3 -m compileall backend/app backend/scripts/test_tool_runtime_slice.py
bash scripts/test_ci_e2e_tooling.sh common
```

## 建议下一步测试补点

新会话一开始，优先补这类 focused test：

- 更高层 service-effects helper 的 success shape
- 更高层 service-effects helper 的 terminal shape
- `trace_write_actions` 的 step/event/persist_force 节奏不变
- `trace_writes` 的 step/event/force_persist 节奏继续兼容
- `next_action` 的 continue/return 分支语义不变
- `next_action_execution` 的 continue/return 执行输入语义不变
- `service_effects_execution` 的聚合 shape 不变
- `service_execution` 的单入口聚合 shape 不变
- `continue_update` 的 observation delta / seq delta 继续沿用既有语义
- terminal path 的 `return_action` 输入与 task_failed / state(error) 语义继续不变

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
