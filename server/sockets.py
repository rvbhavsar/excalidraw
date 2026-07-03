import socketio

from auth import verify_socket_token
from db import SessionLocal
from models import Drawing, RoomMember

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# socket id -> {"user_id": str, "room_id": str | None, "username": str}
_connections: dict[str, dict] = {}


def _has_access(drawing_id: str, user_id: str) -> bool:
    db = SessionLocal()
    try:
        drawing = db.get(Drawing, drawing_id)
        if not drawing:
            return False
        if drawing.owner_id == user_id:
            return True
        member = (
            db.query(RoomMember)
            .filter(RoomMember.drawing_id == drawing_id, RoomMember.user_id == user_id)
            .first()
        )
        return member is not None
    finally:
        db.close()


@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token")
    user_id = verify_socket_token(token)
    if not user_id:
        raise socketio.exceptions.ConnectionRefusedError("Invalid or missing auth token")
    _connections[sid] = {"user_id": user_id, "room_id": None, "username": (auth or {}).get("username", "Anonymous")}


@sio.event
async def disconnect(sid):
    conn = _connections.pop(sid, None)
    if conn and conn["room_id"]:
        room_id = conn["room_id"]
        await sio.emit(
            "room-user-change",
            _roster(room_id),
            room=room_id,
        )


def _roster(room_id: str) -> list[dict]:
    return [
        {"socketId": sid, "username": c["username"]}
        for sid, c in _connections.items()
        if c["room_id"] == room_id
    ]


@sio.on("join-room")
async def join_room(sid, room_id):
    conn = _connections.get(sid)
    if not conn:
        return
    if not _has_access(room_id, conn["user_id"]):
        await sio.emit("error", {"message": "Not authorized for this room"}, to=sid)
        return

    existing_in_room = _roster(room_id)
    conn["room_id"] = room_id
    await sio.enter_room(sid, room_id)

    if existing_in_room:
        await sio.emit("new-user", sid, room=room_id, skip_sid=sid)
    else:
        await sio.emit("first-in-room", to=sid)

    await sio.emit("room-user-change", _roster(room_id), room=room_id)


@sio.on("server-broadcast")
async def server_broadcast(sid, room_id, payload, iv=None):
    conn = _connections.get(sid)
    if not conn or conn["room_id"] != room_id:
        return
    await sio.emit("client-broadcast", payload, room=room_id, skip_sid=sid)


@sio.on("server-volatile-broadcast")
async def server_volatile_broadcast(sid, room_id, payload, iv=None):
    conn = _connections.get(sid)
    if not conn or conn["room_id"] != room_id:
        return
    await sio.emit("client-broadcast", payload, room=room_id, skip_sid=sid)


@sio.on("user-follow")
async def user_follow(sid, payload):
    await sio.emit("user-follow-room-change", payload, skip_sid=sid)
