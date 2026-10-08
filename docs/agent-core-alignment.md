# Agent 核心能力对齐

## 目标与封板结论

按项目“可视化、可解释、工具驱动的 Agent + Memory/RAG + 流式输出”定位补齐已有能力的缺口。

**2026-10-08：本地实现与契约验证已封板，可进入后续维护或按实际需求选定的下一主线。** 已覆盖有界对话上下文、RAG 正文/来源证据、工具反馈决策、Trace 关系/完整详情和知识文件导入；三个核心场景通过 PostgreSQL/Chroma 验证。真实模型的语义质量、延迟与成本不属于本地替身可证明的范围，仍留在 `project-completion-audit` 外部待验收项；无有效 key/目标环境时不反复索要资源。

## 会话上下文与知识证据

- 普通非 canonical mock 任务在执行开始时读取同用户、同会话中本任务创建前已完成的问答配对，按最近任务选取并恢复时间顺序。失败、取消、未配对、跨用户/会话内容，以及在本任务创建后才完成的答案均排除。
- 最多 6 轮，单消息最多 4,000 字符，历史 JSON 最多 16,000 字符；按完整配对裁剪，最新一对即使 JSON 转义膨胀也会缩短到预算内。SQL 读取同样限制条数和每条内容大小。
- 首轮规划、后续决策与最终回答共享同一快照。规则回退、实际工具执行、当前 task.prompt/message 与 Memory 追加仍使用本次原始输入，避免历史工具标记重放；完整分支重跑的新会话不复制父会话，checkpoint 分支与 canonical mock 演示保持原行为。
- 历史 assistant 上下文可选携带最终回答步骤的白名单 `completion` 原因，计入上述 JSON 预算；模型收到截断/执行限制及“结束不代表目标完成”的提示，损坏或缺失记录不推断。见[回答完整性](answer-completion.md)。
- 首轮 Trace.meta 可选追加 `conversation_context` 的 `turn_count`、`character_count` 与 `truncated`，不持久化整份模型历史提示词。
- 模型额外接收已脱敏 RAG Trace 的正文与知识库、来源、文档 ID、版本/hash，优先最近检索；最多 6 片段、单片段 1,200 字符、证据 JSON 8,000 字符，标记为不可信数据，并指导引用提供的来源/版本。计数型 Observation 和已有 Trace/导出保持原形状；证据提供不保证真实模型一定正确引用。
- 后续维护补齐公开 HTTP 工具结果：成功 action 的公开结果字段进入模型反馈与最终回答，补足计数摘要丢失的搜索条目等内容。只读取 `effective_result_output_keys` 并复用脱敏；最多 6 项、单项 JSON 3,000/总 JSON 8,000 字符，最多三层容器、每容器最多 6 项、单字符串最多 1,200 字符，并可进一步收缩以满足 JSON 预算；裁剪标记 `truncated`。失败结果、原始响应/输入/注册表配置不进入新增证据，原 Observation/Trace/export 与 canonical mock 保持原行为。
- 会话消息仍在 PostgreSQL，Chroma Memory 仍沿用已有追加/调试职责；这里没有新增长期语义回忆或附件服务。

## Agent 执行契约

执行方式为结构化工具规划 → 执行 → 安全 Observation → 下一轮工具规划 → 最终流式回答。复用现有 Provider、工具注册表、DAG 调度、取消/超时、SSE 和持久化。

- `AGENT_MAX_ROUNDS=3`，包含首轮，范围 1–8；设为 1 保持旧单轮行为。每任务最多 32 个业务工具节点，不计首轮 planner 工具。
- 只有首轮模型规划有效且包含业务工具时才启动反馈。canonical Mock、首轮规则回退、无业务工具和 checkpoint 分支保持单轮；不将 Mock 规则输出宣称为自主模型决策。
- 反馈使用任务启动时的工具注册表快照；各轮仍由现有执行器校验工具与用户资源权限。
- 后续规划只接受完整有效的工具列表，不把非法/部分有效响应回退成原始计划。决策阶段 Provider 异常沿用任务失败处理。
- 各轮 DAG 独立；依赖与标量绑定仅引用本轮节点。跨轮通过安全 Observation 传递信息，不能引用上一轮 DAG 节点 ID。
- 根据模型返回的工具列表动态追加行动；空列表结束工具阶段。轮次、总节点数、Observation 上限（24,000 字符）或重复规划动作触发终止；已有工具重试仍由执行器控制。
- 最终回答接收白名单工具停止原因与证据/未解决事项说明，并在最终 Trace 可选记录 agent_stop_reason；模型结束原因与聊天/详情提示见[回答完整性](answer-completion.md)，不宣称真实模型一定遵循提示。
- 终止 Trace 的 `agent_decision` 为 `no_tools`、`max_rounds`、`max_tool_calls`、`observation_limit`、`repeated_action` 或 `invalid_decision`；继续执行为 `continue`。到达限制表示结束工具阶段，不证明任务需求已全部满足。
- 每轮执行完毕、进入下一次模型决策前立即持久化已完成 Trace；取消/超时在决策前后复核，迟到决策不得追加工具。
- Trace.meta 可选追加 `agent_round`、`agent_decision`、`agent_from_step_ids`；SSE 事件名、Trace ID/seq、delta 和 JSON v1.0/Markdown 导出形状兼容。
- 成功任务的用量汇总包含首轮规划、后续决策（包括空列表/被拒绝响应）与最终回答；提供方缺失字段沿用估算规则。没有模型调用的限额终止步骤 token/cost 为 0。
- [任务/会话用量统计](usage-accounting.md)消费已持久化的 overall 总量，字段缺失时回退 final + planning；Dashboard、会话汇总与导出保持相同口径，来源筛选包含规划阶段，不改变任务明细。
- [正常任务成功保存](task-completion.md)将 completed/Trace/usage、assistant 消息与会话更新时间一起提交，避免成功状态可见但下一轮缺失回答；失败回滚与终态竞争沿用既有处理。
- 多轮任务不生成单轮 checkpoint 快照；`AGENT_MAX_ROUNDS=1` 和已有 checkpoint 分支仍保留原有资格。完整任务分支重跑不受影响。

