from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.deps import get_current_user
from app.services.auth_session_service import (
    issue_auth_tokens,
    list_auth_sessions,
    refresh_auth_tokens,
    revoke_all_auth_sessions,
    revoke_auth_session_by_id,
    revoke_auth_session_by_refresh_token,
)
from app.services.auth_service import authenticate_user, create_user, is_valid_email
from app.services.audit_service import record_audit_event


router = APIRouter()


class UserSummary(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    created_at: str
    updated_at: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    display_name: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not is_valid_email(normalized):
            raise ValueError("invalid email format")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not is_valid_email(normalized):
            raise ValueError("invalid email format")
        return normalized


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    session_id: str
    token_type: str = "bearer"
    user: UserSummary


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=1024)


class LogoutRequest(BaseModel):
    session_id: str | None = None
    refresh_token: str | None = None

    @model_validator(mode="after")
    def _validate_payload(self) -> "LogoutRequest":
        sid = self.session_id.strip() if isinstance(self.session_id, str) else ""
        rt = self.refresh_token.strip() if isinstance(self.refresh_token, str) else ""
        if not sid and not rt:
            raise ValueError("session_id or refresh_token is required")
        self.session_id = sid or None
        self.refresh_token = rt or None
        return self


class LogoutResponse(BaseModel):
    ok: bool = True
    revoked: bool


class LogoutAllResponse(BaseModel):
    ok: bool = True
    revoked: int


class AuthSessionSummary(BaseModel):
    id: str
    active: bool
    created_at: str
    updated_at: str
    expires_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class AuthSessionListResponse(BaseModel):
    items: list[AuthSessionSummary]


def _client_ip(request: Request) -> str | None:
    client = request.client
    if client is None or not client.host:
        return None
    return str(client.host)[:80]


def _user_agent(request: Request) -> str | None:
    raw = request.headers.get("user-agent")
    if raw is None:
        return None
    text = raw.strip()
    return text[:240] if text else None


def _safe_record_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    detail: dict[str, object] | None = None,
) -> None:
    try:
        record_audit_event(user_id=user_id, event_type=event_type, detail=detail)
    except Exception:
        # 审计日志采用 best-effort，不影响主流程成功返回
        return


@router.post("/register", response_model=AuthTokenResponse)
def register(payload: RegisterRequest, request: Request) -> AuthTokenResponse:
    try:
        user = create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        msg = str(exc)
        if "exists" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=422, detail=msg) from exc

    issued = issue_auth_tokens(
        user=user,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    _safe_record_audit_event(
        user_id=str(user["id"]),
        event_type="login",
        detail={
            "reason": "register_auto_login",
            "session_id": str(issued["session_id"]),
        },
    )
    return AuthTokenResponse(
        access_token=str(issued["access_token"]),
        refresh_token=str(issued["refresh_token"]),
        session_id=str(issued["session_id"]),
        user=UserSummary(**user),
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, request: Request) -> AuthTokenResponse:
    user = authenticate_user(email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="email or password is incorrect")
    issued = issue_auth_tokens(
        user=user,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    _safe_record_audit_event(
        user_id=str(user["id"]),
        event_type="login",
        detail={
            "reason": "password",
            "session_id": str(issued["session_id"]),
        },
    )
    return AuthTokenResponse(
        access_token=str(issued["access_token"]),
        refresh_token=str(issued["refresh_token"]),
        session_id=str(issued["session_id"]),
        user=UserSummary(**user),
    )


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: RefreshRequest, request: Request) -> AuthTokenResponse:
    issued = refresh_auth_tokens(
        refresh_token=payload.refresh_token,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    if issued is None:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    user = issued["user"]
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="invalid refresh token user")
    _safe_record_audit_event(
        user_id=str(user["id"]),
        event_type="refresh",
        detail={"session_id": str(issued["session_id"])},
    )
    return AuthTokenResponse(
        access_token=str(issued["access_token"]),
        refresh_token=str(issued["refresh_token"]),
        session_id=str(issued["session_id"]),
        user=UserSummary(**user),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    payload: LogoutRequest,
    current_user: dict = Depends(get_current_user),
) -> LogoutResponse:
    user_id = str(current_user["id"])
    revoked = False
    if payload.session_id:
        revoked = revoke_auth_session_by_id(user_id=user_id, session_id=payload.session_id)
        _safe_record_audit_event(
            user_id=user_id,
            event_type="logout",
            detail={"scope": "single", "session_id": payload.session_id, "revoked": revoked},
        )
    elif payload.refresh_token:
        revoked = revoke_auth_session_by_refresh_token(
            user_id=user_id,
            refresh_token=payload.refresh_token,
        )
        _safe_record_audit_event(
            user_id=user_id,
            event_type="logout",
            detail={"scope": "refresh_token", "revoked": revoked},
        )
    return LogoutResponse(revoked=revoked)


@router.post("/logout-all", response_model=LogoutAllResponse)
def logout_all(current_user: dict = Depends(get_current_user)) -> LogoutAllResponse:
    user_id = str(current_user["id"])
    revoked = revoke_all_auth_sessions(user_id=user_id)
    _safe_record_audit_event(
        user_id=user_id,
        event_type="logout",
        detail={"scope": "all", "revoked": revoked},
    )
    return LogoutAllResponse(revoked=revoked)


@router.get("/sessions", response_model=AuthSessionListResponse)
def get_auth_sessions(current_user: dict = Depends(get_current_user)) -> AuthSessionListResponse:
    rows = list_auth_sessions(user_id=str(current_user["id"]))
    return AuthSessionListResponse(items=[AuthSessionSummary(**row) for row in rows])


@router.delete("/sessions/{session_id}", status_code=204, response_class=Response)
def delete_auth_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> Response:
    revoke_auth_session_by_id(user_id=str(current_user["id"]), session_id=session_id)
    return Response(status_code=204)


@router.get("/me", response_model=UserSummary)
def me(current_user: dict = Depends(get_current_user)) -> UserSummary:
    return UserSummary(**current_user)
