import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.patients.repository import PatientRepository
from app.modules.patients.schemas import PatientCreate, PatientUpdate
from app.modules.patients.models import Patient

class PatientService:
    def __init__(self, session: AsyncSession):
        self.repo = PatientRepository(session)
        self.session = session

    async def create(self, org_id: uuid.UUID, payload: PatientCreate) -> Patient:
        obj = await self.repo.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def get(self, org_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        return await self.repo.get(org_id, patient_id)

    async def list(self, org_id: uuid.UUID, limit: int = 50, offset: int = 0):
        return await self.repo.list(org_id, limit, offset)

    async def update(self, org_id: uuid.UUID, patient_id: uuid.UUID, payload: PatientUpdate) -> Patient | None:
        obj = await self.repo.update(org_id, patient_id, **payload.model_dump(exclude_unset=True))
        if obj:
            await self.session.commit()
        return obj

    async def delete(self, org_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
        ok = await self.repo.soft_delete(org_id, patient_id)
        if ok:
            await self.session.commit()
        return ok