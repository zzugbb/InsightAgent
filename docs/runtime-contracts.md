# 运行时稳定契约

本文是跨前后端契约的导航和共同约束；具体字段与边界由专题文档负责。修改对外接口时同时审查 OpenAPI、SSE、Trace、导出和真实调用行为。

## SSE、Trace 与导出

- `GET /api/tasks/{task_id}/stream` 事件：`start`、`state`、`trace`、`tool_start`、`tool_end`、`heartbeat`、`token`、`cancelled`、`timeout`、`done`、`error`。
- trace 事件的 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）；tool_start/end 与 action 按 `step_id` 对齐。并发工具事件允许交错。
- REST trace 返回持久化完整步骤；delta 使用 after_seq，默认 limit 200、最大 500。步骤正文/metadata/用量更新递增 seq，可跳号；最终 observation / final_answer 的阶段性空值不能视为最终结果。
- 历史回放、任务/会话 JSON v1.0 与 Markdown 导出消费同一记录，不触发执行。新增 meta 属于可选扩展，旧 Trace 不补造依赖、并发、结束原因或 checkpoint。
- error 保留结构化 code/fatal/retryable/detail/status_code；diagnostic 仅含固定分类、reason、recoverability、HTTP 状态族与 detail 是否存在。

## 执行与证据

| 主题 | 稳定边界 | 详细规则 |
| --- | --- | --- |
| Agent / 上下文 | 同用户/会话、有界历史；规划 → 工具 → 反馈，默认 3 轮 / 32 节点；公开证据裁剪并脱敏 | [Agent 核心](agent-core-alignment.md) |
| 依赖与绑定 | 最多 32 节点 / 128 边；仅成功公开预览标量绑定 query/expression，非法图拒绝整图 | [工具依赖](tool-dependencies.md) |
| 内建工具并发 | 默认串行、单任务 1–4、进程最多 8 读取线程；协调线程写 Trace/终态 | [并发](task-tool-parallel.md) |
| HTTP 读取并发 | 固定 GET、无请求体、显式 parallel_read_only；资格绑定工厂 runner 与配置快照 | [HTTP 只读](http-read-parallel.md) |
| 分支重跑 | 本人已终结任务，独立会话，当前设置，幂等，不复制结果 | [重跑](task-reruns.md) |
| 步骤恢复 | 实验性内建顺序计划快照，成功前缀复用；HTTP/DAG 不支持 | [checkpoint](task-checkpoints.md) |
| RAG 导入 | 幂等受理、每请求 5000 切块、分批确认、仅排队取消、权限复核，不自动重放部分失败 | [后台导入](rag-background-ingest.md) |

- 检索证据最多 6 片段，每片段 1,200 字符、JSON 8,000 字符，来源/文档版本作为不可信资料供模型引用；提供证据不证明模型一定正确引用。
- HTTP 模型证据仅取成功 action 的公开 effective_result_output_keys，最多 6 项、单项 JSON 3,000 / 总 JSON 8,000 字符；不复制原始响应、输入和注册表秘密。
- 实际工具执行清单与 checkpoint 复用分开传给最终回答，区分自行推算与已执行。普通提示中的故障标记不触发失败，显式测试辅助函数不由生产 runner 自动调用。
- canonical mock 是明确演示路径；remote 缺连接配置明确失败。默认配置可按 provider/model/key 自动选择 remote，否则 canonical mock；该默认继承规则不等于 remote 异常后静默切换 mock。

## 终态、回答与用量

- 成功状态、最终 Trace/usage、assistant 消息和会话时间原子提交；竞争失败不插入回答，Memory 与 done 在提交后执行。详见[任务成功事务](task-completion.md)。
- 远端流只有 DONE 或已知首 choice finish_reason 才按正常结束；异常 EOF 保留部分失败 Trace，不写成功消息、不自动重试。详见[流结束](provider-stream-completion.md)。
- completed 表示执行和保存结束，不证明目标满足。工具停止原因与模型结束原因按白名单展示；消息 completion 是可选扩展，独立于任务分页/筛选，旧/损坏 Trace 不推断。详见[回答完整性](answer-completion.md)。
- planning/final/overall 分阶段记录，统计优先有效 overall，缺项按已知 final + planning 回退，不重复计数。失败、放弃或取消尝试未返回用量时保持未知，费用仅为配置估算。详见[用量口径](usage-accounting.md)。
- 流尾、回退返回和成功提交前复核取消/超时，终态与执行 owner 竞争不覆盖他人的结果。底层调用返回前未必可强制中断。

## 前端展示与恢复

输入法组合中的 Enter 不发送；普通 Enter 发送、Shift+Enter 换行。normalized 状态驱动轮询，failure hint/source 优先显式摘要；本地语义过滤、处置提示和知识库往返不改变业务 API。

failed 轮询不提前截断活动 SSE。增量同步失败可退避，流关闭后必要时补拉既有任务/Trace；列表刷新失败保留陈旧数据与草稿。Task Center/Audit/Usage 共用失败回放，不能从 UI 状态推断缺失工具调用。窄屏与 ID 显示处理见[专项检查](post-seal-usability-audit.md)。

## 鉴权、安全与工程接口

JWT 要求 alg=HS256、typ=JWT，过期与 subject 校验；refresh 输入 trim 后拒绝空白。生产默认 JWT 与 wildcard CORS 被拒绝，签发校验在 auth session 写入/轮换之前完成。Key 与访问边界见[安全政策](../SECURITY.md)。

服务端 X-Request-ID、安全 header、路由模板日志和 llm_http_attempt 只输出限定低敏字段。health.operations、release/trend/artifact/operator summary 不回显连接秘密、联系人、runbook URL 或日志正文；readiness 配置摘要不能代替运维演练。

OpenAPI 当前为 51 操作 / 89 组件，指纹门禁与[API 变更记录](api-changelog.md)一起维护；OpenAPI 不覆盖 SSE/export 的全部行为。门禁选择器、零匹配退出码 5、list-tests/list-selections、summary 与 artifact 保留流程见[运行手册](development-runbook.md)。
