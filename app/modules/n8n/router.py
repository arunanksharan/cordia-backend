from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json
import httpx
from datetime import timedelta, datetime

from app.core.db import get_session
from app.core.redis import redis_manager
from app.modules.conversations.state_service import ConversationStateService
from app.modules.intake.orchestration import save_intake_from_redis
from .schemas import GptResponsePayload
from app.modules.appointments.schemas import N8nDepartmentTriagePayload
from app.modules.appointments.service import AppointmentService
from app.core.twilio import twilio_client, TWILIO_PHONE_NUMBER
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def parse_extracted_fields(fields: dict) -> dict:
    parsed_fields = {}
    for key, value in fields.items():
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                parsed_fields[key] = parsed_value
            except json.JSONDecodeError:
                parsed_fields[key] = value
        else:
            parsed_fields[key] = value
    return parsed_fields

@router.post("/intake-response", status_code=status.HTTP_200_OK)
async def handle_gpt_response(payload: GptResponsePayload, db: AsyncSession = Depends(get_session)):
    """
    Receives the processed data from the n8n GPT node, updates the conversation state,
    and sends the next question to the user.
    """
    conversation_id = payload.conversation_id
    state_service = ConversationStateService(conversation_id)

    try:
        if payload.extracted_fields:
            parsed_fields = parse_extracted_fields(payload.extracted_fields)
            required_fields_before = await state_service.get_required_fields()
            await state_service.update_state(
                new_data=parsed_fields, 
                required_fields_before_update=required_fields_before,
                next_field_from_gpt=payload.next_field
            )

        extracted_data = await state_service.get_extracted_data()
        user_phone = extracted_data.get("user_phone")

        if not user_phone:
            raise HTTPException(status_code=404, detail="User phone not found in session state.")

        if not payload.next_question or not payload.next_question.strip():
            # CONVERSATION IS COMPLETE - Trigger booking logic (already done by n8n triage workflow)
            logger.info(f"Conversation {conversation_id} is complete. Triggering final data save and department triage.")
            await save_intake_from_redis(conversation_id, db)

            # --- Trigger n8n Department Triage Workflow ---
            chief_complaint = extracted_data.get("intake.chief_complaint.text", "")
            symptoms_json = extracted_data.get("intake.symptoms", "[]")
            symptoms = []
            try:
                symptoms = json.loads(symptoms_json)
            except json.JSONDecodeError:
                if isinstance(symptoms_json, str):
                    symptoms = [symptoms_json]

            n8n_triage_payload = {
                "conversation_id": conversation_id,
                "chief_complaint": chief_complaint,
                "symptoms": symptoms,
                "booking_intent": 1
            }

            try:
                async with httpx.AsyncClient() as client:
                    await client.post(settings.N8N_WEBHOOK_URL, json=n8n_triage_payload, timeout=30.0)
                logger.info(f"Successfully triggered n8n department triage workflow for {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to trigger n8n department triage workflow for {conversation_id}: {e}", exc_info=True)

            # Do NOT send a message from here if conversation is complete,
            # the slots message will be sent by handle_triage_response
            pass
        else:
            # CONVERSATION IS ONGOING - Send the next question
            if twilio_client:
                twilio_client.messages.create(
                    body=payload.next_question,
                    from_=TWILIO_PHONE_NUMBER,
                    to=user_phone
                )
            else:
                logger.error("Twilio client not configured, cannot send reply.")

        return {"status": "success", "message": "Reply sent to user."}

    except Exception as e:
        logger.error(f"Error processing GPT response for convo {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing GPT response.")

