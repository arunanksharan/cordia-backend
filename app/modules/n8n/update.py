from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import uuid
from datetime import datetime
import httpx

from app.core.db import get_session
from app.core.redis import redis_manager
from .schemas import IntakeResponsePayload
from app.modules.conversations.state_service import ConversationStateService

# Import all necessary models
from app.modules.patients.models import Patient
from app.modules.patient_context.models import PatientProfile
from app.modules.intake.models import (
    IntakeSession,
    IntakeChiefComplaint,
    IntakeConditionHistory,
    IntakeAllergy,
    IntakeMedication,
    IntakeFamilyHistory,
    IntakeSymptom
)

router = APIRouter()
logger = logging.getLogger(__name__)

async def trigger_booking(conversation_id: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/api/v1/appointments/book-appointment", json={"conversation_id": conversation_id}, timeout=30.0)
    except httpx.RequestError as e:
        logger.error(f"Failed to trigger booking for conversation {conversation_id}: {e}")

@router.post("/update", status_code=status.HTTP_201_CREATED)
async def update_data(payload: IntakeResponsePayload, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    """
    This endpoint is triggered when an intake conversation is complete.
    It reads the JSON data from the payload and handles the creation of the
    patient, the intake session, and all associated clinical data.
    """
    conversation_id = payload.conversation_id

    # 1. Retrieve the user_id (phone number) from Redis
    user_phone_number = await redis_manager.redis.get(f"conversation_id_map:{conversation_id}")
    if not user_phone_number:
        logger.error(f"Could not find user_id for conversation_id: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found or expired.")

    # For now, we'll use a hardcoded org_id.
    # TODO: Implement a mechanism to determine the org_id dynamically.
    org_id = uuid.UUID("a87e6e1e-c028-4e7c-a06c-12cf5a3c133a")

    try:
        data = payload.data
        patient_data = data.patient
        intake_data = data.intake

        # 2. Find or Create Patient
        patient_result = await db.execute(
            select(Patient).where(Patient.primary_phone == user_phone_number, Patient.org_id == org_id)
        )
        patient = patient_result.scalars().first()

        if not patient:
            patient = Patient(
                org_id=org_id,
                legal_name=patient_data.name,
                primary_phone=user_phone_number
            )
            db.add(patient)
            await db.flush()
            await db.refresh(patient)

        # Store patient_id in Redis for the next step
        state_service = ConversationStateService(str(conversation_id))
        pipe = state_service.redis.pipeline()
        pipe.hset(state_service.extracted_data_key, "patient_id", str(patient.id))
        await pipe.execute()

        # 3. Find or Create Patient Profile (for DOB)
        profile_result = await db.execute(select(PatientProfile).where(PatientProfile.patient_id == patient.id))
        profile = profile_result.scalars().first()

        if not profile:
            profile = PatientProfile(org_id=org_id, patient_id=patient.id)
            db.add(profile)
            await db.flush()

        if patient_data.dob and not profile.dob:
            profile.dob = datetime.strptime(patient_data.dob, '%Y-%m-%d').date()

        # 4. Create Intake Session
        intake_session = IntakeSession(
            org_id=org_id,
            patient_id=patient.id,
            conversation_id=uuid.UUID(conversation_id),
            context=payload.model_dump(),
            status='submitted'
        )
        db.add(intake_session)
        await db.flush()
        await db.refresh(intake_session)

        # 5. Create Clinical Records
        if intake_data.chief_complaint and intake_data.chief_complaint.text and intake_data.chief_complaint.text.lower() != 'none':
            cc = IntakeChiefComplaint(
                org_id=org_id,
                session_id=intake_session.id,
                text=intake_data.chief_complaint.text
            )
            db.add(cc)

        if intake_data.symptoms:
            for item in intake_data.symptoms:
                notes = item.get('notes')
                if notes and notes.lower() != 'none':
                    symptom = IntakeSymptom(org_id=org_id, session_id=intake_session.id, notes=notes)
                    db.add(symptom)

        if intake_data.condition_.history:
            for item in intake_data.condition_history:
                condition = item.get('condition')
                if condition and condition.lower() != 'none':
                    ch = IntakeConditionHistory(org_id=org_id, session_id=intake_session.id, condition=condition)
                    db.add(ch)

        if intake_data.allergies:
            for item in intake_data.allergies:
                substance = item.get('substance')
                if substance and substance.lower() != 'none':
                    allergy = IntakeAllergy(org_id=org_id, session_id=intake_session.id, substance=substance)
                    db.add(allergy)

        if intake_data.medications:
            for item in intake_data.medications:
                name = item.get('name')
                if name and name.lower() != 'none':
                    med = IntakeMedication(org_id=org_id, session_id=intake_session.id, name=name)
                    db.add(med)

        if intake_data.family_history:
            for item in intake_data.family_history:
                condition = item.get('condition')
                relative = item.get('relative')
                if condition and condition.lower() != 'none' and relative and relative.lower() != 'none':
                    fh = IntakeFamilyHistory(
                        org_id=org_id,
                        session_id=intake_session.id,
                        relative=relative,
                        condition=condition
                    )
                    db.add(fh)

        await db.commit()

        # Trigger booking process in the background
        background_tasks.add_task(trigger_booking, conversation_id)

        return {"message": "Patient data processed and saved successfully.", "patient_id": str(patient.id), "intake_session_id": str(intake_session.id)}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing intake data for user {user_phone_number}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing intake data."
        )