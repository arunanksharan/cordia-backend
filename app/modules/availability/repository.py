import uuid
from datetime import datetime, timezone, timedelta
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.modules.availability.models import PractitionerSchedule, AvailabilityHold
from app.modules.appointments.models import Appointment

class AvailabilityRepository:
    def __init__(self, s: AsyncSession): self.s = s

    # schedules
    async def create_schedule(self, org: uuid.UUID, **data) -> PractitionerSchedule:
        obj = PractitionerSchedule(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_schedules(self, org: uuid.UUID, practitioner_id: uuid.UUID, location_id: uuid.UUID) -> Sequence[PractitionerSchedule]:
        res = await self.s.execute(select(PractitionerSchedule).where(
            PractitionerSchedule.org_id==org,
            PractitionerSchedule.practitioner_id==practitioner_id,
            PractitionerSchedule.location_id==location_id,
            PractitionerSchedule.active.is_(True),
            PractitionerSchedule.deleted_at.is_(None)
        ))
        return res.scalars().all()

    # conflicts
    async def list_appointments_in_range(self, org: uuid.UUID, practitioner_id: uuid.UUID, location_id: uuid.UUID, start: datetime, end: datetime) -> Sequence[Appointment]:
        res = await self.s.execute(select(Appointment).where(
            Appointment.org_id==org,
            Appointment.deleted_at.is_(None),
            Appointment.practitioner_name.isnot(None),  # we store by name today; filter by time only
            or_(
                and_(Appointment.confirmed_start.isnot(None), Appointment.confirmed_end.isnot(None), Appointment.confirmed_start < end, Appointment.confirmed_end > start),
                and_(Appointment.requested_start.isnot(None), Appointment.requested_end.isnot(None), Appointment.requested_start < end, Appointment.requested_end > start),
            )
        ))
        return res.scalars().all()

    async def list_holds_in_range(self, org: uuid.UUID, practitioner_id: uuid.UUID, location_id: uuid.UUID, start: datetime, end: datetime, now: datetime) -> Sequence[AvailabilityHold]:
        res = await self.s.execute(select(AvailabilityHold).where(
            AvailabilityHold.org_id==org,
            AvailabilityHold.practitioner_id==practitioner_id,
            AvailabilityHold.location_id==location_id,
            AvailabilityHold.deleted_at.is_(None),
            AvailabilityHold.used_at.is_(None),
            AvailabilityHold.expires_at > now,
            AvailabilityHold.start < end,
            AvailabilityHold.end > start
        ))
        return res.scalars().all()

    # holds
    async def create_hold(self, org: uuid.UUID, *, practitioner_id: uuid.UUID, location_id: uuid.UUID, start: datetime, end: datetime, patient_id: uuid.UUID | None, intake_session_id: uuid.UUID | None, ttl_seconds: int = 180) -> AvailabilityHold:
        token = uuid.uuid4().hex[:16]
        obj = AvailabilityHold(org_id=org, practitioner_id=practitioner_id, location_id=location_id, start=start, end=end, patient_id=patient_id, intake_session_id=intake_session_id, token=token, expires_at=datetime.now(timezone.utc)+timedelta(seconds=ttl_seconds))
        self.s.add(obj); await self.s.flush(); return obj

    async def get_hold(self, org: uuid.UUID, token: str) -> AvailabilityHold | None:
        res = await self.s.execute(select(AvailabilityHold).where(
            AvailabilityHold.org_id==org, AvailabilityHold.token==token, AvailabilityHold.deleted_at.is_(None)
        ))
        return res.scalar_one_or_none()

    async def mark_hold_used(self, hold: AvailabilityHold, at: datetime):
        hold.used_at = at; await self.s.flush()