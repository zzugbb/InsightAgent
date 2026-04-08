from fastapi import APIRouter

from app.config import get_settings
from app.db import get_sqlite_path


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "insightagent-backend",
        "environment": settings.app_env,
        "mode": settings.mode,
        "provider": settings.provider,
        "model": settings.model_name,
        "sqlite_path": str(get_sqlite_path()),
    }
