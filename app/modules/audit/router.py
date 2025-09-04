from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.security import get_principal, Principal, require_scopes
from app.modules.audit.models import AuditEvent

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

@router.get("/audit", dependencies=[Depends(require_scopes("audit:read"))])
async def list_audit(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
):
    q = select(AuditEvent).where(
        AuditEvent.org_id == principal.org_id,
        AuditEvent.deleted_at.is_(None),
    ).order_by(desc(AuditEvent.created_at)).limit(limit)
    res = await session.execute(q)
    # Return raw dicts for simplicity
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "actor_user_id": row.actor_user_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "purpose": row.purpose,
            "success": row.success,
            "occurred_at": row.occurred_at,
        }
        for row in res.scalars().all()
    ]