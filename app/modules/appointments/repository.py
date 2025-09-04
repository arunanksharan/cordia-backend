import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.modules.appointments.models import Appointment, WaitlistEntry, CheckinMeta

class AppointmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Appointment:
        obj = Appointment(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, appt_id: uuid.UUID) -> Appointment | None:
        q = select(Appointment).where(
            and_(Appointment.id == appt_id,
                 Appointment.org_id == org_id,
                 Appointment.deleted_at.is_(None))
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list(self, org_id: uuid.UUID, *, status: str | None = None, patient_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0) -> Sequence[Appointment]:
        cond = [Appointment.org_id == org_id, Appointment.deleted_at.is_(None)]
        if status:
            cond.append(Appointment.status == status)
        if patient_id:
            cond.append(Appointment.patient_id == patient_id)
        q = select(Appointment).where(and_(*cond)).order_by(Appointment.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(q)
        return res.scalars().all()


class WaitlistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> WaitlistEntry:
        obj = WaitlistEntry(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, wid: uuid.UUID) -> WaitlistEntry | None:
        q = select(WaitlistEntry).where(
            and_(WaitlistEntry.id == wid,
                 WaitlistEntry.org_id == org_id,
                 WaitlistEntry.deleted_at.is_(None))
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list_active(self, org_id: uuid.UUID, *, location_name: str | None = None, reason_code: str | None = None, limit: int = 100) -> Sequence[WaitlistEntry]:
        cond = [WaitlistEntry.org_id == org_id, WaitlistEntry.deleted_at.is_(None), WaitlistEntry.active.is_(True)]
        if location_name:
            cond.append(WaitlistEntry.location_name == location_name)
        if reason_code:
            cond.append(WaitlistEntry.reason_code == reason_code)
        q = select(WaitlistEntry).where(and_(*cond)).order_by(WaitlistEntry.rank.asc())
        if limit:
            q = q.limit(limit)
        res = await self.session.execute(q)
        return res.scalars().all()


class CheckinRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, appointment_id: uuid.UUID, forms_completed: dict | None, payment_collected: bool) -> CheckinMeta:
        obj = CheckinMeta(org_id=org_id, appointment_id=appointment_id, forms_completed=forms_completed, payment_collected=payment_collected)
        self.session.add(obj)
        await self.session.flush()
        return obj