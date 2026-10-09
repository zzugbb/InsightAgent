# 任务生命周期与运行时契约

本文维护 SSE、Trace、回答、用量与恢复的共同规则。模型决策见[架构](architecture.md#agent-上下文与反馈)，工具图和并发见[工具执行](tool-execution.md)，导入见[RAG](rag-background-ingest.md)。修改接口同时审查 OpenAPI、SSE、Trace、导出和真实调用行为。

## SSE、Trace 与导出

- `GET /api/tasks/{task_id}/stream` 事件：start、state、trace、tool_start、tool_end、heartbeat、token、cancelled、timeout、done、error。stream 驱动/接管任务，仅 POST 创建后离开客户端不保证自动执行。
- `trace.data.step` 与 REST TraceStep 同构：id/type/content/meta/seq?；工具事件按 step_id 合并，可交错。delta 使用 after_seq，limit 默认200、最大500；正文/metadata/用量更新递增seq，可跳号。阶段性空正文不能视为最终结果。
- REST完整Trace、历史回放与任务/会话JSON v1.0、Markdown导出消费同一记录，不触发执行。新增meta为可选扩展，旧记录不补造依赖、并发、结束原因或checkpoint。
- error 保留 code/fatal/retryable/detail/status_code；diagnostic 仅含固定分类、reason、recoverability、HTTP状态族与detail是否存在。SSE建连HTTP200不证明任务成功。

流程图虚线只表示记录顺序，实线只表示 plan_node_id/depends_on 或 agent_from_step_ids 声明关系；同 parallel_group_id 并排且不连接组内相邻工具。plan node按agent_round隔离，旧记录默认首轮；筛选不替换隐藏的真实来源，展开内容在节点内滚动。

## 成功提交与终态竞争

正常回答由 `complete_task(..., assistant_content=final_content)` 在一个PostgreSQL事务中保存completed、最终Trace/usage、assistant消息与会话updated_at，提交后写best-effort Memory、发送最终trace更新和done。并发同任务仅一方成功，后续返回0；回答插入/会话更新失败回滚，随后保存失败Trace并发error，没有成功消息或Memory。

- 成功更新受用户、活动状态和execution owner限制，session_id取成功更新行，不能由调用方指定；外部读取只见提交前活动状态或提交后完整结果。
- 独立create_message及不传assistant_content的complete_task保留原语义；不补造历史缺失回答。失败最终文本可保留Trace，不进入后续成功问答上下文。
- 流尾、空流回退返回、最终Trace保存后/成功事务前复核取消和总时限；跨时限不写成功消息、Memory或done。同步socket阻塞未必立即中断，迟到决策不得追加Trace/工具。
- 执行器自己终结的失败/超时保存已知规划与当前调用用量；外部取消或其他实例已终结不覆盖状态/用量。未持久化的供应商消耗仍可能存在。

实现：`chat_execution_service.py`、`chat_persistence_service.py`、`task_terminal_usage.py`（backend/app/services/）。

## 流结束与回答完整性

流有文本并收到 `[DONE]` 或首choice已知finish_reason（stop、length、tool_calls、content_filter、function_call）才正常结束，继续读取后续usage帧。仅EOF、usage、空choices/delta、null/未知原因不算完成；空role/结束/usage帧不产生文字或递归解析。收到原因后传输/解析异常仍失败。参见[OpenAI流事件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)。

无结束信号返回 remote_provider_stream_interrupted，正常结束无文字返回 remote_provider_empty_response。部分文字进入失败Trace：片段更新内存和seq，DB仍按每8片段及时间节流写入，终态保存完整已收文本。不写成功消息/Memory、不发done；重连回放错误、不重放请求。retryable指可创建分支，只有首次400的stream_options兼容回退保留；EOF观测outcome为interrupted，不记业务正文或凭据。

| 可选最终回答metadata | 允许值与含义 |
| --- | --- |
| agent_stop_reason | no_tools、max_rounds、max_tool_calls、observation_limit、repeated_action、invalid_decision；无反馈的单轮/mock/checkpoint不推断 |
| provider_finish_reason | stop、length、content_filter、tool_calls、function_call；首choice白名单，每次重置，流/非流都支持，仅DONE不推断stop |

模型收到工具停止原因、实际执行/复用清单及已有证据，区分自行推算和执行；限额、重复或无效计划不额外调用决策/工具。自然语言仍为提示约束。completed只表示执行和保存结束，不证明目标满足；原因可随失败Trace保存，不改变失败语义。

### 历史与页面completion

后续历史快照可携带两种白名单completion原因，计入6轮/单消息4000/JSON16000预算；SQL先选最近7个配对，提取最后final_answer，每原因最多32字符。PostgreSQL16 JSON校验兼容损坏/非数组旧数据，无有效原因保留原问答；不复制工具载荷、不据正文推断，消息/原prompt/Memory不变。

消息接口为同用户/会话assistant可选返回 nullable completion（seq及两个原因）；user、无对应任务、跨范围或损坏记录不推断。seq仅非负JSON整数、最大JavaScript安全整数，无有效字段为null。聊天/详情比较消息、已加载任务和活动流seq，较新优先；同seq消息优先于任务、活动流优先于消息。超过最近50任务或筛选隐藏仍从消息读提示，不逐消息请求；旧服务沿用Trace。

中英文提示工具限制、重复/无效决策、长度/过滤/工具请求结束；stop/no_tools及缺字段不额外提示，不改正文，不自动续写或重跑。实现：completion_signals.py、answer_completion.py、conversation_context.py、session_message_history.py、answer-notices.ts / answer-notice-view.tsx。

## 用量口径

summary、dashboard/趋势/榜单、会话导出和Context汇总持久化usage_json，规划含后续反馈决策，明细仍保留final/planning/overall。

- 每个prompt_tokens、completion_tokens、cost_estimate优先有效overall，缺失/无效才按已知final+planning回退，不重复加planning；一项已知保留该值，两项未知保持未知，旧记录不回填。
- 有效值为有限非负数或可解析数字串，0有效；bool/负数/空白/NaN/Infinity无效。total按prompt+completion统计，cost按配置单价估算；不从账单读取。provider/estimated混用归mixed，无法判断归legacy，来源筛选含规划。
- 失败/超时保存已记录规划；已完成最终生成按正常用量，未完成只读取该次ProviderUsage，不按部分文字估算，不读取上一规划last_usage。只有总量保留provider_total_tokens，不反推输入输出；前端仅planning/overall可显示，final未知不显示0。
- 收到模型响应但图非法，规划器随原图错误传实际usage，失败前计planning，不执行图；空正文错误同样只带当前请求usage，非流请求开始前重置last_usage。首轮规则回退、后续失败保持原路径。
- 多次规划任一字段未知，该字段合计仍未知；prompt/completion都已知才计算该次total/成本。没有final调用不造final用量，最终overall仍按各阶段已知字段汇总，不证明未知消耗为0。

统一实现为 `backend/app/services/usage_accounting.py` 与前端 `workbench/utils.ts`，失败/放弃/取消的供应商账单另核对。

## 完整任务分支重跑

本人已结束任务可复制/编辑输入，在独立会话使用当前模型/工具/知识库重新执行。原任务不变，不复制历史消息、Memory、Trace或结果，不保证历史数据版本，不撤销外部副作用，新调用可能收费或写入。

| 接口 | 行为 |
| --- | --- |
| POST /api/tasks/{task_id}/reruns | 201，保存session/task/message/relation；请求{}或UUID idempotency_key与可选user_input，返回TaskCreateResponse及nullable parent_task_id；不调用模型/工具 |
| GET /api/tasks/{task_id}/reruns?limit=20&offset=0 | 本人来源与直接分支，limit1–100/offset≥0，最新优先，total/has_more |

只允许completed/failed/cancelled/timed_out及既有别名；其他返回409 rerun_parent_not_terminal。不存在/他人统一404，管理员无跨用户权限。user_input省略取原prompt，提供时trim非空≤64000，原输入无效也可编辑；无效422 rerun_input_invalid。

同用户/键/来源/参数返回同分支当前状态，同键不同参数409 rerun_idempotency_conflict；无键每次生成。未知送达冻结原参数并复用键，编辑前先查分支。GET含task_id/is_rerun/parent_task_id/items/total/limit/offset/has_more，items仅task_id/session_id/status/created_at，无请求键/hash/原正文/内部用户身份。

创建持有用户advisory lock与来源行读锁，全部插入同事务，失败回滚。删除来源关系parent置空、分支继续存在；删除分支级联关系，幂等记录同寿命。审计task_rerun_created仅新/来源ID、input_edited、prompt_length。新分支通过既有stream执行，“创建并运行”返回工作台接管，不改变列表/Trace/export形状。

## 实验性步骤恢复

同一reruns请求可指定UUID checkpoint_step_id，但必须省略user_input，否则422 checkpoint_input_immutable；无合格快照409 checkpoint_unavailable。本人已结束、同键同起点幂等，不同起点/完整重跑参数冲突。未知送达冻结起点并复用键。

GET /api/tasks/{task_id}/checkpoints 返回task_id、experimental=true、items（step_id/index/tool_name/reused_steps）；旧/不支持任务items为空，他人/不存在404。

- 只支持已存快照的内建task_plan/task_retrieve/calc_eval顺序计划≤32工具；整图必须合格。HTTP、DAG、结果绑定、自定义/覆盖runner、写入工具不支持。多轮反馈不存checkpoint，AGENT_MAX_ROUNDS=1与既有恢复分支保留资格。
- 选择已执行成功或失败步骤，之前全部工具须成功且有观察结果；未执行/缺前缀不可选。独立会话复用前缀，重新执行起点及后续，再回答；复用检索不更新，需新资料选检索起点，需改输入/HTTP/DAG用完整重跑。并发设置不改变前缀顺序。
- 当前设置须验证整份计划runner身份/启用，不兼容checkpoint_unavailable且不调用工具。内建输入白名单，脱敏改变输入不存计划；独立queued seed快照≤2MB，来源删除不影响执行，无新增表。
- 不重新调用规划模型；新规划Trace、复用步骤新UUID/seq，checkpoint_reused与checkpoint_source_step_id标来源，tokens/cost/latency/retryCount归0。checkpoint_index/checkpoint_observations/checkpoint_plan为可选meta，SSE/export兼容。
- 队列、execution owner、重连、取消/超时保护照常；结果提交/新回答前复核，迟到结果不得落盘。外部操作不能强制撤销。

## 前端与安全约束

composition中的Enter不发送，普通Enter发送、Shift+Enter换行。normalized状态驱动轮询，failed轮询不截断活动SSE；delta失败退避，流关闭必要时补拉。列表刷新失败保留数据和草稿；本地筛选/处置不改业务状态。窄屏筛选换行、宽表格内部滚动，ID缩略可查看/复制，API/路由/导出保留完整值。

JWT要求HS256/typ JWT、过期/subject校验，refresh trim拒空白；生产默认JWT/wildcard CORS拒绝，签发校验先于会话写入/轮换。X-Request-ID、安全header和路由/LLM日志仅低敏字段，health/operator摘要不泄露连接秘密或业务正文，readiness不能替代演练。详见[安全政策](../SECURITY.md)。

OpenAPI当前51操作/89组件，与[API变更](api-changelog.md)共同维护；它不覆盖全部SSE/export行为。

## 实现与验证

| 静态selector | 隔离文件（backend/scripts/） | 历史集成范围 |
| --- | --- | --- |
| task_completion_atomic / task_terminal_usage | test_task_completion_postgres.py / test_task_terminal_postgres.py | 6/6、10/10；事务/触发器/竞争/流尾时限 |
| provider_stream_completion | test_provider_stream_postgres.py | 6/6；结束信号、EOF、400、尾部usage |
| answer_completion / conversation_context | test_answer_completion_postgres.py | 14/14；历史白名单、seq、消息与导出 |
| usage_accounting | test_usage_accounting_postgres.py | 3/3；多轮汇总/来源/导出 |
| task_rerun | test_task_rerun_postgres.py | 11/11；独立分支、幂等、来源与删除 |
| task_checkpoint | test_task_checkpoint_postgres.py | 9/9；快照资格/复用/权限/生命周期 |

静态入口和隔离命令见[开发手册](development-runbook.md#隔离专项入口)，数据库场景已纳入backend-e2e。前端专项为 e2e/answer-completion.spec.ts、task-reruns.spec.ts、task-checkpoints.spec.ts 与 answer-notices/usage-accounting.node.test.ts（均在frontend）；数据库/业务API替身不证明真实模型质量。当前整体与真实结果见[验收记录](acceptance.md#验证基线)。
