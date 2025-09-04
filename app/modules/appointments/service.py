import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.appointments.repository import AppointmentRepository, WaitlistRepository, CheckinRepository
from app.modules.appointments.models import Appointment
from app.modules.appointments.schemas import (
    AppointmentRequest, AppointmentConfirm, AppointmentUpdate, AppointmentStatusChange,
    WaitlistCreate, WaitlistUpdate, CheckinCreate
)
from app.modules.events.outbox import OutboxService

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

class AppointmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.appts = AppointmentRepository(session)
        self.waitlist = WaitlistRepository(session)
        self.checkins = CheckinRepository(session)

    # ---- Appointments ----
    async def request(self, org_id: uuid.UUID, payload: AppointmentRequest) -> Appointment:
        obj = await self.appts.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def confirm(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: AppointmentConfirm) -> Appointment | None:
        obj = await self.appts.get(org_id, appt_id)
        if not obj:
            return None
        # allow confirm from requested/pending_confirm/rescheduled/no_show (reconfirm) states
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
        await self.session.commit()
        return obj

    async def update_fields(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: AppointmentUpdate) -> Appointment | None:
        obj = await self.appts.get(org_id, appt_id)
        if not obj:
            return None
        # only allow updates on non-terminal states
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
        # effects
        if nxt == "rescheduled":
            obj.reschedule_count += 1
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
        # naive suggestion: top-ranked active entries filtered by location/reason
        return await self.waitlist.list_active(org_id, location_name=location_name, reason_code=reason_code, limit=limit)

    # ---- Check-in ----
    async def checkin(self, org_id: uuid.UUID, appt_id: uuid.UUID, payload: CheckinCreate):
        appt = await self.appts.get(org_id, appt_id)
        if not appt:
            return None
        obj = await self.checkins.create(org_id, appt_id, payload.forms_completed, payload.payment_collected)
        # store a flag in appointment meta
        meta = dict(appt.meta or {})
        meta["checked_in"] = True
        appt.meta = meta
        await self.session.commit()
        return obj