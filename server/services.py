import uuid

from sqlalchemy.orm import Session

from auth import fetch_org_name
from models import Workspace


async def ensure_workspace(db: Session, org_id: str) -> Workspace:
    """Self-heals the workspace row for a Clerk org the first time we see it,
    so we don't depend on the org webhook having fired first."""
    workspace = db.query(Workspace).filter(Workspace.clerk_org_id == org_id).first()
    if workspace:
        return workspace
    workspace = Workspace(id=uuid.uuid4(), clerk_org_id=org_id, name=await fetch_org_name(org_id))
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace
