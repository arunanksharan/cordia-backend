import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import ContactPointCreate, RelatedPersonCreate, DirectoryCreate

class IdentityService:
    def __init__(self, s: AsyncSession):
        self.s = s
        self.repo = IdentityRepository(s)

    async def add_contact(self, org: uuid.UUID, p: ContactPointCreate):
        obj = await self.repo.add_contact(org, **p.model_dump(exclude_unset=True)); await self.s.commit(); return obj
    async def list_contacts(self, org: uuid.UUID, owner_type: str, owner_id: uuid.UUID):
        return await self.repo.list_contacts(org, owner_type, owner_id)

    async def add_related(self, org: uuid.UUID, p: RelatedPersonCreate):
        obj = await self.repo.add_related(org, **p.model_dump(exclude_unset=True)); await self.s.commit(); return obj
    async def list_related(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self.repo.list_related(org, patient_id)

    async def add_practitioner(self, org: uuid.UUID, p: DirectoryCreate):
        obj = await self.repo.add_practitioner(org, **p.model_dump(exclude_unset=True)); await self.s.commit(); return obj
    async def list_practitioners(self, org: uuid.UUID):
        return await self.repo.list_practitioners(org)

    async def add_location(self, org: uuid.UUID, p: DirectoryCreate):
        obj = await self.repo.add_location(org, **p.model_dump(exclude_unset=True)); await self.s.commit(); return obj
    async def list_locations(self, org: uuid.UUID):
        return await self.repo.list_locations(org)