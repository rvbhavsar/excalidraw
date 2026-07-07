import os
import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from core_access import check_core_access, socket_has_access
from db import get_db
from models import PendingInvite, RoomMember, User

CLERK_JWKS_URL = os.environ["CLERK_JWKS_URL"]
CLERK_SECRET_KEY = os.environ["CLERK_SECRET_KEY"]

_jwk_client = PyJWKClient(CLERK_JWKS_URL)

# user_id -> (set of clerk org ids, fetched_at epoch). Short TTL so team access
# reflects membership changes without a Clerk round-trip on every request.
_ORG_CACHE: dict[str, tuple[set[str], float]] = {}
_ORG_CACHE_TTL = 60.0


@dataclass
class AuthContext:
    user_id: str
    org_id: str | None  # the active organization on the request's token, if any


def _extract_org_id(claims: dict) -> str | None:
    return claims.get("org_id") or (claims.get("o") or {}).get("id")


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
    """JIT-mirrors the `users` row on a user's first authed request (the
    platform pattern: agent apps do NOT subscribe to Clerk webhooks; Core
    owns the only webhook subscription). Without this, any endpoint that
    writes owner_id/user_id as a foreign key fails for new accounts."""
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
    email = primary_email.strip().lower() if primary_email else None
    db.add(
        User(
            id=user_id,
            email=email,
            username=data.get("username") or data.get("first_name"),
            avatar_url=data.get("image_url"),
        )
    )
    # convert any pending-by-email invites into real room memberships —
    # this used to happen in the Clerk user.created webhook; the JIT create
    # IS the "user just appeared" moment now
    if email:
        for invite in db.query(PendingInvite).filter(PendingInvite.email == email).all():
            existing = (
                db.query(RoomMember)
                .filter(
                    RoomMember.drawing_id == invite.drawing_id,
                    RoomMember.user_id == user_id,
                )
                .first()
            )
            if not existing:
                db.add(
                    RoomMember(
                        drawing_id=invite.drawing_id, user_id=user_id, role=invite.role
                    )
                )
            db.delete(invite)
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
    await check_core_access(user_id, token)  # entitlement gate, fail-closed
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


async def get_current_context(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthContext:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        claims = _decode(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    user_id = claims["sub"]
    await check_core_access(user_id, token)  # entitlement gate, fail-closed
    await _ensure_user_exists(db, user_id)
    return AuthContext(user_id=user_id, org_id=_extract_org_id(claims))


async def get_user_org_ids(user_id: str) -> set[str]:
    """All Clerk org ids the user belongs to, cached briefly. Used for access
    control so a user reaches team drawings regardless of their active org."""
    cached = _ORG_CACHE.get(user_id)
    if cached and (time.time() - cached[1]) < _ORG_CACHE_TTL:
        return cached[0]
    org_ids: set[str] = set()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.clerk.com/v1/users/{user_id}/organization_memberships",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            params={"limit": 100},
            timeout=5.0,
        )
    if response.status_code != 200:
        # don't cache a failure — that would lock the user out of their own team
        # drawings for the whole TTL on a single transient Clerk blip
        return cached[0] if cached else org_ids
    data = response.json()
    rows = data.get("data", data) if isinstance(data, dict) else data
    for row in rows or []:
        org = row.get("organization") or {}
        if org.get("id"):
            org_ids.add(org["id"])
    _ORG_CACHE[user_id] = (org_ids, time.time())
    return org_ids


def invalidate_org_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _ORG_CACHE.clear()
    else:
        _ORG_CACHE.pop(user_id, None)


async def fetch_org_name(org_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.clerk.com/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            timeout=5.0,
        )
    if response.status_code == 200:
        return response.json().get("name") or "Workspace"
    return "Workspace"


async def verify_socket_token(token: str | None, db: Session) -> str | None:
    if not token:
        return None
    try:
        user_id = _decode(token)["sub"]
    except jwt.PyJWTError:
        return None
    if not await socket_has_access(user_id, token):
        return None  # connect handler refuses unauthenticated connections
    await _ensure_user_exists(db, user_id)
    return user_id
