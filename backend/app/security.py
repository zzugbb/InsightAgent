from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from app.config import get_settings


_DEFAULT_DEV_JWT_SECRET = "dev-only-change-me"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + pad).encode("ascii"))


def _sign_hs256(message: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def _ensure_jwt_secret_allowed(settings: object) -> None:
    app_env = str(getattr(settings, "app_env", "") or "").strip().lower()
    jwt_secret = str(getattr(settings, "auth_jwt_secret", "") or "")
    if app_env == "production" and jwt_secret == _DEFAULT_DEV_JWT_SECRET:
        raise RuntimeError("default JWT secret is not allowed in production")


def create_access_token(*, user_id: str, email: str) -> str:
    settings = get_settings()
    _ensure_jwt_secret_allowed(settings)
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=int(settings.auth_access_token_ttl_minutes))
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    header_part = _b64url_encode(
        json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    payload_part = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signed_input = f"{header_part}.{payload_part}".encode("ascii")
    sign_part = _b64url_encode(_sign_hs256(signed_input, settings.auth_jwt_secret))
    return f"{header_part}.{payload_part}.{sign_part}"


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    normalized = token.strip()
    if not normalized:
        raise ValueError("refresh token is empty")
    digest = hmac.new(
        _secret_material(),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"v1.{digest}"


def parse_access_token(token: str) -> dict[str, object]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token format")
    header_part, payload_part, sign_part = parts
    header_raw = _b64url_decode(header_part)
    header = json.loads(header_raw.decode("utf-8"))
    if not isinstance(header, dict):
        raise ValueError("invalid token header")
    if header.get("alg") != "HS256":
        raise ValueError("unsupported token algorithm")
    if header.get("typ") != "JWT":
        raise ValueError("invalid token type")

    settings = get_settings()
    _ensure_jwt_secret_allowed(settings)
    signed_input = f"{header_part}.{payload_part}".encode("ascii")
    expected_sign = _sign_hs256(signed_input, settings.auth_jwt_secret)
    given_sign = _b64url_decode(sign_part)
    if not hmac.compare_digest(expected_sign, given_sign):
        raise ValueError("invalid token signature")

    payload_raw = _b64url_decode(payload_part)
    payload = json.loads(payload_raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid token payload")
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise ValueError("token exp missing")
    if int(datetime.now(UTC).timestamp()) >= exp:
        raise ValueError("token expired")
    return payload


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120_000,
    )
    return salt, digest.hex()


def verify_password(password: str, *, salt_hex: str, digest_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000,
    )
    return hmac.compare_digest(actual, expected)


def _secret_material() -> bytes:
    settings = get_settings()
    source = settings.auth_secret_key or settings.auth_jwt_secret
    return hashlib.sha256(source.encode("utf-8")).digest()


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def encrypt_secret(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    raw = plaintext.encode("utf-8")
    if len(raw) == 0:
        return None

    key = _secret_material()
    nonce = secrets.token_bytes(16)
    stream = bytearray()
    counter = 0
    while len(stream) < len(raw):
        block = hmac.new(
            key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        stream.extend(block)
        counter += 1
    cipher = _xor_bytes(raw, bytes(stream[: len(raw)]))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    blob = nonce + cipher + tag
    return f"v1.{_b64url_encode(blob)}"


def decrypt_secret(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    raw = ciphertext.strip()
    if not raw:
        return None
    if not raw.startswith("v1."):
        return None
    data = _b64url_decode(raw[3:])
    if len(data) < 16 + 32:
        return None
    nonce = data[:16]
    tag = data[-32:]
    cipher = data[16:-32]
    key = _secret_material()
    expected_tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        return None
    stream = bytearray()
    counter = 0
    while len(stream) < len(cipher):
        block = hmac.new(
            key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        stream.extend(block)
        counter += 1
    plain = _xor_bytes(cipher, bytes(stream[: len(cipher)]))
    return plain.decode("utf-8")
