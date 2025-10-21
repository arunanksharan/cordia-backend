from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import logging
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.db import get_session
from app.core.redis import redis_manager
from app.modules.conversations.state_service import ConversationStateService
from app.modules.webhooks.twilio_schema import TwilioTextMessage, TwilioMediaMessage
from app.modules.appointments.service import AppointmentService
from app.core.twilio import twilio_client, TWILIO_PHONE_NUMBER
from app.core.speech_to_text import speech_to_text_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/twilio/webhook", status_code=204)
async def handle_twilio_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    """
    This endpoint receives a message from Twilio. It routes the message to either the
    slot selection logic or the main intake conversation flow.
    """
    form_data = await request.form()
    user_phone = form_data.get('From')
    user_text = None

    if not user_phone:
        return Response(status_code=204)

    try:
        if form_data.get('NumMedia') and int(form_data.get('NumMedia')) > 0:
            # It's a media message
            twilio_data = TwilioMediaMessage.model_validate(form_data)
            # Manually construct media_urls from form_data
            media_urls = []
            i = 0
            while f'MediaUrl{i}' in form_data:
                media_urls.append(form_data[f'MediaUrl{i}'])
                i += 1
            twilio_data.media_urls = media_urls

            if twilio_data.media_urls:
                media_url = twilio_data.media_urls[0]
                # Assuming the first media is the voice message
                user_text = await speech_to_text_service.transcribe_audio_url(media_url)
            else:
                user_text = twilio_data.body.strip() if twilio_data.body else ""
        else:
            # It's a text message
            twilio_data = TwilioTextMessage.model_validate(form_data)
            user_text = twilio_data.body.strip()

    except Exception as e:
        logger.error(f"Twilio data validation or transcription failed: {e}")
        return Response(status_code=400)

    if not user_text:
        return Response(status_code=204)

    try:
        # 1. Get or Create Conversation ID
        convo_id_key = f"phone_to_convo:{user_phone}"
        stored_conversation_id = await redis_manager.redis.get(convo_id_key)

        if stored_conversation_id:
            # Check if the actual conversation data exists for this ID
            state_service_check = ConversationStateService(stored_conversation_id)
            extracted_data_exists = await redis_manager.redis.exists(state_service_check.extracted_data_key)
            
            if extracted_data_exists:
                conversation_id = stored_conversation_id
                is_new_conversation = False
                await redis_manager.redis.expire(convo_id_key, 900) # Extend expiry for continuing conversation
                logger.info(f"Continuing conversation: {conversation_id}")
            else:
                # convo_id_key exists, but conversation data is gone. Treat as new conversation.
                await redis_manager.redis.delete(convo_id_key)
                conversation_id = str(uuid.uuid4())
                is_new_conversation = True
                await redis_manager.redis.set(convo_id_key, conversation_id, ex=900)
                logger.info(f"New conversation started (stale convo_id_key cleaned up): {conversation_id}")
        else:
            # No convo_id_key found, definitely a new conversation.
            conversation_id = str(uuid.uuid4())
            is_new_conversation = True
            await redis_manager.redis.set(convo_id_key, conversation_id, ex=900)
            logger.info(f"New conversation started: {conversation_id}")

        state_service = ConversationStateService(conversation_id)
        await state_service.set_user_phone(user_phone)

        # 2. Check if we are in the slot selection phase
        logger.info(f"Checking for available slots for convo: {conversation_id}")
        available_slots_json = await redis_manager.redis.hget(state_service.extracted_data_key, "appointment_request.available_slots")
        logger.info(f"Found available_slots_json: {available_slots_json is not None}")
        
        if available_slots_json:
            # This is a reply to the slots message
            logger.info("Routing to handle_slot_reply")
            appointment_service = AppointmentService(db)
            result = await appointment_service.handle_slot_reply(conversation_id, user_text)
            reply_text = result.get("message")
            if reply_text and twilio_client:
                twilio_client.messages.create(body=reply_text, from_=TWILIO_PHONE_NUMBER, to=user_phone)
            return Response(status_code=204)

        awaiting_slot_reply = await redis_manager.redis.hget(state_service.extracted_data_key, "awaiting_slot_reply")
        if awaiting_slot_reply == "True":
            logger.info("Awaiting slot reply, re-routing to handle_slot_reply")
            appointment_service = AppointmentService(db)
            result = await appointment_service.handle_slot_reply(conversation_id, user_text)
            reply_text = result.get("message")
            if reply_text and twilio_client:
                twilio_client.messages.create(body=reply_text, from_=TWILIO_PHONE_NUMBER, to=user_phone)
            return Response(status_code=204)

        # 3. If not slot selection, proceed with intake flow
        logger.info("Routing to intake flow")
        if is_new_conversation:
            await state_service.initialize_session(user_phone)

        required_fields = await state_service.get_required_fields()
        n8n_payload = {
            "conversation_id": conversation_id,
            "user_text": user_text,
            "required_fields": required_fields,
            "booking_intent": 0
        }
        
        if settings.N8N_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(settings.N8N_WEBHOOK_URL, json=n8n_payload, timeout=5.0)
                logger.info(f"Triggered n8n workflow for conversation {conversation_id}")
            except httpx.RequestError as e:
                logger.error(f"HTTP error triggering n8n: {e}")
        else:
            logger.warning("N8N_WEBHOOK_URL is not set. Cannot trigger workflow.")

    except Exception as e:
        logger.error(f"Critical error in Twilio webhook: {e}", exc_info=True)
    
    return Response(status_code=204)