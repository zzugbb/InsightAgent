from fastapi import APIRouter

from app.config import get_settings
from app.db import get_sqlite_path
from app.services.chroma_status import probe_chroma_reachable


router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    chroma_url = settings.chroma_http_url
    chroma_reachable: bool | None
    if settings.chroma_probe:
        chroma_reachable = probe_chroma_reachable(chroma_url)
    else:
        chroma_reachable = None

    return {
        "status": "ok",
        "service": "insightagent-backend",
        "environment": settings.app_env,
        "mode": settings.mode,
        "provider": settings.provider,
        "model": settings.model_name,
        "sqlite_path": str(get_sqlite_path()),
        "chroma": {
            "url": chroma_url,
            "reachable": chroma_reachable,
        },
    }
