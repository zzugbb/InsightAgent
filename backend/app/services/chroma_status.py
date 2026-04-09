"""Chroma 可达性探测（占位）：ingest/检索 API 尚未实现，仅服务编排与健康检查。"""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# 不同版本 Chroma 心跳路径；依次尝试
_HEARTBEAT_PATHS = ("/api/v2/heartbeat", "/api/v1/heartbeat")


def probe_chroma_reachable(base_url: str, *, timeout: float = 2.0) -> bool:
    """
    对 Chroma HTTP 服务做轻量 GET；任一已知 heartbeat 返回 2xx 即视为可达。
    """
    base = base_url.rstrip("/")
    for path in _HEARTBEAT_PATHS:
        url = f"{base}{path}"
        try:
            with urlopen(url, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return True
        except (URLError, HTTPError, TimeoutError, OSError):
            continue
    return False
