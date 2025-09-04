import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.availability.repository import AvailabilityRepository
from app.modules.availability.schemas import SlotsQuery
from app.modules.availability.models import PractitionerSchedule
from app.modules.events.outbox import OutboxService
from app.modules.appointments.service import AppointmentService

def _dt_floor(dt: datetime) -> datetime:
    if dt.tzinfo is None: return dt.replace(tzinfo=timezone.utc)
    return dt

class AvailabilityService:
    def __init__(self, s: AsyncSession):
        self.s = s
        self.repo = AvailabilityRepository(s)

    async def create_schedule(self, org: uuid.UUID, **data):
        obj = await self.repo.create_schedule(org, **data)
        await OutboxService(self.s).enqueue(org, "SCHEDULE_CREATED", "schedule", obj.id, {})
        await self.s.commit()
        return obj

    async def list_schedules(self, org: uuid.UUID, practitioner_id: uuid.UUID, location_id: uuid.UUID):
        return await self.repo.list_schedules(org, practitioner_id, location_id)

    async def search_slots(self, org: uuid.UUID, q: SlotsQuery) -> list[dict]:
        start = _dt_floor(q.start); end = _dt_floor(q.end)
        if end <= start: return []
        schedules = await self.repo.list_schedules(org, q.practitioner_id, q.location_id)
        # gather conflicts (appointments + holds)
        appts = await self.repo.list_appointments_in_range(org, q.practitioner_id, q.location_id, start, end)
        holds = await self.repo.list_holds_in_range(org, q.practitioner_id, q.location_id, start, end, now=datetime.now(timezone.utc))

        busy: list[tuple[datetime, datetime]] = []
        for a in appts:
            s = a.confirmed_start or a.requested_start
            e = a.confirmed_end or a.requested_end
            if s and e: busy.append((s, e))
        for h in holds:
            busy.append((h.start, h.end))

        def free_for(window_start: datetime, window_end: datetime, dur_min: int) -> List[tuple[datetime, datetime]]:
            cur = window_start
            out = []
            delta = timedelta(minutes=dur_min)
            while cur + delta <= window_end:
                slot_ok = True
                ce = cur + delta
                for bs, be in busy:
                    if cur < be and ce > bs:  # overlap
                        slot_ok = False; break
                if slot_ok:
                    out.append((cur, ce))
                cur = cur + delta
            return out

        # compute per-day windows from schedules
        result: list[dict] = []
        day = datetime(start.year, start.month, start.day, tzinfo=start.tzinfo)
        while day < end:
            dow = day.weekday()  # 0-6
            todays = [s for s in schedules if s.day_of_week == dow and s.active]
            for sc in todays:
                w_start = day + timedelta(minutes=sc.start_minute)
                w_end = day + timedelta(minutes=sc.end_minute)
                if w_end <= start or w_start >= end: continue
                ws = max(w_start, start); we = min(w_end, end)
                for sst, sse in free_for(ws, we, q.duration):
                    result.append({
                        "id": f"{q.practitioner_id}:{q.location_id}:{int(sst.timestamp())}",
                        "start": sst, "end": sse,
                        "practitioner_id": q.practitioner_id,
                        "location_id": q.location_id,
                        "state": "open"
                    })
            day = day + timedelta(days=1)
        return result

    async def create_hold(self, org: uuid.UUID, *, practitioner_id: uuid.UUID, location_id: uuid.UUID, start: datetime, end: datetime, patient_id: uuid.UUID | None, intake_session_id: uuid.UUID | None, ttl_seconds: int = 180):
        # verify slot still free (no overlap with appts/valid holds)
        conflicts_appt = await self.repo.list_appointments_in_range(org, practitioner_id, location_id, start, end)
        if any(True for a in conflicts_appt if (a.confirmed_start or a.requested_start) < end and (a.confirmed_end or a.requested_end) > start):
            return None, "conflict_appointment"
        conflicts_hold = await self.repo.list_holds_in_range(org, practitioner_id, location_id, start, end, now=datetime.now(timezone.utc))
        if conflicts_hold:
            return None, "conflict_hold"
        hold = await self.repo.create_hold(org, practitioner_id=practitioner_id, location_id=location_id, start=start, end=end, patient_id=patient_id, intake_session_id=intake_session_id, ttl_seconds=ttl_seconds)
        await OutboxService(self.s).enqueue(org, "AVAILABILITY_HOLD_CREATED", "hold", hold.id, {"token": hold.token, "start": start.isoformat(), "end": end.isoformat()})
        await self.s.commit()
        return hold, None

    async def book_with_hold(self, org: uuid.UUID, *, token: str, patient_id: uuid.UUID, intake_session_id: uuid.UUID | None, reason_code: str | None, notify_contact: dict | None):
        hold = await self.repo.get_hold(org, token)
        if not hold: return None, "invalid_hold"
        now = datetime.now(timezone.utc)
        if hold.used_at is not None or hold.expires_at <= now:
            return None, "expired_hold"
        # Create then confirm appointment using existing service
        appt_svc = AppointmentService(self.s)
        # request
        req_payload = type("X",(object,),{"model_dump":lambda s,exclude_unset=True: {
            "patient_id": patient_id,
            "reason_code": reason_code,
            "channel_origin": "agent",
            "requested_start": hold.start,
            "requested_end": hold.end,
            "location_name": "",  # we keep by name; directory IDs exist separately
            "practitioner_name": ""
        }})()
        appt = await appt_svc.request(org, req_payload)
        # confirm
        conf_payload = type("Y",(object,),{"confirmed_start": hold.start, "confirmed_end": hold.end, "location_name": None, "practitioner_name": None, "model_dump":lambda s,exclude_unset=True: {"confirmed_start": hold.start, "confirmed_end": hold.end}})()
        appt = await appt_svc.confirm(org, appt.id, conf_payload)
        await self.repo.mark_hold_used(hold, now)
        await OutboxService(self.s).enqueue(org, "AVAILABILITY_BOOKED", "appointment", appt.id, {"hold_token": token})

        # optional immediate notify using notifications module (if contact provided)
        if notify_contact and notify_contact.get("to"):
            try:
                from app.modules.notifications.service import NotificationsService
                vars = {"start": hold.start.isoformat()}
                await NotificationsService(self.s).send(org, channel=notify_contact.get("channel","sms"), to=notify_contact["to"], subject=None, body="Your appointment is confirmed for ${start}", variables=vars)
            except Exception:
                # do not break booking if notifications fail
                pass

        await self.s.commit()
        return appt, None