"""AIX Core entitlement gate.

AIXDraw never stores its own access table. Every privileged request calls
Core's `/api/v1/agents/aixdraw/access` with the user's JWT and trusts the
answer. Fail-closed: Core unreachable, 5xx, or agent missing from the
catalog all deny (503) rather than grant.

See Docs/core-platform/handoff (agent ↔ AIX Core auth integration) for the
full contract.
"""

import os
import time

import httpx
from fastapi import HTTPException

# Catalog id of this agent in Core's agents.catalog.
AGENT_ID = "aixdraw"
AIX_CORE_API_URL = os.environ["AIX_CORE_API_URL"].rstrip("/")

# user_id -> (has_access, reason, checked_at). TTL must stay <= 60s: any
# longer leaves users with stale access after an org admin revokes.
_ACCESS_CACHE: dict[str, tuple[bool, str | None, float]] = {}
_ACCESS_CACHE_TTL = 60.0


async def check_core_access(user_id: str, token: str) -> None:
    """Raise unless AIX Core says this user may use AIXDraw.

    401 -> token rejected by Core; 503 -> Core unavailable or agent not in
    catalog (fail closed); 403 -> valid user without entitlement.
    """
    cached = _ACCESS_CACHE.get(user_id)
    if cached and (time.time() - cached[2]) < _ACCESS_CACHE_TTL:
        has_access, reason = cached[0], cached[1]
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{AIX_CORE_API_URL}/api/v1/agents/{AGENT_ID}/access",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise HTTPException(503, "AIX Core access check unavailable") from exc
        if response.status_code == 401:
            raise HTTPException(401, "Token rejected by AIX Core")
        if response.status_code == 404:
            raise HTTPException(503, f"{AGENT_ID} is not registered in the AIX Core catalog")
        if response.status_code >= 500:
            raise HTTPException(503, f"AIX Core access check failed: {response.status_code}")
        data = response.json()
        has_access, reason = bool(data.get("has_access")), data.get("reason")
        # only definitive answers are cached; errors above always retry
        _ACCESS_CACHE[user_id] = (has_access, reason, time.time())
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "no_agent_access",
                "reason": reason,
                "message": "You don't have access to AIXDraw. Ask your org admin to grant access from the AIX Core dashboard.",
            },
        )


async def socket_has_access(user_id: str, token: str) -> bool:
    """Boolean variant for the socket.io connect handler (no HTTP context)."""
    try:
        await check_core_access(user_id, token)
        return True
    except HTTPException:
        return False


def invalidate_access_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _ACCESS_CACHE.clear()
    else:
        _ACCESS_CACHE.pop(user_id, None)
