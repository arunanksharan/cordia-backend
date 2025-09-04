import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.modules.identity.models import ContactPoint, RelatedPerson, Practitioner, Location

class IdentityRepository:
    def __init__(self, s: AsyncSession): self.s = s

    async def add_contact(self, org: uuid.UUID, **data) -> ContactPoint:
        obj = ContactPoint(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_contacts(self, org: uuid.UUID, owner_type: str, owner_id: uuid.UUID) -> Sequence[ContactPoint]:
        r = await self.s.execute(select(ContactPoint).where(ContactPoint.org_id==org, ContactPoint.owner_type==owner_type, ContactPoint.owner_id==owner_id, ContactPoint.deleted_at.is_(None))); return r.scalars().all()

    async def add_related(self, org: uuid.UUID, **data) -> RelatedPerson:
        obj = RelatedPerson(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_related(self, org: uuid.UUID, patient_id: uuid.UUID) -> Sequence[RelatedPerson]:
        r = await self.s.execute(select(RelatedPerson).where(RelatedPerson.org_id==org, RelatedPerson.patient_id==patient_id, RelatedPerson.deleted_at.is_(None))); return r.scalars().all()

    async def add_practitioner(self, org: uuid.UUID, **data) -> Practitioner:
        obj = Practitioner(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_practitioners(self, org: uuid.UUID) -> Sequence[Practitioner]:
        r = await self.s.execute(select(Practitioner).where(Practitioner.org_id==org, Practitioner.deleted_at.is_(None))); return r.scalars().all()

    async def add_location(self, org: uuid.UUID, **data) -> Location:
        obj = Location(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_locations(self, org: uuid.UUID) -> Sequence[Location]:
        r = await self.s.execute(select(Location).where(Location.org_id==org, Location.deleted_at.is_(None))); return r.scalars().all()