import os

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from db import Base, engine
import models  # noqa: F401  (ensures models are registered before create_all)
from routers import collections, drawings, shared_scenes
from sockets import sio

Base.metadata.create_all(bind=engine)


def _run_lightweight_migrations() -> None:
    """create_all() only creates new tables; it never adds columns to an
    existing one. These idempotent ALTERs add the workspace/collection/thumbnail
    columns to the pre-existing `drawings` table (no Alembic yet)."""
    statements = [
        "ALTER TABLE drawings ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL",
        "ALTER TABLE drawings ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES collections(id) ON DELETE SET NULL",
        "ALTER TABLE drawings ADD COLUMN IF NOT EXISTS thumbnail TEXT",
        "CREATE INDEX IF NOT EXISTS ix_drawings_workspace_id ON drawings (workspace_id)",
        "CREATE INDEX IF NOT EXISTS ix_drawings_collection_id ON drawings (collection_id)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


_run_lightweight_migrations()

app = FastAPI(title="AIXDraw API")

CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
allow_origins = (
    ["*"] if CORS_ORIGIN == "*" else [o.strip() for o in CORS_ORIGIN.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drawings.router)
app.include_router(collections.router)
app.include_router(shared_scenes.router)
# Clerk webhooks removed on purpose: platform rule is that Core owns the only
# Clerk webhook subscription; agent apps JIT-mirror on first authed request
# (see auth._ensure_user_exists) gated by the Core /access check.


@app.get("/health")
def health():
    return {"ok": True}


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")
