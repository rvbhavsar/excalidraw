import os

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, engine
import models  # noqa: F401  (ensures models are registered before create_all)
from routers import drawings, webhooks
from sockets import sio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIXDraw API")

CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drawings.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"ok": True}


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")
