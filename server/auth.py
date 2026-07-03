import os

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from db import get_db
from models import User

CLERK_JWKS_URL = os.environ["CLERK_JWKS_URL"]
CLERK_SECRET_KEY = os.environ["CLERK_SECRET_KEY"]

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


async def _ensure_user_exists(db: Session, user_id: str) -> None:
    """Self-heals the `users` row for accounts that signed up before the
    Clerk webhook was wired up (or if a webhook delivery was ever missed).
    Without this, any endpoint that writes owner_id/user_id as a foreign key
    fails for those accounts."""
    if db.get(User, user_id):
        return
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.clerk.com/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            timeout=5.0,
        )
    response.raise_for_status()
    data = response.json()
    emails = data.get("email_addresses", [])
    primary_email = next(
        (e["email_address"] for e in emails if e.get("id") == data.get("primary_email_address_id")),
        emails[0]["email_address"] if emails else None,
    )
    db.add(
        User(
            id=user_id,
            email=primary_email.strip().lower() if primary_email else None,
            username=data.get("username") or data.get("first_name"),
            avatar_url=data.get("image_url"),
        )
    )
    db.commit()


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        claims = _decode(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    user_id = claims["sub"]
    await _ensure_user_exists(db, user_id)
    return user_id


async def get_current_user_id_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str | None:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        claims = _decode(token)
    except jwt.PyJWTError:
        return None
    user_id = claims["sub"]
    await _ensure_user_exists(db, user_id)
    return user_id


async def verify_socket_token(token: str | None, db: Session) -> str | None:
    if not token:
        return None
    try:
        user_id = _decode(token)["sub"]
    except jwt.PyJWTError:
        return None
    await _ensure_user_exists(db, user_id)
    return user_id
