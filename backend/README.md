# Backend

基于 FastAPI 的 Agent 后端，当前以 `mock` 模式优先，覆盖任务流、轨迹、会话持久化与会话级 Memory。

## 当前进度

- W1：已完成
- W2：已完成（已收口）
- W3：已完成（mock 范围）
- W4：进行中（真实工具 / RAG 生产化）
- 工程协作：前端 `npm run lint` 已可直接执行，且当前告警已清零
- 协同进展：前端已切换到后端 usage 聚合接口（全局/会话双范围），并显示覆盖率与状态反馈（loading/error/empty）
- 协同进展：前端右侧 Inspector（Context）已按可观测运维场景完成分区重排（概览/同步诊断/用量/Memory/任务索引），后端现有字段可直接支撑后续模块扩展
- 协同进展：前端任务索引已支持本地状态筛选/时间排序/失败置顶，不新增后端接口负担
- 协同进展：前端任务索引已支持标题/ID 快速检索与失败摘要提示（由现有任务字段推导），无需新增后端接口
- 协同进展：前端 Trace 面板已支持步骤类型筛选/关键词检索/类型计数，复用现有 TraceStep 字段，无需新增后端接口
- 协同进展：前端右侧 Inspector 已完成一体化收口（Trace 密度、Context 快速跳转、状态徽标），均基于现有字段推导，无需新增后端接口
- 协同进展：前端左侧与中栏已完成风格收口（导航层级、runtime strip、输入区动效与密度），继续复用现有接口与字段
- 协同进展：前端已按最新交互要求收敛头部占位（移除会话状态胶囊与输入计数提示），继续复用现有接口与字段
- 状态增强：`/api/tasks*` 响应已补充 `status_normalized`、`status_label`、`status_rank`，统一状态语义并保持向后兼容
- W3 增量：mock 工具链路支持可复现错误语义（`[mock-tool-error]` 可恢复重试，`[mock-tool-fatal]` 致命失败），`tool_end/error/trace.meta.tool` 已输出 `retry_count/error`
- W3 优化：新增本地计算器工具 `calc_eval`（支持 `[calc:1+2*3]` 与“计算 1+2*3”触发），纳入统一工具生命周期事件
- W1 优化：新增 `POST /api/settings/validate`，用于设置保存前的结构/连通性预校验（不落库）
- W1 稳定性优化：`remote` 模式保存/校验支持沿用已存储 `api_key`（空值提交不再清空历史密钥）

## 当前已有内容

- `app/config.py`：统一配置读取
- `app/schemas/trace.py`：`TraceStep` / `TraceStepMeta` 与解析校验
- `app/api/routes/`：`health`、`sessions`、`tasks`、`settings`
- `app/db.py`：SQLite 初始化与基础表
- `app/providers/`：Provider 抽象 + mock 实现
- `app/services/chat_execution_service.py`：SSE 任务流（mock 四步 trace）
- 流式阶段已支持最终 `observation` 的批次增量持久化（`seq` 递增，默认每 8 个 chunk 落库一次 + 结束兜底）
- `app/services/chroma_memory_service.py`：会话 Memory 的 status/add/query 与任务后摘要 best-effort 写入
- `tasks.usage_json`：任务完成时持久化 `done.usage`（前端可用于任务列表摘要展示）

## HTTP 接口（摘要）

- `GET /health`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/validate`
- `POST /api/sessions`
- `GET /api/sessions?limit=&offset=`（含 `total/has_more`）
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `GET /api/sessions/{session_id}/memory/status`
- `GET /api/sessions/{session_id}/usage/summary`
- `POST /api/sessions/{session_id}/memory/add`
- `POST /api/sessions/{session_id}/memory/query`
- `POST /api/tasks`
- `GET /api/tasks?limit=&offset=&session_id=`（含 `total/has_more`）
- `GET /api/tasks*` 相关响应包含状态派生字段：`status_normalized`、`status_label`、`status_rank`
- `GET /api/tasks/usage/summary`（可选 `session_id`）
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/stream`
- `GET /api/tasks/{task_id}/trace`
- `GET /api/tasks/{task_id}/trace/delta?after_seq=&limit=`（`limit` 默认 200，最大 500；`has_more` 反映剩余分页或任务仍在运行）

## SSE 与 TraceStep 契约

`GET /api/tasks/{task_id}/stream` 当前事件：
- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `done`
- `error`

其中 `event: trace` 的 `data.step` 与 REST TraceStep 同构（`id/type/content/meta/seq?`）。
`tool_start/tool_end` 使用与 action 节点一致的 `step_id`，可与 trace 节点一一对齐。
当输入包含 `[mock-tool-error]` 时，会先触发一次工具错误并发出 `error(fatal=false,retryCount=1)`，随后自动重试并完成；
当输入包含 `[mock-tool-fatal]` 时，会触发工具致命失败并直接结束任务（`status=failed`）。
当输入包含 `[calc:表达式]`（如 `[calc:1+2*3]`）或文本“计算 1+2*3”时，会触发本地计算器工具并在 Trace 中记录 `input/output/status`。
`trace/delta?after_seq=` 现可在任务流式进行中拉取到最终 `observation` 的阶段性刷新内容。
前端已接入流式期间定时拉取、失败退避重试与流结束补拉，后端接口保持幂等增量语义。
前端 Context 摘要会展示 delta 同步状态/重试次数/最近成功时间，便于联调与问题定位。
当前在连续失败场景下也会显示轻提示，后端接口无需额外状态字段。
并会展示下次重试时间、最近错误内容与恢复提示（短时自动消退），重试中还有秒级倒计时，便于确认故障是否恢复。
页面后台时前端会暂停自动 delta 拉取，返回前台后恢复，不影响接口幂等语义。

## Memory / Chroma / Embedding

- collection 命名：`memory_{session_id}`
- 连接方式：`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- 默认配置：`CHROMA_HOST=127.0.0.1`、`CHROMA_PORT=8001`、`CHROMA_PROBE=true`
- 当前 embedding 边界：应用层未显式传自定义 embedding function，依赖 Chroma Server 默认策略
- Chroma 不可达时：`memory/add`、`memory/query` 返回 503；任务后的摘要写入为 best-effort

## 本地启动

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可复制 `.env.example` 为 `.env` 覆盖默认配置。

如需 Memory 能力，在仓库根目录执行：

```bash
docker compose up -d chroma
```

## 当前限制（W4 生产化前）

- `api_key` 仅最小存储骨架，未加密
- `remote` 模式 provider 校验仍较粗
- 真实工具调用循环与真实 RAG 尚未完全生产化（当前已具备 `tool_start/tool_end` mock 生命周期 + 错误重试语义）
- usage/token/cost 仍是占位增强阶段
- `trace/delta` 当前链路已稳定，后续仅做参数级调优（不影响 W2 已收口）
