# API 变更记录

记录对外 HTTP/OpenAPI 契约的基线及后续变更；指纹差异需要人工判断兼容性。

## 更新流程

1. 从仓库根目录运行 `backend/.venv/bin/python backend/scripts/check_api_surface.py`。检查已接入后端 full slice；它比较运行时 OpenAPI 的操作和组件指纹，输出变更名称，不输出请求或响应数据。
2. 对每个差异查看运行时 `/openapi.json` 和代码，判断新增、兼容修改或破坏性修改。指纹包含 schema 字段与文档文案，任何差异都需要人工判断，检查通过本身不证明语义兼容。
3. 确认调用方影响、迁移方式与版本策略后，运行 `backend/.venv/bin/python backend/scripts/check_api_surface.py --write --note '具体变更及兼容性结论'` 更新基线并追加记录。若为破坏性变更，在此处补充受影响接口、迁移路径和通知计划。
4. 代码审查同时核对 `backend/api_surface_baseline.json`、本记录及外部 SSE/Trace/export 契约；未纳入 OpenAPI 的运行时行为仍由测试和人工审查验证。

- 2026-09-30 · API 0.1.0：建立试点前 OpenAPI 路由与 schema 指纹基线；后续差异需人工核对兼容性

- 2026-10-06 · API 0.1.0：新增持久化异步 RAG 导入的创建、列表、详情和排队取消接口；保留同步 ingest 及 SSE/Trace/export 契约，新增接口为兼容扩展

- 2026-10-06 · API 0.1.0：后台 RAG 任务新增可空 progress 计数字段，历史记录仍可读取；后台提交新增 5000 切块展开上限，超过上限的原有效请求现返回 422，调用方需分拆请求或降低 overlap。同步 ingest 及 SSE/Trace/export 契约保持不变

- 2026-10-06 · API 0.1.0：新增任务分支重跑 POST/GET /api/tasks/{task_id}/reruns；只允许本人已终结任务创建独立会话，支持幂等与分页来源关系。新任务通过既有 stream 执行，使用当前设置；原任务、任务列表、SSE/Trace/export shape 保持不变，新增接口为兼容扩展

- 2026-10-06 · API 0.1.0：任务内并发为服务端可选模式，默认串行；复用既有 SSE 事件，允许不同工具 step 的事件交错。Trace.meta 新增可选 execution_mode、parallel_group_id、parallel_group_size；既有 meta 允许扩展，JSON v1.0/Markdown 主结构保持稳定，OpenAPI 50 操作 / 86 组件指纹未变。

- 2026-10-06 · API 0.1.0：Provider 显式工具图支持节点 ID、前置依赖和公开预览的标量绑定；旧平铺计划兼容。Trace.meta 新增可选 plan_node_id、depends_on，工具 input 为解析后的实际输入；Trace.seq 按拓扑执行顺序递增。图/输入错误通过既有 SSE error 返回固定 tool_dependency_plan_invalid / tool_dependency_input_unavailable，JSON v1.0/Markdown 外层结构不变，OpenAPI 50 操作 / 86 组件指纹未变。

- 2026-10-07 · API 0.1.0：http_json.execution 新增可选布尔 parallel_read_only，明确声明的固定 GET/无请求体工具可加入既有有界并发；false/缺省继续串行，true 配合不支持的方法/模板/请求体通过既有配置预检拒绝。execution_summary 增加同名可选布尔声明；SSE、Trace/delta、JSON v1.0/Markdown 外层结构及 OpenAPI 50 操作 / 86 组件保持兼容。

- 2026-10-07 · API 0.1.0：新增本人任务实验性 checkpoint 候选查询；分支重跑请求新增可选 checkpoint_step_id，完整重跑、Trace/SSE/export 形状兼容，恢复仅限内建顺序计划；OpenAPI 51 操作 / 88 组件，Trace.meta 的快照/复用信息为可选兼容扩展。

- 2026-10-08 · API 0.1.0：最终回答 Trace.meta 增加可选 agent_stop_reason / provider_finish_reason；成功保存后用既有 trace 事件更新最终步骤，再发送 done。Trace ID 不变、metadata 更新递增 seq；delta/回放/JSON v1.0/Markdown 兼容。completed 表示执行与保存结束，不证明答案或用户目标完整；OpenAPI 51 操作 / 88 组件指纹未变。

- 2026-10-08 · API 0.1.0：会话消息 GET 响应增加可选 nullable completion（seq 与两个白名单结束原因），兼容旧客户端；消息正文及 JSON v1.0/Markdown 导出形状不变，历史提示不再依赖任务分页或筛选；OpenAPI 51 操作 / 89 组件。
