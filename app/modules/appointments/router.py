import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, Principal, require_scopes
from app.modules.appointments.schemas import (
    AppointmentRequest, AppointmentConfirm, AppointmentUpdate, AppointmentStatusChange, AppointmentOut,
    WaitlistCreate, WaitlistUpdate, WaitlistOut,
    CheckinCreate, CheckinOut
)
from app.modules.appointments.service import AppointmentService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> AppointmentService:
    return AppointmentService(session)

# ---- Appointments ----

@router.post("/appointments", response_model=AppointmentOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def request_appointment(
    payload: AppointmentRequest,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.request(principal.org_id, payload)
    return obj

@router.post("/appointments/{appointment_id}/confirm", response_model=AppointmentOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def confirm_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentConfirm,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.confirm(principal.org_id, appointment_id, payload)
    if not obj:
        raise HTTPException(status_code=400, detail="Cannot confirm appointment in current state or not found")
    return obj

@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.update_fields(principal.org_id, appointment_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Appointment not found or not updatable")
    return obj

@router.post("/appointments/{appointment_id}/status", response_model=AppointmentOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def change_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusChange,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.change_status(principal.org_id, appointment_id, payload)
    if not obj:
        raise HTTPException(status_code=400, detail="Invalid status transition or not found")
    return obj

@router.get("/appointments/{appointment_id}", response_model=AppointmentOut, dependencies=[Depends(require_scopes("appointments:read"))])
async def get_appointment(
    appointment_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.get(principal.org_id, appointment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return obj

@router.get("/appointments", response_model=list[AppointmentOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def list_appointments(
    status: str | None = Query(default=None, pattern="^(requested|pending_confirm|confirmed|rescheduled|canceled|no_show|completed)$"),
    patient_id: uuid.UUID | None = None,
    limit: int = 50, offset: int = 0,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    return await service.list(principal.org_id, status=status, patient_id=patient_id, limit=limit, offset=offset)

# ---- Waitlist ----

@router.post("/waitlist", response_model=WaitlistOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def add_waitlist(
    payload: WaitlistCreate,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    return await service.waitlist_add(principal.org_id, payload)

@router.patch("/waitlist/{waitlist_id}", response_model=WaitlistOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def update_waitlist(
    waitlist_id: uuid.UUID,
    payload: WaitlistUpdate,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.waitlist_update(principal.org_id, waitlist_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return obj

@router.get("/waitlist/suggest", response_model=list[WaitlistOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def suggest_waitlist(
    location_name: str | None = None,
    reason_code: str | None = None,
    limit: int = 10,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    return await service.waitlist_suggest(principal.org_id, location_name=location_name, reason_code=reason_code, limit=limit)

# ---- Check-in ----

@router.post("/appointments/{appointment_id}/checkin", response_model=CheckinOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def checkin(
    appointment_id: uuid.UUID,
    payload: CheckinCreate,
    principal: Principal = Depends(get_principal),
    service: AppointmentService = Depends(svc),
):
    obj = await service.checkin(principal.org_id, appointment_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return obj