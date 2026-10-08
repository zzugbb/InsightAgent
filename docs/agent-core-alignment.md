# Agent 核心能力对齐

## 目标与状态

按项目“可视化、可解释、工具驱动的 Agent + Memory/RAG + 流式输出”定位补齐已有能力的缺口。

- 已实现：工具结果驱动的有界反馈决策、Trace 依赖/并发/决策来源展示、完整节点内容与 metadata、知识库内 TXT/Markdown 文件导入与目标库检索入口。
- 当前主线未整体封板：下一步核对多轮上下文、知识库来源追溯和工具条件分支三个核心场景。
- 用户已结束上一阶段的持续收尾目标。`project-completion-audit` 留作外部验收记录；真实 key、目标部署与签收仍未验证，不阻止本地核心能力开发。
- 模板中心、分支对比、扩大 checkpoint 和更多基础设施暂缓。只读备份计划不修改。

## Agent 执行契约

执行方式为结构化工具规划 → 执行 → 安全 Observation → 下一轮工具规划 → 最终流式回答。复用现有 Provider、工具注册表、DAG 调度、取消/超时、SSE 和持久化。

- `AGENT_MAX_ROUNDS=3`，包含首轮，范围 1–8；设为 1 保持旧单轮行为。每任务最多 32 个业务工具节点，不计首轮 planner 工具。
- 只有首轮模型规划有效且包含业务工具时才启动反馈。canonical Mock、首轮规则回退、无业务工具和 checkpoint 分支保持单轮；不将 Mock 规则输出宣称为自主模型决策。
- 反馈使用任务启动时的工具注册表快照；各轮仍由现有执行器校验工具与用户资源权限。
- 后续规划只接受完整有效的工具列表，不把非法/部分有效响应回退成原始计划。决策阶段 Provider 异常沿用任务失败处理。
- 各轮 DAG 独立；依赖与标量绑定仅引用本轮节点。跨轮通过安全 Observation 传递信息，不能引用上一轮 DAG 节点 ID。
- 根据模型返回的工具列表动态追加行动；空列表结束工具阶段。轮次、总节点数、Observation 上限（24,000 字符）或重复规划动作触发终止；已有工具重试仍由执行器控制。
- 终止 Trace 的 `agent_decision` 为 `no_tools`、`max_rounds`、`max_tool_calls`、`observation_limit`、`repeated_action` 或 `invalid_decision`；继续执行为 `continue`。到达限制表示结束工具阶段，不证明任务需求已全部满足。
- 每轮执行完毕、进入下一次模型决策前立即持久化已完成 Trace；取消/超时在决策前后复核，迟到决策不得追加工具。
- Trace.meta 可选追加 `agent_round`、`agent_decision`、`agent_from_step_ids`；SSE 事件名、Trace ID/seq、delta 和 JSON v1.0/Markdown 导出形状兼容。
- 成功任务的用量汇总包含首轮规划、后续决策（包括空列表/被拒绝响应）与最终回答；提供方缺失字段沿用估算规则。没有模型调用的限额终止步骤 token/cost 为 0。
- 多轮任务不生成单轮 checkpoint 快照；`AGENT_MAX_ROUNDS=1` 和已有 checkpoint 分支仍保留原有资格。完整任务分支重跑不受影响。

## Trace Flow 展示契约

- 虚线仅表示实际记录顺序，不推断工具依赖；实线表示 `plan_node_id/depends_on` 声明的依赖，或 `agent_from_step_ids` 的决策来源。
- `parallel_group_id` 相同的工具并排展示，不连接同组相邻工具。
- 同一 plan node ID 按 `agent_round` 隔离，旧 Trace 缺省为首轮。筛选隐藏源节点后，不用邻近节点替代真实依赖。
- 节点展开显示完整内容和服务端返回的 metadata；节点内滚动，避免展开遮挡相邻节点。
- 旧 Trace 继续显示记录顺序；不补造历史依赖、并发或决策信息。

## 知识导入契约

普通文件入口复用后台 RAG 任务，UTF-8、数量/大小和字符预算在浏览器校验；文件名保留为 source/document_id，同名文档新内容保留版本。预览后提交，结果不确定时冻结草稿并重试原载荷/幂等键。复核自动展开目标库，检索测试带入该库，共享写入仍限管理员。详情与使用边界见 [RAG 后台导入](rag-background-ingest.md)。

## 验证与实现位置

2026-10-08：知识文件校验 10/10、Chromium 7/7（桌面/手机、原载荷重试、版本复核/目标库检索、权限、连接和读取竞态），布局复核 2/2；full release gate 10/10（后端 2135/2135、前端 200/200、双构建）。来源 `/tmp/insightagent-knowledge-import-release.md`、`/tmp/insightagent-knowledge-import-e2e.log` 与 `/tmp/insightagent-knowledge-import-layout.log`；本轮业务 API fixture 未代替实际 Chroma/模型验收。

2026-10-07：反馈静态专项 6/6；隔离 PostgreSQL 专项 6/6（本地条件规划、用量、Trace/delta/导出、终止、取消）；前端布局专项 6/6。full release gate 10/10（后端 2135/2135、前端 190/190、双构建），Trace 桌面/390px 手机 Chromium 2/2；步骤恢复回归 9/9、DAG 回归 7/7。验证来源见四份活跃文档。

- `backend/app/services/agent_feedback.py`：反馈协议、有界状态和规划用量汇总。
- `backend/app/services/chat_execution_service.py`：任务生命周期与既有执行器接管。
- `frontend/app/components/workbench/trace-flow-layout.ts` / `trace-flow-view.tsx`：关系派生、布局与完整详情。
- `frontend/app/components/workbench/knowledge-import-modal.tsx` / `knowledge-import-utils.ts`：文件预览/校验；`rag-ingest-jobs.tsx` 复用后台任务与幂等请求，浏览器专项为 `e2e/knowledge-import.spec.ts`。
- `backend/scripts/test_agent_feedback_postgres.py`：隔离数据库验证，无外部模型调用，自动清理容器；已纳入 backend-e2e workflow。
- `frontend/e2e/trace-flow.spec.ts`：仅业务 API fixture 的桌面/手机浏览器交互。

命令遵循 [development-runbook](development-runbook.md)。真实模型分支选择质量、延迟与成本仍待有效 key 验证；本地替身不能代替效果验收。
