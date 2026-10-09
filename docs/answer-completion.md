# 工具停止与回答完整性提示

## 当前状态与含义

2026-10-08：本地实现与契约验证完成。任务 `completed` 表示执行及回答保存正常结束，不证明用户目标已经全部满足；工具停止与模型生成结束分别记录。

- 反馈工具阶段结束时，将白名单停止原因和“只依据现有证据回答、区分已支持与未解决内容”的提示传给最终回答模型；限额/无效或重复计划不新增模型决策或工具调用。
- 最终回答 Trace.meta 可选记录 `agent_stop_reason`：`no_tools`、`max_rounds`、`max_tool_calls`、`observation_limit`、`repeated_action`、`invalid_decision`。无反馈循环的单轮/mock/checkpoint 不推断停止原因。
- OpenAI-compatible Provider 保留首 choice 已知 `finish_reason`，每次新调用重置；流式与非流式回答均支持。最终回答 Trace.meta 可选记录 `provider_finish_reason`：`stop`、`length`、`content_filter`、`tool_calls`、`function_call`。仅 `[DONE]` 不推断 `stop`，未知值/其他 choice 不进入记录。
- 接收到结束原因后的传输/解析失败仍保持失败；已知原因可随失败 Trace 保存，不产生成功回答或 `done`。取消/执行实例竞争遵守原终态保护。
- 成功提交后、`done` 前发送既有 `trace` 事件更新最终回答步骤；Trace ID 不变，最终正文/用量及新增 metadata 更新递增 seq；空流转入非流式回答时也递增，不依赖结束原因，delta、回放和 JSON v1.0/Markdown 导出读取相同记录。SSE/Trace/delta/export 外层字段形状保持兼容。

## 连续对话中的历史回答

后续任务的会话快照为历史 assistant 记录可选附带 `completion`，仅含 `agent_stop_reason` / `provider_finish_reason` 白名单代码。首轮规划、后续决策与最终回答共享快照，并收到提示：历史回答的生成结束不证明目标完成，截断或执行限制可能留下未解决检查。

- 保留同用户/同会话、任务创建前已完成的配对；最多 6 轮、单消息 4,000、历史 JSON 16,000 字符，completion 计入该预算。消息、task.prompt、Memory 追加、API/SSE/导出正文不变。
- 数据库先限制最近 7 个候选配对，再提取 Trace 中最后一个 `final_answer` 步骤的两个原因字段，每字段最多 32 字符；应用层再次校验枚举。不复制 Trace 内容、工具载荷或其他 metadata。
- PostgreSQL 16 的 JSON 输入校验保护损坏/非数组/不可转 jsonb 的旧记录；无合法结束原因时仍保留原问答，不根据正文推断。正常 `stop` / `no_tools` 也不作为目标完成证明。
- 本地测试验证信号传递和隔离；真实模型是否正确使用这些提示须按具体任务验收，当前样本见[真实模型记录](real-model-acceptance.md)。

## 展示规则

聊天回答与任务详情以中英文文案分别提示工具执行限制、无效/重复后续计划、输出长度限制、内容过滤和工具请求结束；不改变已保存正文，也不自动续写、重跑或更改成功状态。正常 `stop`/`no_tools` 不额外提示；缺少字段的旧任务保持原展示。

会话消息接口 `GET /api/sessions/{session_id}/messages` 的每条消息可选返回 nullable `completion`：`seq`、`agent_stop_reason`、`provider_finish_reason`。只为同用户/会话任务对应的 assistant 消息提取最终回答信息；user、无对应任务、跨用户/会话、损坏或未知记录不推断。`seq` 仅接受非负 JSON 整数，最大为 JavaScript 安全整数；无有效字段时 completion 为 null。新增为兼容响应扩展，OpenAPI 51 操作 / 89 组件，正文、SSE/Trace/delta 和会话/任务 JSON v1.0/Markdown 导出不变。

聊天比较消息 completion、已加载任务 Trace 与活动流最终回答的 seq：较新记录优先；同序号时消息优先于任务列表，活动流优先于消息。任务不在最近 50 条或被筛选隐藏时，仍可直接从历史消息显示提示，不增加逐消息请求；旧服务未返回 completion 时沿用 Trace。前端仅信任白名单代码，不把上游任意原因当作文案。

提示说明可观察到的执行限制，不判断答案语义质量；是否正确回答、是否正确引用及是否遵循停止提示仍须真实模型验证。未覆盖的模型场景与目标部署保持未验证。

## 实现与验证

历史回答 PostgreSQL 14/14、终态用量 10/10、原子完成 6/6 覆盖空流回退后递增 seq、消息/导出一致、取消竞争及历史白名单容错。历史 Chromium 2/2 覆盖桌面/390px、超过 50 个任务与筛选独立性，使用业务 API fixture。最新完整门禁与来源见[验证基线](validation-baseline.md)。

- `backend/app/providers/completion_signals.py` / `openai_compatible_provider.py`：首 choice 原因白名单、调用间重置。
- `backend/app/services/answer_completion.py` / `chat_execution_service.py`：停止上下文、最终步骤原因、终态/seq 与 SSE。
- `backend/app/services/conversation_context.py` / `session_message_history.py`：复用最终回答安全投影与枚举归一化，分别提供模型快照和消息 completion；消息按任务一次提取，避免同任务重复消息重复解析。
- `frontend/app/components/workbench/answer-notices.ts` / `answer-notice-view.tsx`：原因与最新版本选择、共用提示；聊天及任务详情复用。

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k conversation_context
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k answer_completion
backend/.venv/bin/python backend/scripts/test_answer_completion_postgres.py
cd frontend
node --test --experimental-strip-types app/components/workbench/answer-notices.node.test.ts
npx playwright test e2e/answer-completion.spec.ts --project=chromium --workers=1 --reporter=list --output=/tmp/insightagent-answer-completion-e2e-results
```

上述专项使用本地模型/业务 API 替身，不能证明所有真实回答遵守提示；真实样本与风险见[验收记录](real-model-acceptance.md)。
