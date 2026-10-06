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
