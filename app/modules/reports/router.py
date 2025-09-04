from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal

router = APIRouter()
async def get_session(): 
    async with SessionLocal() as s:
        yield s

@router.get("/reports/overview", dependencies=[Depends(require_scopes("reports:read"))])
async def reports_overview(days: int = Query(30, ge=1, le=365), principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    # Simple aggregate queries using SQL text for speed
    org = str(principal.org_id)
    q = text("""
        SELECT
          (SELECT count(*) FROM ticket WHERE org_id=:org AND deleted_at IS NULL AND created_at >= now() - INTERVAL ':days days') AS tickets,
          (SELECT count(*) FROM appointment WHERE org_id=:org AND deleted_at IS NULL AND created_at >= now() - INTERVAL ':days days') AS appointments,
          (SELECT (count(*)::float / NULLIF((SELECT count(*) FROM ticket WHERE org_id=:org AND deleted_at IS NULL AND created_at >= now() - INTERVAL ':days days'),0))::float
             FROM slaplication WHERE org_id=:org AND breach_state='breached') AS sla_breach_rate
    """).bindparams(org=org, days=days)
    res = await s.execute(q)
    r = res.first()
    return {"tickets": r[0], "appointments": r[1], "sla_breach_rate": r[2] or 0.0}