@router.post("/triage-response", status_code=status.HTTP_200_OK)
async def handle_triage_response(payload: N8nDepartmentTriagePayload, db: AsyncSession = Depends(get_session)):
    """
    Receives the department triage result from n8n, saves it to Redis,
    and triggers the slot finding logic.
    """
    conversation_id = str(payload.conversation_id)
    logger.info(f"Triage response received for conversation: {conversation_id}")
    state_service = ConversationStateService(conversation_id)
    
    if not payload.best_department:
        raise HTTPException(status_code=400, detail="best_department not found in payload.")

    department_name = payload.best_department.name
    
    try:
        # Save the best department to Redis
        redis_key = state_service.extracted_data_key
        await redis_manager.redis.hset(redis_key, "appointment_request.best_department", department_name)
        logger.info(f"Successfully saved best_department '{department_name}' for conversation {conversation_id}")
        
        # Find available slots
        appointment_service = AppointmentService(db)
        available_slots = await appointment_service.find_available_slots(conversation_id)
        
        # Retrieve user_phone before potentially deleting extracted_data
        extracted_data = await state_service.get_extracted_data()
        user_phone = extracted_data.get("user_phone")

        if not available_slots:
            reply_text = "I'm sorry, but I couldn't find any available appointment slots that match your preferences. Our team will review your request and get back to you shortly."
            if user_phone and twilio_client:
                twilio_client.messages.create(
                    body=reply_text,
                    from_=TWILIO_PHONE_NUMBER,
                    to=user_phone
                )
                logger.info(f"Sent 'no slots found' message to user for convo {conversation_id}.")
            else:
                logger.error(f"Could not send 'no slots found' message for convo {conversation_id}: missing phone or twilio client.")

            # Delete Redis data and end session
            await redis_manager.redis.delete(redis_key)
            # Also delete the phone_to_convo mapping to ensure a new conversation starts next time
            convo_id_key = f"phone_to_convo:{user_phone}"
            await redis_manager.redis.delete(convo_id_key)
            logger.info(f"Conversation {conversation_id} session ended and Redis data deleted due to no available slots.")
            return {"status": "success", "message": "No slots found message sent and session ended."}
        else:
            # Save the found slots to Redis for the next step
            serializable_slots = [
                {
                    "slot": s["slot"].isoformat(),
                    "practitioner_name": s["practitioner_name"],
                    "location_name": s["location_name"],
                    "slot_minutes": s["slot_minutes"]
                }
                for s in available_slots
            ]
            slots_json = json.dumps(serializable_slots)
            await redis_manager.redis.hset(redis_key, "appointment_request.available_slots", slots_json)
            logger.info(f"Saving slots to Redis for convo {conversation_id}. Key: {redis_key}")
            logger.info(f"Slots JSON: {slots_json}")

            # Format the message for the user
            reply_text = "Here are some available appointment slots:\n\n"
            
            for i, slot_info in enumerate(available_slots):
                slot_time = slot_info["slot"]
                slot_minutes = slot_info["slot_minutes"]
                end_time = slot_time + timedelta(minutes=slot_minutes)
                
                start_time_str = slot_time.strftime("%I:%M %p")
                end_time_str = end_time.strftime("%I:%M %p")
                
                practitioner_name = slot_info["practitioner_name"]
                location_name = slot_info["location_name"]

                reply_text += f"{i+1}️⃣  {start_time_str} – {end_time_str} with {practitioner_name} at {location_name}\n"
                
            total_slots = len(available_slots)
            reply_text += f"\nPlease reply with the slot number (1–{total_slots}) or type \"none\" if none of these work for you."

            if user_phone and twilio_client:
                twilio_client.messages.create(
                    body=reply_text,
                    from_=TWILIO_PHONE_NUMBER,
                    to=user_phone
                )
                # Set flag to indicate we are awaiting a slot reply
                await redis_manager.redis.hset(redis_key, "awaiting_slot_reply", "True")
                await redis_manager.redis.expire(redis_key, 900) # Expire the hash in 15 minutes
                logger.info(f"Set 'awaiting_slot_reply' flag for convo {conversation_id}")
            else:
                logger.error(f"Could not send slots to user for convo {conversation_id}: missing phone or twilio client.")

            return {"status": "success", "message": "Slots sent to user."}

    except Exception as e:
        logger.error(f"Error processing triage response for convo {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing triage response.")