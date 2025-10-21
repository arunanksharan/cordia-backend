
import json
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

from app.modules.conversations.state_service import ConversationStateService
from app.modules.patients.models import Patient
from app.modules.patient_context.models import PatientProfile
from app.modules.conversations.models import Conversation # Import Conversation model
from app.modules.intake.models import (
    IntakeSession,
    IntakeChiefComplaint,
    IntakeSymptom,
    IntakeConditionHistory,
    IntakeAllergy,
    IntakeMedication,
    IntakeFamilyHistory
)

logger = logging.getLogger(__name__)

async def save_intake_from_redis(conversation_id: str, db: AsyncSession):
    """
    Orchestrates the final saving of a completed intake conversation from Redis to PostgreSQL.
    """
    logger.info(f"Starting final save process for conversation {conversation_id}")
    state_service = ConversationStateService(conversation_id)
    
    try:
        extracted_data = await state_service.get_extracted_data()
        if not extracted_data:
            logger.warning(f"No extracted data found for conversation {conversation_id}. Aborting save.")
            return

        # --- Extract Data ---
        user_phone = extracted_data.get("user_phone")
        if not user_phone:
            logger.error(f"user_phone not found in extracted_data for {conversation_id}. Cannot save.")
            return

        # Using a hardcoded org_id as requested.
        org_id = uuid.UUID("a87e6e1e-c028-4e7c-a06c-12cf5a3c133a")

        # --- 1. Find or Create Patient ---
        patient_result = await db.execute(
            select(Patient).where(Patient.primary_phone == user_phone, Patient.org_id == org_id)
        )
        patient = patient_result.scalars().first()

        if not patient:
            patient_name = extracted_data.get("patient.name", "Unknown Patient")
            patient = Patient(org_id=org_id, legal_name=patient_name, primary_phone=user_phone)
            db.add(patient)
            await db.flush()
            await db.refresh(patient)
            logger.info(f"Created new patient {patient.id} for phone {user_phone}")
        
        # Save patient_id to Redis extracted_data
        await state_service.redis.hset(state_service.extracted_data_key, "patient_id", str(patient.id))

        # Save patient_id to Redis extracted_data
        await state_service.redis.hset(state_service.extracted_data_key, "patient_id", str(patient.id))

        # --- 2. Find or Create Conversation record ---
        conversation_uuid = uuid.UUID(conversation_id)
        conversation_result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_uuid)
        )
        new_conversation = conversation_result.scalars().first()

        if not new_conversation:
            new_conversation = Conversation(
                id=conversation_uuid,
                org_id=org_id,
                patient_id=patient.id,
                status="closed"  # Since the intake is complete
            )
            db.add(new_conversation)
            await db.flush() # Flush to ensure the conversation is in the session for the intake session FK
        else:
            # Optionally, update the status if it was open before
            if new_conversation.status != "closed":
                new_conversation.status = "closed"


        # --- 3. Find or Create Patient Profile (DOB) ---
        dob_str = extracted_data.get("patient.dob")
        if dob_str and dob_str.lower() != 'none':
            profile_result = await db.execute(select(PatientProfile).where(PatientProfile.patient_id == patient.id))
            profile = profile_result.scalars().first()
            if not profile:
                profile = PatientProfile(org_id=org_id, patient_id=patient.id)
                db.add(profile)
                await db.flush()
            if not profile.dob:
                parsed_dob = None
                # Attempt to parse multiple date formats
                for fmt in ('%Y-%m-%d', '%d %B %Y', '%d %b %Y'): # Added common formats
                    try:
                        parsed_dob = datetime.strptime(dob_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if parsed_dob:
                    profile.dob = parsed_dob
                else:
                    logger.warning(f"Could not parse DOB string with any known format: {dob_str}")

        # --- 4. Create Intake Session ---
        intake_session = IntakeSession(
            org_id=org_id,
            patient_id=patient.id,
            conversation_id=new_conversation.id, # Link to the newly created conversation
            context=extracted_data, # Save all extracted data as context
            status='submitted'
        )
        db.add(intake_session)
        await db.flush()
        await db.refresh(intake_session)

        # --- 5. Create Clinical Records (More Robust Parsing) ---
        def process_clinical_data(raw_value, key_name):
            """
            Processes raw data which can be a JSON string of a list of objects,
            or a simple string.
            Returns a list of dictionaries.
            """
            if not raw_value or not isinstance(raw_value, str) or raw_value.lower().strip() == 'none':
                return []

            try:
                # If it's a JSON string of a list, parse it
                data = json.loads(raw_value)
                if isinstance(data, list):
                    return data
                # If it's some other JSON (e.g., a single object), wrap it in a list
                elif isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                # It's not a valid JSON string, treat it as a simple string.
                logger.warning(f'Could not decode JSON for key {key_name}. Treating as plain text: {raw_value}')
                # Return a list with a single object, assuming a default key like 'name' or 'notes'
                # This part is heuristic and depends on the target model.
                if key_name == "intake.symptoms":
                    return [{'notes': raw_value}]
                if key_name == "intake.condition_history":
                    return [{'condition': raw_value}]
                if key_name == "intake.allergies":
                    return [{'substance': raw_value}]
                if key_name == "intake.medications":
                    return [{'name': raw_value}]
                if key_name == "intake.family_history":
                    # This one is tricky as it has two fields. We can't reliably parse it.
                    return []
            return []

        cc_text = extracted_data.get("intake.chief_complaint.text")
        if cc_text and cc_text.lower() != 'none':
            db.add(IntakeChiefComplaint(org_id=org_id, session_id=intake_session.id, text=cc_text))

        symptoms = process_clinical_data(extracted_data.get("intake.symptoms"), "intake.symptoms")
        for item in symptoms:
            notes = item.get('notes')
            if notes and str(notes).lower() != 'none':
                db.add(IntakeSymptom(org_id=org_id, session_id=intake_session.id, notes=str(notes)))

        conditions = process_clinical_data(extracted_data.get("intake.condition_history"), "intake.condition_history")
        for item in conditions:
            condition = item.get('condition')
            if condition and str(condition).lower() != 'none':
                db.add(IntakeConditionHistory(org_id=org_id, session_id=intake_session.id, condition=str(condition)))

        allergies = process_clinical_data(extracted_data.get("intake.allergies"), "intake.allergies")
        for item in allergies:
            substance = item.get('substance')
            if substance and str(substance).lower() != 'none':
                db.add(IntakeAllergy(org_id=org_id, session_id=intake_session.id, substance=str(substance)))

        medications = process_clinical_data(extracted_data.get("intake.medications"), "intake.medications")
        for item in medications:
            name = item.get('name')
            if name and str(name).lower() != 'none':
                db.add(IntakeMedication(org_id=org_id, session_id=intake_session.id, name=str(name)))

        family_history = process_clinical_data(extracted_data.get("intake.family_history"), "intake.family_history")
        for item in family_history:
            relative = item.get('relative')
            condition = item.get('condition')
            if relative and str(relative).lower() != 'none' and condition and str(condition).lower() != 'none':
                db.add(IntakeFamilyHistory(org_id=org_id, session_id=intake_session.id, relative=str(relative), condition=str(condition)))

        await db.commit()
        logger.info(f"Successfully saved all data for conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error during final save for conversation {conversation_id}: {e}", exc_info=True)
        await db.rollback()
        raise
