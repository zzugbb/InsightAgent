from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_current_user
from app.security import create_access_token
from app.services.auth_service import authenticate_user, create_user, is_valid_email


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
    token_type: str = "bearer"
    user: UserSummary


@router.post("/register", response_model=AuthTokenResponse)
def register(payload: RegisterRequest) -> AuthTokenResponse:
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

    token = create_access_token(user_id=user["id"], email=user["email"])
    return AuthTokenResponse(access_token=token, user=UserSummary(**user))


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest) -> AuthTokenResponse:
    user = authenticate_user(email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="email or password is incorrect")
    token = create_access_token(user_id=user["id"], email=user["email"])
    return AuthTokenResponse(access_token=token, user=UserSummary(**user))


@router.get("/me", response_model=UserSummary)
def me(current_user: dict = Depends(get_current_user)) -> UserSummary:
    return UserSummary(**current_user)
