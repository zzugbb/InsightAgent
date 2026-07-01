# InsightAgent

InsightAgent 是一个可观测 AI Agent 平台，目标是把「会话 -> 任务执行 -> 轨迹解释 -> Memory / RAG」做成可调试、可回放、可扩展的工程闭环。

## 当前状态

- W1-W4 已完成并收口：会话/任务/消息持久化、SSE 流、Trace 回放与增量同步、Memory、RAG、Token/Cost 展示、基础前后端工作台闭环已可用。
- 当前主线已切到默认工具去 mock 化、真实工具接入，以及 `tool registry / profile / provider source` 治理产品化。
- `tool-runtime-productionization` 已归档，不再把那两份 runtime spec 当作活跃文档维护；当前以代码、三份 README 和本计划文件为准。
- 默认运行策略仍是：配置完整真实 provider/model/api_key 时自动走 `remote`，否则回退 canonical `mock`。
- 最近代码主线已经打通：
  - planner 能规划 real/extra tools 与动态 registry/source 候选。
  - provider / provider source 已支持直接声明 `loader_factory`，file-backed diagnostics 会保留并透传到设置预览、selected source 与 artifacts。
  - tool execution 的规范化输入已贯通到 action step、`tool_start`、runner、success/error step meta。
  - extra/real tool 的 preview/output/result-summary/runtime semantic 已贯通 live trace、持久化 trace、export 与 mock final answer。
  - real/provider retrieval snippet 在缺少 `knowledge_base_id` 时，不再在 rag follow-up 与 task markdown export 中伪造 `default` 本地知识库语义。
  - runtime override real retrieval tool 即使投影出 `hit_count/knowledge_base_id`，result summary 与 observation 也不再误写成默认本地 knowledge-base 命中。
  - mock final answer 的 observation 摘要器在遇到 `provider_search` 这类 runtime override real tool payload 时，也不再把命中误解释为本地 knowledge-base 检索。
  - noncanonical extra/real tool 在未显式声明 `result_output_keys` 但已能推断 preview 语义时，也会同步推断安全 output keys，避免 observation / output 再退回原始 JSON。
  - name-only success-artifact helper 在缺少显式 registry context 时，也会复用 step meta 中已落下的 label / result summary / output_preview，避免 observation 再退回通用名称或原始 JSON。
  - trace/export helper 现在会同时接受 `effective_result_output_keys` 的 `list/tuple` 形态，旁路或旧 trace 里的 safe output 不会再静默丢失。
  - step-meta safe output helper 现在也兼容 `effective_result_output_keys` 的 `list/tuple` 形态，name-only observation fallback 不会因为内部 tuple 旁路而重新泄露原始输出。
  - code-backed provider/source override spec 中的 `result_preview_keys / result_output_keys` 现在也兼容 `list/tuple` 形态，registry 治理入口不会再静默忽略 tuple 配置。
  - runtime helper 的 name-only fallback 也会复用 configured registry，不再静默退回默认内建语义。
- 当前最近一次已记录校验基线：
  - `backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py` 通过（`698/698`）
  - `cd frontend && node --test --experimental-strip-types app/components/workbench/utils.node.test.ts lib/stores/chat-stream-store-utils.node.test.ts app/components/workbench/model-settings-modal-utils.node.test.ts` 通过（`39/39`）
  - `cd frontend && npm run lint` 通过
  - `bash scripts/test_ci_e2e_tooling.sh common` 通过
  - `git diff --check` 通过

## 当前主线

1. 默认工具去 mock 化：优先补“已经能被规划，但执行本体、结果预览、trace/observation/export 仍残留默认 stub 语义”的缺口。
2. 真实工具接入：优先推进 extra/real tools 的执行本体产品化，而不是只停留在 planner payload 兼容。
3. registry / profile / provider source 治理：保持 loader、provider、source、diagnostics、selected source 与 settings summary 一套语义。
4. 契约稳定：外部 SSE / trace / export / e2e 契约尽量不乱改，优先做内部 helper、runtime 与 display 语义收口。

## 阶段 5 已完成基线

- 鉴权与数据层：JWT + refresh 会话管理、用户级设置与密钥加密、PostgreSQL 单后端运行时已落地。
- 基础治理：`RBAC-lite`、`rag-rbac-lite`、shared/private 知识库语义、审计事件扩展已落地。
- 执行可靠性：任务取消/超时、running task 恢复、任务/会话导出、usage dashboard 与主链路 e2e / CI tooling 已落地。
- 当前未完成的重点不是这些基线能力，而是默认工具去 mock 化后的真实执行语义、registry 治理深化与单机并发治理。

## SSE 与 TraceStep 契约（当前实现）

`GET /api/tasks/{task_id}/stream` 的 `event: trace` 中 `data.step` 与 REST `TraceStep` 同构（`id/type/content/meta/seq?`）。

当前 SSE 事件类型：

- `start`
- `state`
- `trace`
- `tool_start`
- `tool_end`
- `heartbeat`
- `token`
- `cancelled`
- `timeout`
- `done`
- `error`

对齐规则：

- SSE 按时间增量发步骤；REST `trace` 返回落库后的完整步骤数组。
- `tool_start/tool_end` 与 `trace` 中的 action 步骤通过同一 `step_id` 对齐。
- 最终 `observation` 在 SSE 中可先为空或阶段性刷新，REST 中返回完整内容。
- 前端实时流、历史 trace 与导出回放都按同一 `TraceStep` 结构消费。

## Memory / Chroma / Embedding 约定（当前实现）

- 会话级 collection：`memory_{session_id}`
- 知识库级 collection：`kb_{user_hash}_{knowledge_base_id}`（用户隔离）
- 后端通过 `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` 连接 Chroma Server
- 默认环境变量：
  - `CHROMA_HOST=127.0.0.1`
  - `CHROMA_PORT=8001`
  - `CHROMA_PROBE=true`
- 当前未在应用层传自定义 embedding function，文本由 Chroma Server 默认策略处理
- Chroma 不可达时：
  - `memory/add`、`memory/query` 返回 503
  - `rag/ingest`、`rag/query` 返回 503
  - 任务结束后的 memory 摘要写入是 best-effort，不阻塞主任务

### 通俗理解：为什么有 RAG 还需要 Memory

- `PostgreSQL`：完整账本，保存会话、消息、任务、trace、usage。
- `Chroma Memory`：当前会话便签本，保存可语义召回的会话记忆片段。
- `Chroma RAG`：长期知识库，保存导入文档的分块内容。

三者分工不同：

- `RAG` 解决“系统知道哪些外部资料”。
- `Memory` 解决“当前会话刚刚确认了什么偏好和约束”。
- `PostgreSQL` 解决“完整历史如何留档和回放”。

## 目录

```text
InsightAgent/
├── backend/
├── frontend/
└── data/
```

## Docker（可选，Chroma）

在仓库根目录启动：

```bash
docker compose up -d chroma
```

默认后端连接 `http://127.0.0.1:8001`。可通过 `GET /health` 检查 `chroma.reachable`。

完整本地栈（backend + frontend + chroma + postgres）可使用：

```bash
docker compose -f compose.full.yml up -d
```

如需一键启动（会自动拉起 `postgres/chroma`，再启动 backend/frontend），可执行：

```bash
./start_insightagent.command
```

## 文档维护约定

- 活跃进度只保留“当前状态、当前主线、最近校验基线、下一步候选”这类高信号内容。
- 长串历史流水账、阶段内小切片和重复能力摘要不再继续堆积到 README。
- 每轮开发完成后同步更新：
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `.cursor/plans/insightagent_开发计划_306e7915.plan.md`
