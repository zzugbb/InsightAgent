from fastapi import APIRouter

from app.api.routes import auth, health, rag, sessions, settings, tasks


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/api/auth", tags=["auth"])
api_router.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
api_router.include_router(settings.router, prefix="/api/settings", tags=["settings"])
api_router.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
api_router.include_router(rag.router, prefix="/api/rag", tags=["rag"])
