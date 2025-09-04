import uuid
from typing import Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.patients.models import Patient

class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Patient:
        obj = Patient(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        q = select(Patient).where(
            Patient.id == patient_id,
            Patient.org_id == org_id,
            Patient.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list(self, org_id: uuid.UUID, limit: int = 50, offset: int = 0) -> Sequence[Patient]:
        q = select(Patient).where(
            Patient.org_id == org_id,
            Patient.deleted_at.is_(None),
        ).order_by(Patient.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(q)
        return res.scalars().all()

    async def update(self, org_id: uuid.UUID, patient_id: uuid.UUID, **data) -> Patient | None:
        obj = await self.get(org_id, patient_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.flush()
        return obj

    async def soft_delete(self, org_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
        obj = await self.get(org_id, patient_id)
        if not obj:
            return False
        from datetime import datetime, timezone
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True