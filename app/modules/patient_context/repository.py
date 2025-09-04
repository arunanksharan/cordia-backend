import uuid
from typing import Sequence, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.modules.patient_context.models import (
    PatientProfile, PatientIdentifier, PatientAddress, PatientCoverage,
    PatientTag, PatientSdoh, ExternalAccountLink
)

class PatientContextRepository:
    def __init__(self, s: AsyncSession): self.s = s

    # Generic helpers
    async def _list_by_patient(self, model: Type, org: uuid.UUID, patient_id: uuid.UUID):
        res = await self.s.execute(select(model).where(
            model.org_id==org, model.patient_id==patient_id, model.deleted_at.is_(None)
        ))
        return res.scalars().all()

    # Profile (1:1 upsert)
    async def upsert_profile(self, org: uuid.UUID, patient_id: uuid.UUID, data: dict) -> PatientProfile:
        res = await self.s.execute(select(PatientProfile).where(
            PatientProfile.org_id==org, PatientProfile.patient_id==patient_id, PatientProfile.deleted_at.is_(None)
        ))
        obj = res.scalar_one_or_none()
        if obj:
            for k,v in data.items(): setattr(obj, k, v)
        else:
            obj = PatientProfile(org_id=org, patient_id=patient_id, **data)
            self.s.add(obj)
        await self.s.flush(); return obj

    async def get_profile(self, org: uuid.UUID, patient_id: uuid.UUID) -> PatientProfile | None:
        res = await self.s.execute(select(PatientProfile).where(
            PatientProfile.org_id==org, PatientProfile.patient_id==patient_id, PatientProfile.deleted_at.is_(None)
        ))
        return res.scalar_one_or_none()

    # Identifiers
    async def add_identifier(self, org: uuid.UUID, data: dict) -> PatientIdentifier:
        obj = PatientIdentifier(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_identifiers(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self._list_by_patient(PatientIdentifier, org, patient_id)

    # Addresses
    async def add_address(self, org: uuid.UUID, data: dict) -> PatientAddress:
        obj = PatientAddress(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_addresses(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self._list_by_patient(PatientAddress, org, patient_id)

    # Coverage
    async def add_coverage(self, org: uuid.UUID, data: dict) -> PatientCoverage:
        obj = PatientCoverage(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_coverages(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self._list_by_patient(PatientCoverage, org, patient_id)

    # Tags
    async def add_tag(self, org: uuid.UUID, data: dict) -> PatientTag:
        obj = PatientTag(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_tags(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self._list_by_patient(PatientTag, org, patient_id)

    # SDOH
    async def upsert_sdoh(self, org: uuid.UUID, patient_id: uuid.UUID, data: dict) -> PatientSdoh:
        res = await self.s.execute(select(PatientSdoh).where(
            PatientSdoh.org_id==org, PatientSdoh.patient_id==patient_id, PatientSdoh.deleted_at.is_(None)
        ))
        obj = res.scalar_one_or_none()
        if obj: obj.data = data
        else:
            obj = PatientSdoh(org_id=org, patient_id=patient_id, data=data); self.s.add(obj)
        await self.s.flush(); return obj

    async def get_sdoh(self, org: uuid.UUID, patient_id: uuid.UUID) -> PatientSdoh | None:
        res = await self.s.execute(select(PatientSdoh).where(
            PatientSdoh.org_id==org, PatientSdoh.patient_id==patient_id, PatientSdoh.deleted_at.is_(None)
        ))
        return res.scalar_one_or_none()

    # External links
    async def add_external_link(self, org: uuid.UUID, data: dict) -> ExternalAccountLink:
        obj = ExternalAccountLink(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_external_links(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self._list_by_patient(ExternalAccountLink, org, patient_id)