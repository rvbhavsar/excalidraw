import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Clerk user id
    email: Mapped[str | None] = mapped_column(String, index=True)
    username: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class Drawing(Base):
    __tablename__ = "drawings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, default="Untitled")
    elements: Mapped[list] = mapped_column(JSONB, default=list)
    app_state: Mapped[dict] = mapped_column(JSONB, default=dict)
    files: Mapped[dict] = mapped_column(JSONB, default=dict)
    scene_version: Mapped[int] = mapped_column(Integer, default=0)
    is_room_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    members: Mapped[list["RoomMember"]] = relationship(
        back_populates="drawing", cascade="all, delete-orphan"
    )
    pending_invites: Mapped[list["PendingInvite"]] = relationship(
        back_populates="drawing", cascade="all, delete-orphan"
    )


class RoomMember(Base):
    __tablename__ = "room_members"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drawings.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, default="editor")  # owner | editor | viewer
    invited_at: Mapped[datetime] = mapped_column(default=_now)

    drawing: Mapped["Drawing"] = relationship(back_populates="members")


class PendingInvite(Base):
    """An invite by email for someone who hasn't signed up yet. Converted into
    a RoomMember automatically the first time they sign in (see webhooks.py)."""

    __tablename__ = "pending_invites"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drawings.id"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String, default="editor")
    invited_at: Mapped[datetime] = mapped_column(default=_now)

    drawing: Mapped["Drawing"] = relationship(back_populates="pending_invites")
