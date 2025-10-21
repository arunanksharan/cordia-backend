import uuid
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import BackgroundTasks

from app.modules.appointments.schemas import N8nBookingResponsePayload
from app.modules.conversations.state_service import ConversationStateService
from app.modules.appointments.models import Appointment
from app.modules.patients.models import Patient
from app.core.twilio import twilio_client, TWILIO_PHONE_NUMBER
from app.modules.appointments.service import AppointmentService

logger = logging.getLogger(__name__)

async def handle_confirm_slot(
    payload: N8nBookingResponsePayload,
    db: AsyncSession,
    state_service: ConversationStateService,
    extracted_data: dict,
    user_phone: str,
) -> dict:
    patient_id = extracted_data.get("patient_id")
    practitioner_name = extracted_data.get("practitioner_name")
    slot_dates_json = extracted_data.get("slot_dates", "[]")
    slot_dates = json.loads(slot_dates_json)

    if not patient_id or not practitioner_name or not payload.booking_response.preferred_time:
        logger.error(f"Missing data to confirm appointment for conversation_id: {payload.conversation_id}")
        return {"message": "Missing data to confirm appointment."}

    patient_result = await db.execute(select(Patient).where(Patient.id == uuid.UUID(patient_id)))
    patient = patient_result.scalars().first()

    if not patient:
        logger.error(f"Patient not found for id: {patient_id}")
        return {"message": "Patient not found."}
    
    preferred_time_str = payload.booking_response.preferred_time
    selected_slot = None
    for slot_iso in slot_dates:
        slot_dt = datetime.fromisoformat(slot_iso)
        if slot_dt.strftime("%H:%M") == preferred_time_str:
            selected_slot = slot_dt
            break

    if not selected_slot:
        logger.error(f"Could not match preferred_time for conversation_id: {payload.conversation_id}")
        return {"message": "Could not match preferred time."}

    appointment = Appointment(
        org_id=patient.org_id,
        patient_id=patient.id,
        practitioner_name=practitioner_name,
        confirmed_start=selected_slot,
        confirmed_end=selected_slot + timedelta(minutes=30), # Assuming 30 min slot
        status="confirmed",
        channel_origin="whatsapp"
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    pipe = state_service.redis.pipeline()
    pipe.hset(state_service.extracted_data_key, "appointment_id", str(appointment.id))
    await pipe.execute()

    if twilio_client and payload.reply_to_user:
        twilio_client.messages.create(body=payload.reply_to_user, from_=TWILIO_PHONE_NUMBER, to=user_phone)

    return {"message": "Appointment confirmed."}

async def handle_reject_slots(
    payload: N8nBookingResponsePayload,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    service = AppointmentService(db)
    background_tasks.add_task(service.book_appointment_from_intake, str(payload.conversation_id), payload.booking_response.preferred_time)
    return {"message": "Finding new slots."}

async def handle_cancel_booking(
    payload: N8nBookingResponsePayload,
    db: AsyncSession,
    extracted_data: dict,
    user_phone: str,
) -> dict:
    appointment_id = extracted_data.get("appointment_id")
    if not appointment_id:
        logger.error(f"No appointment_id found to cancel for conversation_id: {payload.conversation_id}")
        return {"message": "No appointment found to cancel."}

    appointment_result = await db.execute(select(Appointment).where(Appointment.id == uuid.UUID(appointment_id)))
    appointment = appointment_result.scalars().first()

    if appointment:
        appointment.status = "canceled"
        await db.commit()

        if twilio_client and payload.reply_to_user:
            twilio_client.messages.create(body=payload.reply_to_user, from_=TWILIO_PHONE_NUMBER, to=user_phone)

    return {"message": "Appointment canceled."}

async def handle_ambiguous(
    payload: N8nBookingResponsePayload,
    user_phone: str,
) -> dict:
    if twilio_client and payload.reply_to_user:
        twilio_client.messages.create(body=payload.reply_to_user, from_=TWILIO_PHONE_NUMBER, to=user_phone)
    return {"message": "Sent clarification message."}
