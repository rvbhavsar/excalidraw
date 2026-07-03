import os

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

CLERK_JWKS_URL = os.environ["CLERK_JWKS_URL"]

_jwk_client = PyJWKClient(CLERK_JWKS_URL)


def _decode(token: str) -> dict:
    signing_key = _jwk_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer ") :]


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        claims = _decode(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    return claims["sub"]


async def get_current_user_id_optional(
    authorization: str | None = Header(default=None),
) -> str | None:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        claims = _decode(token)
    except jwt.PyJWTError:
        return None
    return claims["sub"]


def verify_socket_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _decode(token)["sub"]
    except jwt.PyJWTError:
        return None
