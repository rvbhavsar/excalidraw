import secrets

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db import get_db
from models import SharedScene

# The client posts to `${BACKEND_V2_POST_URL}` (= .../api/v2/post/) and reads
# from `${BACKEND_V2_GET_URL}${id}` (= .../api/v2/{id}). This mirrors the shape
# of excalidraw's public json backend so the frontend's exportToBackend /
# importFromBackend work unchanged.
router = APIRouter(prefix="/api/v2", tags=["share-links"])

# The blob is already compressed + encrypted client-side; this cap only guards
# against abuse. Matches the client's RequestTooLargeError handling branch.
MAX_SCENE_BYTES = 8 * 1024 * 1024


@router.post("/post/")
async def create_shared_scene(request: Request, db: Session = Depends(get_db)):
    data = await request.body()
    if len(data) > MAX_SCENE_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error_class": "RequestTooLargeError"},
        )
    scene_id = secrets.token_hex(16)
    db.add(SharedScene(id=scene_id, data=data))
    db.commit()
    return {"id": scene_id}


@router.get("/{scene_id}")
def get_shared_scene(scene_id: str, db: Session = Depends(get_db)):
    scene = db.get(SharedScene, scene_id)
    if scene is None:
        return Response(status_code=404)
    return Response(content=scene.data, media_type="application/octet-stream")
