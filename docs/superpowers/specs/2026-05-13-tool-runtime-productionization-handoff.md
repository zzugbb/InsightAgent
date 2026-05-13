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
- `build_tool_plan_item_execution()`
- `build_tool_plan_item_success_effects()`
- `build_tool_plan_item_terminal_effects()`

### 2. `chat_execution_service.py` 当前剩余职责

虽然已经明显变薄，但它还保留以下职责：

- `for tool_spec in tool_plan` 外层遍历
- 单个 tool 的 `while True` retry loop 控制流
- SSE 发射时机
  - `tool_start`
  - `state`
  - `tool_end`
  - `error`
  - `trace`
- terminal failure 时的：
  - `complete_task(...)`
  - `record_failure_event(...)`
  - `yield state(error)`
  - `return`
- success path 时的：
  - trace append
  - `tool_observations.append(...)`
  - rag follow-up step append

换句话说，当前“字段搬运”已经显著减少，但“整个单个 tool plan item retry loop 的执行控制”还没有完整封装成一个更高层 helper。

### 3. 当前 focused regression 状态

[backend/scripts/test_tool_runtime_slice.py](/Users/gaobingbing/Desktop/code/SuperPod/InsightAgent/backend/scripts/test_tool_runtime_slice.py) 当前已经扩展到 **61 条测试**，并全部通过。

已覆盖的关键契约包括：

- `build_tool_attempt_bundle`
- `build_tool_attempt_execution`
- `build_tool_attempt_loop_result`
- `build_tool_attempt_loop_terminal_result`
- `build_tool_plan_item_retry_loop_result`
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

- focused tests：`61` 条通过
- `compileall`：通过
- `common` tooling + backend/frontend e2e 聚合回归：通过

## 推荐的新会话第一优先级

### P0: 封装“执行单个 tool plan item retry loop”的完整 helper

这是最自然的下一刀，也是当前收口链条的延续。

#### 建议目标

在 `tool_runtime.py` 中新增一个更高层 helper，语义大致类似：

- `build_tool_plan_item_retry_loop_execution(...)`
- 或 `execute_tool_plan_item_loop(...)`

该 helper 最好直接承接：

- `task_id`
- `iteration_ctx`
- `initial_action_step`
- `tool_name`
- `tool_input`
- `prompt`
- `user_id`
- `provider_model`
- 以及生成 token / rag token 所需输入

#### 理想返回内容

建议该 helper 直接返回一个“循环终态对象”，至少包含：

- start/tool_end/error 相关事件
- 最终 `action_step`
- `last_error`
- `retryable`
- success path 的：
  - `trace_event`
  - `success_effects`
  - `rag_followup`
- terminal path 的：
  - `terminal_effects`
  - `should_return`
- 以及需要继续兼容的旧字段（若 service 仍依赖）

#### 收益

完成后，`chat_execution_service.py` 中单个 tool 的部分会进一步缩成：

1. 调 runtime helper 得到 loop 执行结果
2. 发 SSE
3. 成功则 append trace / observation / rag
4. 失败则 complete task / audit / return

也就是把当前 `while True` 自己控制 retry 的壳子进一步拿掉。

## 建议执行方式

### 仍然保持当前节奏

继续用“小切片成组推进”的方式，不要大改。

建议一轮只推进 2-3 个紧邻小切片，例如：

1. 先补 focused failing tests
2. 再加 loop execution helper
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

- 单个 tool retry loop success 终态 shape
- 单个 tool retry loop terminal failure 终态 shape
- retry 场景下 `attempt` / `last_error` / `next_action_step` 继续沿用既有语义
- `tool_start/state` 仍然先于执行发出
- success path 的 `trace + observation + rag_followup` 仍完整可取

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

