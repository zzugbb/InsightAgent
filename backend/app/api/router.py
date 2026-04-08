from fastapi import APIRouter

from app.api.routes import chat, health, sessions, settings, tasks


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/api/chat", tags=["chat"])
api_router.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
api_router.include_router(settings.router, prefix="/api/settings", tags=["settings"])
api_router.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
