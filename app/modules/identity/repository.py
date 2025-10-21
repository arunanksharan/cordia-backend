import uuid
from typing import Sequence
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import ContactPoint, RelatedPerson, IdentityProvider, IdentityLocation

class IdentityRepository:
    def __init__(self, session: AsyncSession):
        self.s = session

    async def add_contact_point(self, org: uuid.UUID, **data):
        obj = ContactPoint(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj

    async def add_related_person(self, org: uuid.UUID, **data):
        obj = RelatedPerson(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj

    async def add_practitioner(self, org: uuid.UUID, **data) -> IdentityProvider:
        obj = IdentityProvider(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_practitioners(self, org: uuid.UUID) -> Sequence[IdentityProvider]:
        r = await self.s.execute(select(IdentityProvider).where(IdentityProvider.org_id==org, IdentityProvider.deleted_at.is_(None))); return r.scalars().all()

    async def add_location(self, org: uuid.UUID, **data) -> IdentityLocation:
        obj = IdentityLocation(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_locations(self, org: uuid.UUID) -> Sequence[IdentityLocation]:
        r = await self.s.execute(select(IdentityLocation).where(IdentityLocation.org_id==org, IdentityLocation.deleted_at.is_(None))); return r.scalars().all()