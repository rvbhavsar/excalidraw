import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from auth import invalidate_org_cache
from db import get_db
from models import PendingInvite, RoomMember, User, Workspace

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

CLERK_WEBHOOK_SECRET = os.environ["CLERK_WEBHOOK_SECRET"]


@router.post("/clerk")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    try:
        event = Webhook(CLERK_WEBHOOK_SECRET).verify(payload, dict(request.headers))
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}") from exc

    event_type = event.get("type")
    data = event.get("data", {})

    if event_type in ("user.created", "user.updated"):
        user_id = data["id"]
        emails = data.get("email_addresses", [])
        primary_email = next(
            (e["email_address"] for e in emails if e.get("id") == data.get("primary_email_address_id")),
            emails[0]["email_address"] if emails else None,
        )
        user = db.get(User, user_id)
        is_new = user is None
        if not user:
            user = User(id=user_id)
            db.add(user)
        user.email = primary_email.strip().lower() if primary_email else None
        user.username = data.get("username") or data.get("first_name")
        user.avatar_url = data.get("image_url")
        db.commit()

        # convert any pending-by-email invites into real room memberships
        if is_new and primary_email:
            email = primary_email.strip().lower()
            pending = db.query(PendingInvite).filter(PendingInvite.email == email).all()
            for invite in pending:
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
            if pending:
                db.commit()
    elif event_type == "user.deleted":
        user_id = data.get("id")
        if user_id:
            user = db.get(User, user_id)
            if user:
                db.delete(user)
                db.commit()

    elif event_type in ("organization.created", "organization.updated"):
        org_id = data["id"]
        workspace = db.query(Workspace).filter(Workspace.clerk_org_id == org_id).first()
        if not workspace:
            workspace = Workspace(clerk_org_id=org_id)
            db.add(workspace)
        workspace.name = data.get("name") or "Workspace"
        db.commit()

    elif event_type == "organization.deleted":
        org_id = data.get("id")
        if org_id:
            workspace = db.query(Workspace).filter(Workspace.clerk_org_id == org_id).first()
            if workspace:
                db.delete(workspace)
                db.commit()

    elif event_type in ("organizationMembership.created", "organizationMembership.deleted"):
        member_user_id = (data.get("public_user_data") or {}).get("user_id")
        invalidate_org_cache(member_user_id)

    return {"ok": True}
