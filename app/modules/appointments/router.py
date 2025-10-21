import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import httpx
import json
from datetime import datetime, timedelta

from app.core.db import SessionLocal, get_session
from app.core.security import get_principal, Principal, require_scopes
from app.modules.appointments.schemas import (
    AppointmentRequest, AppointmentConfirm, AppointmentUpdate, AppointmentStatusChange, AppointmentOut,
    WaitlistCreate, WaitlistUpdate, WaitlistOut,
    CheckinCreate, CheckinOut, BookAppointmentRequest, N8nBookingResponsePayload, N8nDepartmentTriagePayload
)
from app.modules.appointments.service import AppointmentService
from app.modules.conversations.state_service import ConversationStateService
from app.modules.appointments.models import Appointment
from app.modules.patients.models import Patient
from app.core.twilio import twilio_client, TWILIO_PHONE_NUMBER
from app.modules.appointments.booking_logic import (
    handle_confirm_slot,
    handle_reject_slots,
    handle_cancel_booking,
    handle_ambiguous,
)

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> AppointmentService:
    return AppointmentService(session)

# ---- Appointments ----

@router.post("/book-from-department", status_code=status.HTTP_200_OK)
async def book_from_department(
    payload: N8nDepartmentTriagePayload,
    service: AppointmentService = Depends(svc),
):
    """
    This endpoint is triggered by the n8n workflow after the department has been determined.
    """
    return await service.book_from_department(payload)

@router.post("/test-post", status_code=status.HTTP_200_OK)
async def test_post():
    return {"message": "POST request successful"}

@router.post("/book-appointment", status_code=status.HTTP_202_ACCEPTED)
async def book_appointment(
    payload: BookAppointmentRequest,
    service: AppointmentService = Depends(svc),
):
    """
    This endpoint is triggered after an intake conversation is complete.
    It reads the conversation data from Redis, calls an n8n workflow
    to determine the best department, finds an available doctor, and sends
    appointment slots to the user.
    """
    await service.book_appointment_from_intake(str(payload.conversation_id), payload.preferred_time)
    return {"message": "Appointment booking process started."}

@router.post("/handle-n8n-booking-callback", status_code=status.HTTP_200_OK)
async def handle_booking_response(
    payload: N8nBookingResponsePayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    """
    This endpoint is triggered by the n8n workflow after the user has responded to the appointment slots.
    It handles confirming, rejecting, or canceling appointments.
    """
    logger.info(f"Received request to handle booking response for conversation_id: {payload.conversation_id} with method: {request.method}")

    try:
        state_service = ConversationStateService(str(payload.conversation_id))
        extracted_data = await state_service.get_extracted_data()
        user_phone = extracted_data.get("user_phone")

        if not user_phone:
            logger.error(f"Missing user_phone for conversation_id: {payload.conversation_id}")
            return {"message": "Missing user_phone to handle booking response."}

        if payload.booking_response:
            intent = payload.booking_response.intent

            if intent == "confirm_slot":
                return await handle_confirm_slot(payload, db, state_service, extracted_data, user_phone)

            elif intent == "reject_slots":
                return await handle_reject_slots(payload, db, background_tasks)

            elif intent == "cancel_booking":
                return await handle_cancel_booking(payload, db, extracted_data, user_phone)

            elif intent == "ambiguous":
                return await handle_ambiguous(payload, user_phone)

        return {"message": "No booking response found."}

    except Exception as e:
        logger.error(f"Error handling booking response for conversation_id: {payload.conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error handling booking response.")

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