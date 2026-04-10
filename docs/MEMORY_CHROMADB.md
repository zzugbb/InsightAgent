# 会话 Memory 与 Chroma / 嵌入说明

本文说明 InsightAgent 如何将 **会话级向量记忆** 写入 [Chroma](https://www.trychroma.com/)，以及**嵌入（embedding）**由谁负责、当前有哪些限制。实现入口：`backend/app/services/chroma_memory_service.py`、会话 Memory 相关路由 `backend/app/api/routes/sessions.py`。

---

## 1. 数据模型

| 概念 | 约定 |
|------|------|
| Collection 名 | `memory_{session_id}`，与会话一一对应 |
| 文档内容 | `add` 传入的 `text`；`query` 使用 `query_texts` 做语义检索 |
| Metadata | 可选键值（字符串）；任务摘要写入时含 `task_id`、`kind` 等 |

---

## 2. 连接方式

后端使用 **`chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`** 连接 **Chroma Server**（HTTP），与本地 SQLite 业务库分离。

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `CHROMA_HOST` | `127.0.0.1` | 与 Docker 同机开发时使用；若 backend 与 chroma 同 Compose 网络可改为服务名 |
| `CHROMA_PORT` | `8001` | 与仓库根 `docker-compose.yml` 中 **`8001:8000`** 映射一致 |
| `CHROMA_PROBE` | `true` | 为 `false` 时 `/health` 中可不探测 Chroma，避免阻塞 |

本地一键启动向量服务：

```bash
docker compose up -d chroma
```

持久化数据在 Compose 卷 `chroma_data`（见 `docker-compose.yml`）。

---

## 3. 嵌入（embedding）由谁计算

- 业务代码 **未** 在 Python 侧传入自定义 `EmbeddingFunction`；`add_session_memory_text` / `query_session_memory` 将 **纯文本**交给 **已存在于 Chroma Server 上的 collection**。
- 使用 **`get_or_create_collection(name=...)`** 时，**嵌入策略由 Chroma Server 及其版本默认配置决定**（通常对 `documents` / `query_texts` 在服务端编码）。不同 Chroma 镜像版本默认模型可能升级，**不以本仓库锁死某一具体模型名为契约**。
- **当前产品约束**：不在 API 中暴露「切换嵌入模型 / 维度」；若未来需要，应在 **服务端** 显式创建带指定 embedding 的 collection，并同步文档与迁移策略。

---

## 4. API 与行为摘要

| 接口 | 作用 |
|------|------|
| `GET .../memory/status` | 心跳 + `get_collection` + `count`（只读） |
| `POST .../memory/add` | `get_or_create_collection` 后 `add`；可选 `metadata` |
| `POST .../memory/query` | `query`；返回 `documents` / `distances` / `metadatas` 等 |

Chroma 不可达时：`add` / `query` 返回 **503**；`status` 中 `chroma_reachable=false`。任务结束时的 **best-effort** 摘要写入失败时**静默**（不阻塞主任务）。

---

## 5. 与「独立 embedding 配置」的关系（W2 收尾）

- **当前**：依赖 Chroma Server 默认嵌入，配置集中在 **部署镜像 / 环境**，而非应用内多租户开关。
- **后续若要独立配置**：建议新增显式迁移与兼容性说明（重建 collection、或双写过渡期），并在 OpenAPI 中单独建模，**不宜**在现有 `add` 上静默改模型导致向量空间不一致。

---

## 6. 相关文件

| 路径 | 说明 |
|------|------|
| `backend/requirements.txt` | `chromadb` 客户端版本下限 |
| `backend/app/services/chroma_memory_service.py` | HttpClient、add/query/status |
| `docker-compose.yml` | Chroma 服务定义 |

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-04-09 | 初版：连接方式、嵌入职责边界与 W2 收尾对照 |
