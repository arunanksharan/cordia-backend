import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
import httpx
import json
import logging
import re

logger = logging.getLogger(__name__)


from app.modules.appointments.repository import AppointmentRepository, WaitlistRepository, CheckinRepository
from app.modules.appointments.models import Appointment
from app.modules.appointments.schemas import (
    AppointmentRequest, AppointmentConfirm, AppointmentUpdate, AppointmentStatusChange,
    WaitlistCreate, WaitlistUpdate, CheckinCreate, N8nDepartmentTriagePayload
)
from app.modules.events.outbox import OutboxService
from app.modules.notifications.service import NotificationsService
from app.modules.conversations.state_service import ConversationStateService
from app.modules.directory.models import Practitioner, Location
from app.modules.availability.models import PractitionerSchedule
from app.core.config import settings
from app.core.twilio import twilio_client, TWILIO_PHONE_NUMBER
from app.modules.patients.models import Patient
from app.core.redis import redis_manager

VALID_NEXT = {
    "requested": {"pending_confirm", "confirmed", "canceled"},
    "pending_confirm": {"confirmed", "canceled"},
    "confirmed": {"rescheduled", "canceled", "no_show", "completed"},
    "rescheduled": {"confirmed", "canceled"},
    "no_show": {"confirmed", "canceled"},
    "completed": set(),
    "canceled": set(),
}

def _now() -> datetime:
    return datetime.now(timezone.utc)

def parse_slot_reply(user_text: str, total_slots: int):
    text = user_text.strip().lower()

    if any(word in text for word in ["none", "no", "nothing"]):
        return {"slot_choice": "none"}

    match = re.search(r"\b(\d+)\b", text)
    if match:
        slot_num = int(match.group(1))
        if 1 <= slot_num <= total_slots:
            return {"slot_choice": slot_num}

    words_to_num = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5
    }
    for word, num in words_to_num.items():
        if word in text and num <= total_slots:
            return {"slot_choice": num}
            
    time_match = re.search(r"(\d{1,2}:\d{2})\s*(am|pm)?", text)
    if time_match:
        return {"slot_choice": "time", "time_str": time_match.group(1)}

    return {"slot_choice": None}

class AppointmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.appts = AppointmentRepository(session)
        self.waitlist = WaitlistRepository(session)
        self.checkins = CheckinRepository(session)

    async def find_available_slots(self, conversation_id: str) -> list[dict]:
        state_service = ConversationStateService(conversation_id)
        extracted_data = await state_service.get_extracted_data()
        
        best_department = extracted_data.get("appointment_request.best_department")
        preferred_location = extracted_data.get("appointment_request.preferred_location")
        preferred_day_str = extracted_data.get("appointment_request.preferred_day")
        preferred_time_str = extracted_data.get("appointment_request.preferred_time")

        logger.info(f"Finding slots for convo {conversation_id} with prefs: day='{preferred_day_str}', time='{preferred_time_str}', loc='{preferred_location}'")

        if not best_department:
            logger.error(f"Best department not found in Redis for convo {conversation_id}")
            return []
        logger.info(f"DEBUG: best_department from Redis: '{best_department}'")
        logger.info(f"DEBUG: best_department from Redis: '{best_department}'")

        practitioner_query = select(Practitioner, Location).join(Location, Practitioner.location_id == Location.id).where(Practitioner.specialty == best_department)
        
        if preferred_location and preferred_location.lower() != 'none':
            practitioner_query = practitioner_query.where(
                Location.name.ilike(f"%{preferred_location}%")
            )

        practitioner_result = await self.session.execute(practitioner_query)
        practitioner_location_pairs = practitioner_result.all()

        if not practitioner_location_pairs and preferred_location and preferred_location.lower() != 'none':
            logger.warning(
                f"No practitioners found for department '{best_department}' "
                f"and location '{preferred_location}'. Falling back to department-only search."
            )

        # Fetch practitioners purely by department, ignoring location
        fallback_query = select(Practitioner).where(Practitioner.specialty == best_department)
        practitioner_result = await self.session.execute(fallback_query)
        practitioners = practitioner_result.scalars().all()

        practitioner_location_pairs = []
        for p in practitioners:
            logger.info(f"DEBUG: Found practitioner '{p.name}' with specialty '{p.specialty}' during fallback search.")
            location_result = await self.session.execute(select(Location).where(Location.id == p.location_id))
            location = location_result.scalars().first()
            practitioner_location_pairs.append((p, location))
        if not practitioner_location_pairs:
            logger.warning(f"No practitioners found for department '{best_department}' even after fallback.")
            return []

        all_available_slots = []
        for practitioner, location in practitioner_location_pairs:
            schedule_result = await self.session.execute(
                select(PractitionerSchedule).where(PractitionerSchedule.practitioner_id == practitioner.id)
            )
            schedules = schedule_result.scalars().all()

            appointments_result = await self.session.execute(
                select(Appointment).where(
                    Appointment.practitioner_name == practitioner.name,
                    Appointment.confirmed_start >= datetime.now(timezone.utc),
                    Appointment.status == "confirmed"
                )
            )
            booked_appointments = appointments_result.scalars().all()

            today = datetime.now(timezone.utc).date()
            for i in range(14):
                current_date = today + timedelta(days=i)
                day_of_week = current_date.weekday()

                for schedule in schedules:
                    if schedule.day_of_week == day_of_week:
                        start_time = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(minutes=schedule.start_minute)
                        end_time = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(minutes=schedule.end_minute)
                        slot_minutes = schedule.slot_minutes

                        current_slot = start_time
                        while current_slot < end_time:
                            is_booked = False
                            for app in booked_appointments:
                                if app.confirmed_start and app.confirmed_start.date() == current_date and app.confirmed_start.time() == current_slot.time():
                                    is_booked = True
                                    break
                            
                            if not is_booked:
                                all_available_slots.append({
                                    "slot": current_slot,
                                    "practitioner_name": practitioner.name,
                                    "location_name": location.name if location else "Unknown Location",
                                    "slot_minutes": slot_minutes
                                })
                            
                            current_slot += timedelta(minutes=slot_minutes)

        unique_slots = []
        seen_slots = set()
        for s in all_available_slots:
            slot_tuple = (s['slot'], s['practitioner_name'], s['location_name'])
            if slot_tuple not in seen_slots:
                unique_slots.append(s)
                seen_slots.add(slot_tuple)
        
        sorted_unique_slots = sorted(unique_slots, key=lambda x: x['slot'])

        preferred_day = None
        if preferred_day_str and preferred_day_str.lower() != 'none':
            try:
                preferred_day = int(preferred_day_str)
                logger.info(f"Parsed preferred_day: {preferred_day}")
            except (ValueError, TypeError):
                logger.warning(f"Could not parse preferred_day: {preferred_day_str}")

        preferred_time_obj = None

        # 1️⃣ Parse preferred_time_str as minutes from midnight
        if preferred_time_str and preferred_time_str.lower() != 'none':
            try:
                minutes_from_midnight = int(preferred_time_str)
                hours = minutes_from_midnight // 60
                minutes = minutes_from_midnight % 60
                preferred_time_obj = datetime.min.replace(hour=hours, minute=minutes).time()
                logger.info(f"Parsed preferred_time as minutes from midnight: {preferred_time_str} -> {preferred_time_obj}")
            except (ValueError, TypeError):
                logger.warning(f"Could not parse preferred_time: {preferred_time_str}. Expected minutes from midnight.")

        filtered_slots = sorted_unique_slots

        # 2️⃣ If user selected a specific day, filter slots for that day
        if preferred_day is not None:
            filtered_slots = [
                slot for slot in filtered_slots
                if slot['slot'].weekday() == preferred_day
            ]
        # 3️⃣ If a preferred time is given, find up to 3 slots around it
        if preferred_time_obj is not None:
            # Sort slots by how close they are to the preferred time
            sorted_by_closeness = sorted(
                filtered_slots,
                key=lambda x: abs(
                    (x['slot'].hour * 60 + x['slot'].minute) -
                    (preferred_time_obj.hour * 60 + preferred_time_obj.minute)
                )
            )
            
            # Get the top 3 closest slots
            top_slots = sorted_by_closeness[:3]

            # Sort them chronologically for presentation
            return sorted(top_slots, key=lambda x: x['slot'])

        # 4️⃣ If no preferred time is given, return the first 3 available slots
        return filtered_slots[:3]

    async def handle_slot_reply(self, conversation_id: str, user_text: str):
        state_service = ConversationStateService(conversation_id)
        extracted_data = await state_service.get_extracted_data()
        
        slots_json = extracted_data.get("appointment_request.available_slots")
        if not slots_json:
            return {"error": "No slots were offered."}
            
        available_slots = json.loads(slots_json)
        total_slots = len(available_slots)
        
        parsed_reply = parse_slot_reply(user_text, total_slots)
        slot_choice = parsed_reply.get("slot_choice")
        
        if slot_choice == "none":
            # Delete Redis data for the cancelled session
            user_phone = extracted_data.get("user_phone")
            if user_phone:
                await redis_manager.redis.delete(f"phone_to_convo:{user_phone}")
            await redis_manager.redis.delete(state_service.required_fields_key)
            await redis_manager.redis.delete(state_service.extracted_data_key)
            logger.info(f"Conversation {conversation_id} cancelled. Redis data deleted.")
            return {"action": "cancel", "message": "Okay, the appointment booking has been cancelled."}
            
        elif isinstance(slot_choice, int):
            chosen_slot_info = available_slots[slot_choice - 1]
            return await self.book_chosen_slot(conversation_id, chosen_slot_info, extracted_data)
            
        elif slot_choice == "time":
            time_str = parsed_reply.get("time_str")
            for slot_info in available_slots:
                slot_time = datetime.fromisoformat(slot_info["slot"])
                if slot_time.strftime("%I:%M").lstrip("0") == time_str or slot_time.strftime("%H:%M") == time_str:
                    return await self.book_chosen_slot(conversation_id, slot_info, extracted_data)
            return {"action": "re-ask", "message": f"I'm sorry, I don't see that time in the list. Please choose a number from 1 to {total_slots}."}

        else: # slot_choice is None
            return {"action": "re-ask", "message": f"I'm sorry, I didn't understand your choice. Please reply with a slot number (1–{total_slots}) or type \"none\"."}

    async def book_chosen_slot(self, conversation_id: str, slot_info: dict, extracted_data: dict):
        """
        Helper function to create the appointment in the database.
        """
        try:
            slot_time = datetime.fromisoformat(slot_info["slot"])
            practitioner_name = slot_info["practitioner_name"]
            
            practitioner_result = await self.session.execute(
                select(Practitioner).where(Practitioner.name == practitioner_name)
            )
            practitioner = practitioner_result.scalars().first()
            if not practitioner:
                return {"action": "error", "message": "Could not find practitioner to book appointment."}

            patient_id = extracted_data.get("patient_id")
            if not patient_id:
                return {"action": "error", "message": "Could not find patient to book appointment."}

            appointment = Appointment(
                org_id=practitioner.org_id,
                patient_id=uuid.UUID(patient_id),
                practitioner_name=practitioner_name,
                confirmed_start=slot_time,
                confirmed_end=slot_time + timedelta(minutes=slot_info["slot_minutes"]),
                status="confirmed",
                channel_origin="whatsapp"
            )
            self.session.add(appointment)
            await self.session.commit()
            
            state_service = ConversationStateService(conversation_id)
            user_phone = extracted_data.get("user_phone")
            await redis_manager.redis.delete(f"phone_to_convo:{user_phone}")
            await redis_manager.redis.delete(state_service.required_fields_key)
            await redis_manager.redis.delete(state_service.extracted_data_key)

            return {"action": "booked", "message": f"Your appointment at {slot_time.strftime('%I:%M %p')} is confirmed. Thank you!"}

        except Exception as e:
            logger.error(f"Error booking appointment for convo {conversation_id}: {e}", exc_info=True)
            return {"action": "error", "message": "I'm sorry, there was an error booking your appointment. Please try again later."}

    # ---- Appointments ----
    async def request(self, org_id: uuid.UUID, payload: AppointmentRequest) -> Appointment:
        obj = await self.appts.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def confirm(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: AppointmentConfirm) -> Appointment | None:
        obj = await self.appts.get(org_id, appt_id)
        if not obj:
            return None
        if obj.status not in {"requested", "pending_confirm", "rescheduled", "no_show"}:
            return None
        obj.status = "confirmed"
        obj.confirmed_start = payload.confirmed_start
        obj.confirmed_end = payload.confirmed_end
        if payload.location_name: obj.location_name = payload.location_name
        if payload.practitioner_name: obj.practitioner_name = payload.practitioner_name
        await OutboxService(self.session).enqueue(
            org_id, "APPT_CONFIRMED", "appointment", obj.id,
            {"start": obj.confirmed_start.isoformat(), "end": obj.confirmed_end.isoformat() if obj.confirmed_end else None}
        )
        if obj.patient_id:
            await NotificationsService(self.session).send(
                org_id, channel="sms", to="+10000000000",
                subject=None, body="Your appointment is confirmed for ${start}",
                variables={"start": obj.confirmed_start.isoformat()}
            )
        await self.session.commit()
        return obj

    async def update_fields(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: AppointmentUpdate) -> Appointment | None:
        obj = await self.appts.get(org_id, appt_id)
        if not obj:
            return None
        if obj.status in {"completed", "canceled"}:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        await self.session.commit()
        return obj

    async def change_status(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: AppointmentStatusChange) -> Appointment | None:
        obj = await self.appts.get(org_id, appt_id)
        if not obj:
            return None
        nxt = payload.status
        if nxt not in VALID_NEXT.get(obj.status, set()):
            return None
        if nxt == "rescheduled":
            obj.reschedule_.reschedule_count += 1
            obj.confirmed_start = None
            obj.confirmed_end = None
        if nxt == "no_show":
            obj.no_show_flag = True
        prev = obj.status
        obj.status = nxt
        await OutboxService(self.session).enqueue(
            org_id, "APPT_STATUS_CHANGED", "appointment", obj.id,
            {"from": prev, "to": nxt}
        )
        await self.session.commit()
        return obj

    async def get(self, org_id: uuid.UUID, appt_id: uuid.UUID) -> Appointment | None:
        return await self.appts.get(org_id, appt_id)

    async def list(self, org_id: uuid.UUID, status: str | None, patient_id: uuid.UUID | None, limit: int, offset: int):
        return await self.appts.list(org_id, status=status, patient_id=patient_id, limit=limit, offset=offset)

    # ---- Waitlist ----
    async def waitlist_add(self, org_id: uuid.UUID, payload: WaitlistCreate):
        obj = await self.waitlist.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def waitlist_update(self, org_id: uuid.UUID, waitlist_id: uuid.UUID, payload: WaitlistUpdate):
        wl = await self.waitlist.get(org_id, waitlist_id)
        if not wl:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(wl, k, v)
        await self.session.commit()
        return wl

    async def waitlist_suggest(self, org_id: uuid.UUID, *, location_name: str | None, reason_code: str | None, limit: int = 10):
        return await self.waitlist.list_active(org_id, location_name=location_name, reason_code=reason_code, limit=limit)

    # ---- Check-in ----
    async def checkin(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: CheckinCreate):
        appt = await self.appts.get(org_id, appt_id)
        if not appt:
            return None
        obj = await self.checkins.create( org_id, appt_id, payload.forms_completed, payload.payment_collected)
        meta = dict(appt.meta or {})
        meta["checked_in"] = True
        appt.meta = meta
        await self.session.commit()
        return obj