## Trace Flow 展示契约

- 虚线仅表示实际记录顺序，不推断工具依赖；实线表示 `plan_node_id/depends_on` 声明的依赖，或 `agent_from_step_ids` 的决策来源。
- `parallel_group_id` 相同的工具并排展示，不连接同组相邻工具。
- 同一 plan node ID 按 `agent_round` 隔离，旧 Trace 缺省为首轮。筛选隐藏源节点后，不用邻近节点替代真实依赖。
- 节点展开显示完整内容和服务端返回的 metadata；节点内滚动，避免展开遮挡相邻节点。
- 旧 Trace 继续显示记录顺序；不补造历史依赖、并发或决策信息。

## 知识导入契约

普通文件入口复用后台 RAG 任务，UTF-8、数量/大小和字符预算在浏览器校验；文件名保留为 source/document_id，同名文档新内容保留版本。预览后提交，结果不确定时冻结草稿并重试原载荷/幂等键。复核自动展开目标库，检索测试带入该库，共享写入仍限管理员。详情与使用边界见 [RAG 后台导入](rag-background-ingest.md)。

## 最终验证与实现位置

后续维护验证来源：`/tmp/insightagent-tool-evidence-release.md` / `.json`，full gate **10/10**（后端 **2155/2155**、前端 **200/200**）；`/tmp/insightagent-tool-evidence-postgres.log` 公开 HTTP 证据 **3/3**，实际请求/持久化验证相同命中数不同正文的分支、单轮回答、来源与脱敏。反馈 **6/6**、HTTP 并发 **7/7**、会话/Chroma 核心 **9/9** 回归日志均为 `/tmp/insightagent-tool-evidence-*-regression.log`；本地替身不能证明真实模型效果。

2026-10-08 最终来源：`/tmp/insightagent-core-scenarios-release.md` / `.json`，full release gate **10/10**（后端 **2148/2148**、module boundary **9/9**、前端 **200/200**、双构建；lint 两个既有 warning）；`/tmp/insightagent-core-scenarios-postgres.log` 核心场景 **9/9**，含真实 Chroma 写入/检索、两个本地条件分支、上下文隔离/排队边界/旧指令回退、Trace/delta/导出来源一致性。模型仅本地替身。

回归来源：`/tmp/insightagent-context-feedback-regression.log` **6/6**，`/tmp/insightagent-context-checkpoint-regression.log` **9/9**。既有前端基线为 Trace 桌面/手机 **2/2**、文件导入 **7/7** 与布局复核 **2/2**，保留原日志来源；本轮没有前端实现变更，未重跑浏览器。

- `backend/app/services/conversation_context.py`：有界会话快照与低敏摘要。
- `backend/app/services/agent_knowledge_context.py`：模型 RAG 证据的来源白名单与预算。
- `backend/app/services/agent_tool_context.py`：公开 HTTP 结果证据与统一模型 Observation 入口。
- `backend/app/services/agent_feedback.py` / `chat_execution_service.py`：反馈协议、用量与任务生命周期。
- `frontend/app/components/workbench/trace-flow-layout.ts` / `trace-flow-view.tsx`：关系派生、布局与完整详情。
- `frontend/app/components/workbench/knowledge-import-modal.tsx` / `knowledge-import-utils.ts`：文件预览/校验；`rag-ingest-jobs.tsx` 复用后台任务与幂等请求。
- `backend/scripts/test_agent_core_scenarios_postgres.py`：独立 PostgreSQL/Chroma、本地 Provider 与实际检索；已纳入 backend-e2e，自动清理。`test_agent_feedback_postgres.py` 继续负责反馈取消/失败/用量边界。
- `frontend/e2e/trace-flow.spec.ts` / `knowledge-import.spec.ts`：已有业务 API fixture 的桌面/手机交互。

命令遵循 [development-runbook](development-runbook.md)。本地封板不代表真实模型、目标部署与用户签收已验收。
