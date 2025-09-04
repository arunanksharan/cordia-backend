import csv, io, json, uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.tickets.models import Ticket
from app.modules.appointments.models import Appointment
from app.modules.conversations.models import Message

router = APIRouter()
async def get_session():
    async with SessionLocal() as s: yield s

def _ndjson(rows):
    def gen():
        for r in rows: yield (json.dumps(r) + "\n").encode("utf-8")
    return StreamingResponse(gen(), media_type="application/x-ndjson")

@router.get("/exports/tickets.ndjson", dependencies=[Depends(require_scopes("exports:read"))])
async def export_tickets(principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Ticket).where(Ticket.org_id==principal.org_id, Ticket.deleted_at.is_(None)))
    rows = [{"id":str(t.id),"category":t.category,"status":t.status,"priority":t.priority,"created_at":t.created_at.isoformat()} for t in res.scalars().all()]
    return _ndjson(rows)

@router.get("/exports/appointments.csv", dependencies=[Depends(require_scopes("exports:read"))])
async def export_appointments_csv(principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Appointment).where(Appointment.org_id==principal.org_id, Appointment.deleted_at.is_(None)))
    out = io.StringIO(); w = csv.writer(out); w.writerow(["id","status","start","end","location","patient_id"])
    for a in res.scalars().all():
        w.writerow([str(a.id), a.status, (a.confirmed_start or a.requested_start), (a.confirmed_end or a.requested_end), a.location_name, a.patient_id])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv")