import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.events.outbox import EventOutbox

router = APIRouter()
async def get_session(): 
    async with SessionLocal() as s: 
        yield s

@router.get("/realtime/events", dependencies=[Depends(require_scopes("realtime:read"))])
async def realtime_events(principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session), after: str | None = None):
    last_seen = datetime.fromisoformat(after) if after else datetime.now(timezone.utc)

    async def event_stream():
        nonlocal last_seen
        while True:
            q = select(EventOutbox).where(
                EventOutbox.org_id==principal.org_id,
                EventOutbox.occurred_at > last_seen,
                EventOutbox.deleted_at.is_(None)
            ).order_by(EventOutbox.occurred_at.asc()).limit(100)
            res = await s.execute(q)
            rows = res.scalars().all()
            for r in rows:
                last_seen = r.occurred_at
                yield f"event: prm\n"
                yield f"data: {{\"type\":\"{r.event_type}\",\"subject\":\"{r.subject_type}:{r.subject_id}\",\"occurred_at\":\"{r.occurred_at.isoformat()}\"}}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")