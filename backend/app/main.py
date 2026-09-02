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


settings = get_settings()


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
