import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import AuthContext, get_current_context, get_user_org_ids
from db import get_db
from models import Collection, Workspace
from services import ensure_workspace

router = APIRouter(prefix="/api", tags=["workspaces"])


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    clerk_org_id: str
    name: str

    class Config:
        from_attributes = True


class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    workspace_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    name: str = "Untitled"
    workspace_id: uuid.UUID | None = None


class CollectionRename(BaseModel):
    name: str


async def _assert_workspace_access(db: Session, user_id: str, workspace_id: uuid.UUID) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.clerk_org_id not in await get_user_org_ids(user_id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return workspace


@router.get("/workspaces", response_model=list[WorkspaceOut])
async def list_workspaces(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
):
    org_ids = await get_user_org_ids(ctx.user_id)
    # self-heal so the active org always resolves to a workspace row
    if ctx.org_id and ctx.org_id in org_ids:
        await ensure_workspace(db, ctx.org_id)
    if not org_ids:
        return []
    return db.query(Workspace).filter(Workspace.clerk_org_id.in_(org_ids)).all()


@router.get("/collections", response_model=list[CollectionOut])
async def list_collections(
    workspace_id: uuid.UUID | None = None,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    if workspace_id is not None:
        await _assert_workspace_access(db, ctx.user_id, workspace_id)
        return db.query(Collection).filter(Collection.workspace_id == workspace_id).all()
    return (
        db.query(Collection)
        .filter(Collection.workspace_id.is_(None), Collection.owner_id == ctx.user_id)
        .all()
    )


@router.post("/collections", response_model=CollectionOut)
async def create_collection(
    body: CollectionCreate,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    if body.workspace_id is not None:
        await _assert_workspace_access(db, ctx.user_id, body.workspace_id)
        collection = Collection(name=body.name, workspace_id=body.workspace_id)
    else:
        collection = Collection(name=body.name, owner_id=ctx.user_id)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
async def rename_collection(
    collection_id: uuid.UUID,
    body: CollectionRename,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    collection = await _get_collection_or_404(db, ctx.user_id, collection_id)
    collection.name = body.name
    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    collection = await _get_collection_or_404(db, ctx.user_id, collection_id)
    db.delete(collection)
    db.commit()
    return {"ok": True}


async def _get_collection_or_404(
    db: Session, user_id: str, collection_id: uuid.UUID
) -> Collection:
    collection = db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.workspace_id is not None:
        await _assert_workspace_access(db, user_id, collection.workspace_id)
    elif collection.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your collection")
    return collection
