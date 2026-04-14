from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import parse_access_token
from app.services.auth_service import get_user_by_id


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = parse_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=401,
            detail=str(exc) or "invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=401,
            detail="invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_id(user_id.strip())
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
