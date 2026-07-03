import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import get_current_user_id
from db import get_db
from models import Drawing, RoomMember, User

router = APIRouter(prefix="/api/drawings", tags=["drawings"])


class DrawingSummary(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: str
    role: str

    class Config:
        from_attributes = True


class DrawingCreate(BaseModel):
    title: str = "Untitled"


class DrawingSave(BaseModel):
    title: str | None = None
    elements: list
    app_state: dict = {}
    files: dict = {}
    scene_version: int


class DrawingOut(BaseModel):
    id: uuid.UUID
    title: str
    elements: list
    app_state: dict
    files: dict
    scene_version: int
    is_room_active: bool
    role: str

    class Config:
        from_attributes = True


class MemberInvite(BaseModel):
    email: str
    role: str = "editor"


def _role_for(drawing: Drawing, user_id: str) -> str | None:
    if drawing.owner_id == user_id:
        return "owner"
    for m in drawing.members:
        if m.user_id == user_id:
            return m.role
    return None


def _get_drawing_or_404(db: Session, drawing_id: uuid.UUID, user_id: str) -> tuple[Drawing, str]:
    drawing = db.get(Drawing, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    role = _role_for(drawing, user_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this drawing")
    return drawing, role


@router.get("", response_model=list[DrawingSummary])
def list_drawings(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    owned = db.query(Drawing).filter(Drawing.owner_id == user_id).all()
    shared_ids = [
        m.drawing_id for m in db.query(RoomMember).filter(RoomMember.user_id == user_id).all()
    ]
    shared = db.query(Drawing).filter(Drawing.id.in_(shared_ids)).all() if shared_ids else []

    results = []
    for d in owned:
        results.append(DrawingSummary(id=d.id, title=d.title, updated_at=d.updated_at.isoformat(), role="owner"))
    for d in shared:
        role = _role_for(d, user_id) or "editor"
        results.append(DrawingSummary(id=d.id, title=d.title, updated_at=d.updated_at.isoformat(), role=role))
    return results


@router.post("", response_model=DrawingOut)
def create_drawing(
    body: DrawingCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing = Drawing(owner_id=user_id, title=body.title, elements=[], app_state={}, files={})
    db.add(drawing)
    db.commit()
    db.refresh(drawing)
    return DrawingOut(
        id=drawing.id,
        title=drawing.title,
        elements=drawing.elements,
        app_state=drawing.app_state,
        files=drawing.files,
        scene_version=drawing.scene_version,
        is_room_active=drawing.is_room_active,
        role="owner",
    )


@router.get("/{drawing_id}", response_model=DrawingOut)
def get_drawing(
    drawing_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing, role = _get_drawing_or_404(db, drawing_id, user_id)
    return DrawingOut(
        id=drawing.id,
        title=drawing.title,
        elements=drawing.elements,
        app_state=drawing.app_state,
        files=drawing.files,
        scene_version=drawing.scene_version,
        is_room_active=drawing.is_room_active,
        role=role,
    )


@router.put("/{drawing_id}", response_model=DrawingOut)
def save_drawing(
    drawing_id: uuid.UUID,
    body: DrawingSave,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing, role = _get_drawing_or_404(db, drawing_id, user_id)
    if role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Read-only access")
    if body.scene_version < drawing.scene_version:
        # stale write, return current authoritative state instead of overwriting
        return DrawingOut(
            id=drawing.id,
            title=drawing.title,
            elements=drawing.elements,
            app_state=drawing.app_state,
            files=drawing.files,
            scene_version=drawing.scene_version,
            is_room_active=drawing.is_room_active,
            role=role,
        )
    if body.title is not None:
        drawing.title = body.title
    drawing.elements = body.elements
    drawing.app_state = body.app_state
    drawing.files = {**drawing.files, **body.files}
    drawing.scene_version = body.scene_version
    db.commit()
    db.refresh(drawing)
    return DrawingOut(
        id=drawing.id,
        title=drawing.title,
        elements=drawing.elements,
        app_state=drawing.app_state,
        files=drawing.files,
        scene_version=drawing.scene_version,
        is_room_active=drawing.is_room_active,
        role=role,
    )


@router.delete("/{drawing_id}")
def delete_drawing(
    drawing_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing, role = _get_drawing_or_404(db, drawing_id, user_id)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can delete")
    db.delete(drawing)
    db.commit()
    return {"ok": True}


@router.post("/{drawing_id}/members")
def invite_member(
    drawing_id: uuid.UUID,
    body: MemberInvite,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing, role = _get_drawing_or_404(db, drawing_id, user_id)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can invite")
    invitee = db.query(User).filter(User.email == body.email).first()
    if not invitee:
        raise HTTPException(
            status_code=404,
            detail="No AIXDraw account found for that email — they need to sign up first",
        )
    existing = (
        db.query(RoomMember)
        .filter(RoomMember.drawing_id == drawing_id, RoomMember.user_id == invitee.id)
        .first()
    )
    if existing:
        existing.role = body.role
    else:
        db.add(RoomMember(drawing_id=drawing_id, user_id=invitee.id, role=body.role))
    drawing.is_room_active = True
    db.commit()
    return {"ok": True}


@router.delete("/{drawing_id}/members/{member_user_id}")
def remove_member(
    drawing_id: uuid.UUID,
    member_user_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    drawing, role = _get_drawing_or_404(db, drawing_id, user_id)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can remove members")
    db.query(RoomMember).filter(
        RoomMember.drawing_id == drawing_id, RoomMember.user_id == member_user_id
    ).delete()
    db.commit()
    return {"ok": True}
