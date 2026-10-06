# RAG 后台导入

后台导入将文档请求先保存到 PostgreSQL，返回任务后由独立 worker 写入 Chroma。运行调试窗口的「后台导入」使用当前知识库、文本和来源，最近任务显示排队、导入中、完成、失败或取消；关闭窗口不影响已受理任务，再打开或刷新页面可继续查看。同步 `POST /api/rag/ingest` 继续可用。

## HTTP 契约

| 接口 | 行为 |
| --- | --- |
| `POST /api/rag/ingest-jobs` | 接受原 ingest 参数及可选 UUID `idempotency_key`，返回 HTTP 202 与任务状态。未提供键时服务端生成。 |
| `GET /api/rag/ingest-jobs?knowledge_base_id=default&limit=20` | 返回当前用户的最近任务；可省略知识库条件，limit 为 1–100，活跃任务优先。 |
| `GET /api/rag/ingest-jobs/{job_id}` | 返回当前用户拥有的任务；不存在或属于他人时均为 404。 |
| `POST /api/rag/ingest-jobs/{job_id}/cancel` | 只取消排队任务；重复取消返回相同状态，已开始或已终结的其他任务返回 409。 |

提交示例：

```json
{
  "idempotency_key": "00000000-0000-4000-8000-000000000001",
  "knowledge_base_id": "default",
  "documents": [{"text": "待导入文本", "source": "handbook.md"}],
  "chunk_size": 500,
  "chunk_overlap": 80
}
```

返回字段为 `id`、`knowledge_base_id`、`document_total`、`status`、`created_at`、`started_at`、`finished_at`、`result` 与 `error_code`。只有完成状态包含既有 `RagIngestResponse` 计数结果；查询结果不包含文档文本、metadata、请求幂等键或内部用户身份。

- 同一用户使用同一幂等键和相同参数再次提交，会返回原任务，包括其终结状态；同键不同参数返回 `409 ingest_idempotency_conflict`。网络结果不确定时应复用原键，重新导入须使用新键。
- 每用户最多 3 个排队/执行中任务，达到限额返回 `429 ingest_queue_full`。最多 100 个文档、每文档 64,000 字符、总文本 512,000 字符；完整序列化请求最多 1,000,000 字节，超出返回 `413 ingest_payload_too_large`。空白文本与无效切块参数返回 422。
- 私有知识库沿用用户隔离；共享库提交仍限管理员，执行前再次核对当前角色，权限失效返回失败状态 `permission_revoked`。导入任务记录始终只对提交者可见。

## 执行、恢复和数据保留

数据库初始化新增 `rag_ingest_jobs` 表与索引；每个 API 实例启动一个常驻 worker 子进程。worker 通过 `FOR UPDATE SKIP LOCKED` 领取任务，并在外部写入期间持有该任务的 PostgreSQL 会话 advisory lock，避免多个实例重复执行或误判活跃任务中断。部署使用直连 PostgreSQL；若加入连接池，须支持会话锁并采用 session pooling。

- 排队任务跨重启保留，重新启动后继续领取。
- 执行中的任务若因进程退出失去会话锁，下一次恢复扫描将其标记为 `failed / interrupted`。Chroma 写入与 PostgreSQL 状态更新没有分布式事务，因此失败任务可能已有部分数据，必须先复核知识库再决定是否重新提交；worker 不自动重放失败任务。
- `RAG_INGEST_JOB_TIMEOUT_SEC` 默认 300 秒，可设 1–3600 秒。父进程在 worker 开始任务后等待固定心跳；超时会杀掉子进程并重建，未终结任务随后按中断恢复。API 正常关闭或被强制终止时，worker 会退出并释放锁。
- 原始文档与 metadata 暂存于 PostgreSQL 的 `payload_json`，完成、失败、取消或中断恢复时清除。终结任务保留低敏状态和结果计数；数据库备份仍须按业务数据的访问与保留策略管理。
- 审计事件为 `rag_ingest_job_created`、`rag_ingest_job_cancelled`、`rag_ingest_job_finished`，仅记录任务 ID、规范化知识库、结果状态/固定错误码等摘要，不记录文档内容或上游异常正文。

固定失败码为 `invalid_input`、`chroma_unavailable`、`interrupted`、`permission_revoked`。`chroma_unavailable` 表示本次写入未完整确认，不能据此断言没有写入数据。

## 验证与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k rag_ingest_job
# 需要 Docker 与本机端口；仅创建临时 PostgreSQL，自动删除容器和测试卷
backend/.venv/bin/python backend/scripts/test_rag_ingest_postgres.py
# 需要已启动的本地 backend/frontend 和 Chroma
cd frontend
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 \
  npm run test:e2e -- e2e/rag-ingest-jobs.spec.ts
```

数据库集成测试已接入 `backend-e2e` workflow；前端完整 Chromium 自动发现新增场景。实现按职责分为路由、schema、持久化队列、worker 和监管模块，继续保持主题文件规模边界。当前验证覆盖本地 PostgreSQL/Chroma 与单机多 worker；目标部署、真实大批量导入性能及用户签收仍待实证。
