# Backend

当前先提供 W1 最小 FastAPI 入口，后续逐步补齐：

- 配置管理
- 设置页 API
- SSE 流式接口
- SQLite 持久化
- Mock Provider

## 当前已有内容

- `app/config.py`：统一读取环境变量与默认配置
- `app/api/routes/`：已拆出最小路由层
- `app/db.py`：SQLite 初始化、配置表与最小业务表结构
- `app/providers/`：Provider 抽象与 mock 实现骨架
- `app/services/chat_persistence_service.py`：最小会话/任务/消息持久化服务
- `app/services/settings_service.py`：最小 settings 读写服务
- `app/services/provider_service.py`：按 settings 解析当前 provider
- `GET /health`：返回当前运行模式和基础配置
- `POST /api/chat`：最小 JSON 聊天接口，已串起 mock provider
- `POST /api/chat/stream`：最小 SSE 聊天接口，当前支持 `start/state/trace/heartbeat/token/done/error`
- `GET /api/sessions/{session_id}`：读取单个会话
- `GET /api/sessions/{session_id}/messages`：读取会话消息
- `GET /api/settings`：返回非敏感设置摘要，供设置页先联调
- `PUT /api/settings`：写入 SQLite 配置表的最小骨架，并包含 `mock/remote` 基础校验
- `GET /api/tasks/{task_id}`：读取单个任务
- `GET /api/tasks/{task_id}/trace`：读取任务 trace 回放数据
- `GET /api/tasks/{task_id}/trace/delta?after_seq=`：读取 trace 增量数据骨架

## 本地启动

```bash
cd backend
python -m uvicorn app.main:app --reload
```

如需自定义配置，可复制 `.env.example` 为 `.env` 后修改。

## 下一步

下一步继续补最小接口收口：

- 保持现有 SSE 与 trace 接口稳定
- 已完成前端 `trace/delta` 消费，当前进入 task 形态收口前的准备阶段
- 后续优先考虑迁移到主计划里的 `/api/tasks` + `/stream` 形态

## 当前 chat 能力

- 当前同时支持普通 JSON 和最小 SSE 两种响应方式
- 当前已支持最小 SSE，请求体与 JSON chat 相同
- 当前会在请求结束后最小落库 `sessions/tasks/messages`
- 当前只调用 mock provider，不做真实远端调用
- 当前 SSE 事件带最小 `task_id`
- 当前 SSE 已带最小 `step_id`
- 当前 SSE 事件包含 `start`、`state`、`trace`、`heartbeat`、`token`、`done`、`error`
- 当前 `trace` 仅内置 2 个 mock step：1 个 `thought`，1 个 `final_answer` 占位
- 当前 `done` 已包含最小 `usage` 占位，`completion_tokens` 为 mock 估算值
- JSON chat 响应当前会返回 `session_id` 和 `task_id`
- 当前已支持按 `session_id`、`task_id` 读取最小详情、全量 trace 与 delta trace
- 当前 trace 落库时会补最小 `seq` 字段，供 replay / delta 共用
- prompt 中包含 `[mock-error]` 时，可主动触发一次 mock SSE error 分支，便于联调
- 当前前端已可手动消费 `trace/delta`，验证 HTTP 补包契约

## 当前限制

- `api_key` 当前仅做最小存储骨架，尚未加密
- 当前只做最小字段校验：`remote` 模式要求 `api_key`，其余仍未做细粒度 provider 校验
- 暂未做远端连通性检测
- 当前 `trace/delta` 还是基于已落库全量 trace 的读取骨架，尚未实现流式过程中实时增量持久化
- 当前仍未实现 `tool_start/tool_end`、真实 usage、列表/分页查询接口

## 当前数据库结构

- `sessions`：会话主表，先保留 `id/title/created_at/updated_at`
- `tasks`：任务主表，当前包含 `prompt/status/trace_json`
- `messages`：消息表，按 `session_id` 归属，可选关联 `task_id`
- 当前 JSON chat 和最小 SSE 已开始写入这些表，并支持最小按 ID 查询
- `trace_json` 当前保存标准化后的 step 数组，包含最小 `seq`
