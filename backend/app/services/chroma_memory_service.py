"""会话级 Memory collection（memory_{session_id}）：状态、写入与向量检索。"""

from __future__ import annotations

from uuid import uuid4

import chromadb

from app.config import get_settings


def memory_collection_name(session_id: str) -> str:
    return f"memory_{session_id}"


def _http_client() -> chromadb.HttpClient:
    settings = get_settings()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )
    client.heartbeat()
    return client


def add_session_memory_text(
    session_id: str,
    text: str,
    *,
    metadatas: dict[str, str] | None = None,
) -> dict[str, object]:
    """get_or_create_collection 后写入一条文档；返回 added_id 与当前条数。"""
    stripped = text.strip()
    if not stripped:
        raise ValueError("text is empty")

    client = _http_client()
    name = memory_collection_name(session_id)
    collection = client.get_or_create_collection(name=name)
    doc_id = str(uuid4())
    meta = metadatas if metadatas is not None else {}
    collection.add(
        documents=[stripped],
        ids=[doc_id],
        metadatas=[meta],
    )
    return {
        "added_id": doc_id,
        "document_count": int(collection.count()),
    }


def query_session_memory(
    session_id: str,
    query_text: str,
    *,
    n_results: int,
) -> dict[str, object]:
    """语义检索；collection 不存在或为空时返回空列表。"""
    q = query_text.strip()
    if not q:
        raise ValueError("query text is empty")

    client = _http_client()
    name = memory_collection_name(session_id)
    try:
        collection = client.get_collection(name=name)
    except Exception:  # noqa: BLE001 — 未创建过 collection
        return {"ids": [], "documents": [], "distances": None, "metadatas": []}

    count = int(collection.count())
    if count == 0:
        return {"ids": [], "documents": [], "distances": None, "metadatas": []}

    k = max(1, min(n_results, count))
    raw = collection.query(query_texts=[q], n_results=k)
    ids = raw.get("ids") or []
    docs_raw = raw.get("documents") or []
    dist = raw.get("distances")
    docs: list[list[str]] = [
        [(s or "") for s in row] for row in docs_raw
    ]
    meta_raw = raw.get("metadatas")
    metadatas = _normalize_query_metadatas(meta_raw, docs)

    return {
        "ids": ids,
        "documents": docs,
        "distances": dist,
        "metadatas": metadatas,
    }


def _normalize_query_metadatas(
    meta_raw: object,
    documents: list[list[str]],
) -> list[list[dict[str, object]]]:
    """与 documents 批次对齐；缺省或 None 的条目补空 dict。"""
    if not documents or not documents[0]:
        return []
    expected = len(documents[0])
    if not meta_raw or not isinstance(meta_raw, (list, tuple)):
        return [[{} for _ in range(expected)]]
    row0 = meta_raw[0] if meta_raw else []
    if not isinstance(row0, (list, tuple)):
        return [[{} for _ in range(expected)]]
    inner: list[dict[str, object]] = []
    for i in range(expected):
        item = row0[i] if i < len(row0) else None
        if item is None:
            inner.append({})
        elif isinstance(item, dict):
            inner.append({str(k): v for k, v in item.items()})
        else:
            inner.append({})
    return [inner]


def try_append_task_memory(
    session_id: str,
    *,
    task_id: str,
    user_prompt: str,
    assistant_excerpt: str,
) -> None:
    """任务成功后 best-effort 写入一条摘要；Chroma 不可用时静默忽略。"""
    excerpt = (assistant_excerpt or "").strip()
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000] + "…"
    up = (user_prompt or "").strip()
    if len(up) > 800:
        up = up[:800] + "…"
    body = f"[task:{task_id}]\nUser: {up}\nAssistant: {excerpt}"
    try:
        add_session_memory_text(
            session_id,
            body,
            metadatas={"task_id": task_id, "kind": "task_summary"},
        )
    except Exception:
        pass


def get_session_memory_status(session_id: str) -> dict[str, object]:
    """
    连接 Chroma HttpClient，心跳成功后读取 collection 是否存在及 document 条数。
    不可达或异常时返回 chroma_reachable=False 与简短 error。
    """
    settings = get_settings()
    name = memory_collection_name(session_id)
    base: dict[str, object] = {
        "collection": name,
        "chroma_url": settings.chroma_http_url,
        "chroma_reachable": False,
        "collection_exists": False,
        "document_count": 0,
        "error": None,
    }

    try:
        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        client.heartbeat()
        base["chroma_reachable"] = True
    except Exception as exc:  # noqa: BLE001 — 对外聚合为只读状态
        msg = str(exc).strip() or type(exc).__name__
        base["error"] = msg[:280]
        return base

    try:
        collection = client.get_collection(name=name)
        base["collection_exists"] = True
        base["document_count"] = int(collection.count())
    except Exception:  # noqa: BLE001 — 无 collection 视为 0 条
        base["collection_exists"] = False
        base["document_count"] = 0

    return base
