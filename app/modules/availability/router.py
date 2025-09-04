from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.availability.service import AvailabilityService
from app.modules.availability.schemas import ScheduleCreate, ScheduleOut, SlotsQuery, SlotOut, HoldCreate, HoldOut, BookRequest

router = APIRouter()

async def get_session():
    async with SessionLocal() as s: yield s

def svc(s: AsyncSession = Depends(get_session)) -> AvailabilityService:
    return AvailabilityService(s)

# Admin schedules
@router.post("/availability/schedules", response_model=ScheduleOut, dependencies=[Depends(require_scopes("availability:write"))])
async def create_schedule(payload: ScheduleCreate, principal: Principal = Depends(get_principal), service: AvailabilityService = Depends(svc)):
    return await service.create_schedule(principal.org_id, **payload.model_dump())

@router.get("/availability/schedules", response_model=list[ScheduleOut], dependencies=[Depends(require_scopes("availability:read"))])
async def list_schedules(practitioner_id: uuid.UUID, location_id: uuid.UUID, principal: Principal = Depends(get_principal), service: AvailabilityService = Depends(svc)):
    return await service.list_schedules(principal.org_id, practitioner_id, location_id)

# Slot search
@router.get("/availability/slots", response_model=list[SlotOut], dependencies=[Depends(require_scopes("availability:read"))])
async def search_slots(practitioner_id: uuid.UUID, location_id: uuid.UUID, start: datetime, end: datetime, duration: int = 30, reason_code: str | None = None, principal: Principal = Depends(get_principal), service: AvailabilityService = Depends(svc)):
    q = SlotsQuery(practitioner_id=practitioner_id, location_id=location_id, start=start, end=end, duration=duration, reason_code=reason_code)
    slots = await service.search_slots(principal.org_id, q)
    return slots

# Hold & Book
@router.post("/availability/holds", response_model=HoldOut, dependencies=[Depends(require_scopes("availability:write"))])
async def create_hold(payload: HoldCreate, principal: Principal = Depends(get_principal), service: AvailabilityService = Depends(svc)):
    if payload.slot_id and (payload.start or payload.end):
        raise HTTPException(400, "use slot_id OR start/end")
    if not payload.slot_id and (not payload.start or not payload.end):
        raise HTTPException(400, "provide slot_id or start/end")
    # If client sent a computed slot_id, start/end must be provided by caller or derived externally; in our API we compute slots so clients call with times.
    hold, err = await service.create_hold(
        principal.org_id,
        practitioner_id=payload.practitioner_id,
        location_id=payload.location_id,
        start=payload.start if payload.start else None,
        end=payload.end if payload.end else None,
        patient_id=payload.patient_id,
        intake_session_id=payload.intake_session_id,
    )
    if err: raise HTTPException(409, err)
    return {"hold_token": hold.token, "expires_at": hold.expires_at}

@router.post("/availability/book")
async def book_with_hold(payload: BookRequest, principal: Principal = Depends(get_principal), service: AvailabilityService = Depends(svc)):
    appt, err = await service.book_with_hold(principal.org_id, token=payload.hold_token, patient_id=payload.patient_id, intake_session_id=payload.intake_session_id, reason_code=payload.reason_code, notify_contact=payload.contact)
    if err == "invalid_hold": raise HTTPException(404, err)
    if err == "expired_hold": raise HTTPException(409, err)
    return {
        "appointment_id": str(appt.id),
        "status": appt.status,
        "start": appt.confirmed_start or appt.requested_start,
        "end": appt.confirmed_end or appt.requested_end
    }