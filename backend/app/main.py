from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.db import initialize_database
from app.services.chat_persistence_service import (
    get_task_execution_owner_id,
    get_task_execution_stale_after_sec,
    recover_orphaned_running_tasks_on_startup,
)
from app.security_headers import add_security_headers


def _validate_cors_origins_for_environment(settings_obj: object) -> None:
    app_env = str(getattr(settings_obj, "app_env", "") or "").strip().lower()
    raw_origins = getattr(settings_obj, "cors_origins", [])
    if isinstance(raw_origins, str):
        origins = [raw_origins]
    else:
        origins = [str(origin) for origin in (raw_origins or [])]
    if app_env == "production" and any(origin.strip() == "*" for origin in origins):
        raise RuntimeError("wildcard CORS origin is not allowed in production")


settings = get_settings()
_validate_cors_origins_for_environment(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    recover_orphaned_running_tasks_on_startup(
        execution_owner_id=get_task_execution_owner_id(settings),
        execution_stale_after_sec=get_task_execution_stale_after_sec(settings),
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_security_headers(app)

app.include_router(api_router)
