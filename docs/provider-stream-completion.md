# 远端模型流结束与部分输出

## 结束判定

OpenAI-compatible `/chat/completions` 流有文本输出且收到以下任一信号时，才按正常结束处理：

- SSE `data: [DONE]`。
- 当前提取文本所用的首个 choice 的已知 `finish_reason`：`stop`、`length`、`tool_calls`、`content_filter` 或 `function_call`。允许这种提供方在结束帧后直接关闭连接；继续读取其后的 usage 帧。

`finish_reason` 取值参考 [OpenAI 官方流事件文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)。这些值表示生成已停止，不证明答案充分、未被截断或符合用户要求。

只有 EOF、usage、空 choices、空 delta、null/未知 finish reason 均不能证明完成；空 role/结束/usage 帧不产生文字，也不能触发递归解析。已收到 finish reason 后的实际传输或解析异常仍按失败处理。

## 失败与持久化

- 无结束信号的空流或部分流返回既有 `remote_provider_stream_interrupted`；正常结束却无文字返回 `remote_provider_empty_response`。
- 部分文字保留在失败任务的最终回答 Trace 中，Trace/delta/JSON/Markdown 导出可读；每个片段更新内存正文与递增 seq，数据库写入仍遵守原来的每 8 片段及时间节流，终态保存全部已接收文字。
- 失败任务不写入成功 assistant 消息或任务 Memory，不发送 `done`；释放队列执行槽。失败重连回放已有错误，不再次请求模型。
- 流中断不自动重放已经输出的请求；`retryable` 表示用户可按既有任务分支重新执行。仅首次 HTTP 400 的 `stream_options` 兼容回退仍保留。
- 低敏 `llm_http_attempt` 的 EOF 结果记为 `interrupted`，不包含提示词、响应正文、模型、主机或 key。SSE/Trace/export 字段形状不变。

## 验证与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k provider_stream_completion
backend/.venv/bin/python backend/scripts/test_provider_stream_postgres.py
```

静态专项 12 个测试覆盖结束信号、空帧/typed delta、部分 EOF、不自动重试、低敏计数及尾部 usage。集成专项 6 个测试使用实际本机 HTTP 的 OpenAI-compatible Provider 与独立 PostgreSQL，覆盖任务失败、单片段与批量边界后尾部、delta 版本、导出、失败重连、400 兼容回退，以及 `[DONE]`/finish reason 正常结束；已进入 backend-e2e workflow。

2026-10-08 验证来源：`/tmp/insightagent-stream-completion-static.log`、`/tmp/insightagent-stream-completion-postgres.log`；反馈和并发生命周期回归各 6/6，来源 `/tmp/insightagent-stream-completion-feedback.log`、`/tmp/insightagent-stream-completion-parallel.log`。完整门禁来源 `/tmp/insightagent-stream-completion-release.md` / `.json`。仅使用本地模型协议替身，不代表真实提供方或模型质量验收。
