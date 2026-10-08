# 工具停止与回答完整性提示

## 当前状态与含义

2026-10-08：本地实现与契约验证完成。任务 `completed` 表示执行及回答保存正常结束，不证明用户目标已经全部满足；工具停止与模型生成结束分别记录。

- 反馈工具阶段结束时，将白名单停止原因和“只依据现有证据回答、区分已支持与未解决内容”的提示传给最终回答模型；限额/无效或重复计划不新增模型决策或工具调用。
- 最终回答 Trace.meta 可选记录 `agent_stop_reason`：`no_tools`、`max_rounds`、`max_tool_calls`、`observation_limit`、`repeated_action`、`invalid_decision`。无反馈循环的单轮/mock/checkpoint 不推断停止原因。
- OpenAI-compatible Provider 保留首 choice 已知 `finish_reason`，每次新调用重置；流式与非流式回答均支持。最终回答 Trace.meta 可选记录 `provider_finish_reason`：`stop`、`length`、`content_filter`、`tool_calls`、`function_call`。仅 `[DONE]` 不推断 `stop`，未知值/其他 choice 不进入记录。
- 接收到结束原因后的传输/解析失败仍保持失败；已知原因可随失败 Trace 保存，不产生成功回答或 `done`。取消/执行实例竞争遵守原终态保护。
- 成功提交后、`done` 前发送既有 `trace` 事件更新最终回答步骤；Trace ID 不变，新增 metadata 更新递增 seq，delta、回放和 JSON v1.0/Markdown 导出读取相同记录。OpenAPI 指纹与外层字段形状保持兼容。

## 展示规则

聊天回答与任务详情以中英文文案分别提示工具执行限制、无效/重复后续计划、输出长度限制、内容过滤和工具请求结束；不改变已保存正文，也不自动续写、重跑或更改成功状态。正常 `stop`/`no_tools` 不额外提示；缺少字段的旧任务保持原展示。

聊天复用当前已加载任务 Trace 和活动流 Trace；按最终回答 seq 选择较新记录，避免旧流覆盖新记录。仅有历史消息但对应任务尚未加载时无法推断提示，可在任务详情读取完整记录。前端仅信任白名单代码，不把上游任意原因当作文案。

提示说明可观察到的执行限制，不判断答案语义质量；是否正确回答、是否正确引用及是否遵循停止提示仍须真实模型验证。没有真实 key/部署环境时保持未验证。

## 实现与验证

- `backend/app/providers/completion_signals.py` / `openai_compatible_provider.py`：首 choice 原因白名单、调用间重置。
- `backend/app/services/answer_completion.py` / `chat_execution_service.py`：停止上下文、最终步骤原因、终态/seq 与 SSE。
- `frontend/app/components/workbench/answer-notices.ts` / `answer-notice-view.tsx`：原因与最新版本选择、共用提示；聊天及任务详情复用。

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k answer_completion
backend/.venv/bin/python backend/scripts/test_answer_completion_postgres.py
cd frontend
node --test --experimental-strip-types app/components/workbench/answer-notices.node.test.ts
npx playwright test e2e/answer-completion.spec.ts --project=chromium --workers=1 --reporter=list --output=/tmp/insightagent-answer-completion-e2e-results
```

静态 **6/6**、独立 PostgreSQL **6/6**、前端计算 **5/5**；真实本机 HTTP 替身验证长度/过滤/工具请求、仅 DONE/规划原因隔离、回退回答及失败后的原因保存；工具停止上下文、SSE/Trace/delta/导出/回放一致。来源 `/tmp/insightagent-answer-completion-{static,postgres,frontend}.log`。

Chromium **2/2**，1440×900 英文、390×900 中文；Enter 发送 → 提示 → 刷新 → 任务详情 → 返回聊天均通过，页面身份/非空/无错误 overlay、控制台与横向溢出检查通过。Browser plugin not available，按前端调试技能使用项目 Playwright；开发工具悬浮入口遮挡紧凑中文发送按钮时使用正常 Enter 发送，未屏蔽错误界面。截图 `/tmp/insightagent-answer-completion-{chat,detail}-{1440,390}.png`；来源 `/tmp/insightagent-answer-completion-e2e.log`。仅业务 API fixture，未验证真实模型和其他浏览器。

终态 **10/10**、反馈 **6/6** 回归来源 `/tmp/insightagent-answer-completion-{terminal,feedback}-regression.log`。完整发布门禁 `/tmp/insightagent-answer-completion-release.md` / `.json`：**10/10 PASS**、后端 **2191/2191**、module boundary **9/9**、前端 **213/213**、lint **0 error / 2 个既有 warning**、双构建通过。新增专项已进入 backend-e2e 和静态门禁；浏览器专项自动进入 frontend Chromium 发现范围。
