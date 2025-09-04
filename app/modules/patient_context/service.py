import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.patient_context.repository import PatientContextRepository
from app.modules.events.outbox import OutboxService
from app.modules.consent.service import ConsentService

class PatientContextService:
    def __init__(self, s: AsyncSession):
        self.s = s
        self.repo = PatientContextRepository(s)

    async def _check_consent(self, org: uuid.UUID, patient_id: uuid.UUID) -> bool:
        # Require data_processing to read/write rich demographics/preferences
        return await ConsentService(self.s).is_allowed(org, patient_id, "data_processing")

    # Profile
    async def upsert_profile(self, org: uuid.UUID, data: dict):
        pid = data["patient_id"]
        if not await self._check_consent(org, pid): return None, "consent_required"
        obj = await self.repo.upsert_profile(org, pid, {k:v for k,v in data.items() if k!="patient_id"})
        await OutboxService(self.s).enqueue(org, "PATIENT_PROFILE_UPSERTED", "patient", pid, {})
        await self.s.commit(); return obj, None

    async def get_profile(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.get_profile(org, patient_id), None

    # Identifiers
    async def add_identifier(self, org: uuid.UUID, data: dict):
        if not await self._check_consent(org, data["patient_id"]): return None, "consent_required"
        obj = await self.repo.add_identifier(org, data)
        await OutboxService(self.s).enqueue(org, "PATIENT_IDENTIFIER_ADDED", "patient", data["patient_id"], {"system": data["system"]})
        await self.s.commit(); return obj, None

    async def list_identifiers(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.list_identifiers(org, patient_id), None

    # Addresses
    async def add_address(self, org: uuid.UUID, data: dict):
        if not await self._check_consent(org, data["patient_id"]): return None, "consent_required"
        obj = await self.repo.add_address(org, data)
        await OutboxService(self.s).enqueue(org, "PATIENT_ADDRESS_ADDED", "patient", data["patient_id"], {"use": data["use"]})
        await self.s.commit(); return obj, None

    async def list_addresses(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.list_addresses(org, patient_id), None

    # Coverage
    async def add_coverage(self, org: uuid.UUID, data: dict):
        if not await self._check_consent(org, data["patient_id"]): return None, "consent_required"
        obj = await self.repo.add_coverage(org, data)
        await OutboxService(self.s).enqueue(org, "PATIENT_COVERAGE_ADDED", "patient", data["patient_id"], {"payer": data["payer"]})
        await self.s.commit(); return obj, None

    async def list_coverages(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.list_coverages(org, patient_id), None

    # Tags
    async def add_tag(self, org: uuid.UUID, data: dict):
        if not await self._check_consent(org, data["patient_id"]): return None, "consent_required"
        obj = await self.repo.add_tag(org, data)
        await OutboxService(self.s).enqueue(org, "PATIENT_TAG_ADDED", "patient", data["patient_id"], {"tag": data["tag"]})
        await self.s.commit(); return obj, None

    async def list_tags(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.list_tags(org, patient_id), None

    # SDOH
    async def upsert_sdoh(self, org: uuid.UUID, patient_id: uuid.UUID, data: dict):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        obj = await self.repo.upsert_sdoh(org, patient_id, data)
        await OutboxService(self.s).enqueue(org, "PATIENT_SDOH_UPSERTED", "patient", patient_id, {})
        await self.s.commit(); return obj, None

    async def get_sdoh(self, org: uuid.UUID, patient_id: uuid.UUID):
        if not await self._check_consent(org, patient_id): return None, "consent_required"
        return await self.repo.get_sdoh(org, patient_id), None

    # External links
    async def add_external_link(self, org: uuid.UUID, data: dict):
        obj = await self.repo.add_external_link(org, data)  # linking account may precede consent; treat as system link
        await OutboxService(self.s).enqueue(org, "PATIENT_EXTERNAL_LINK_ADDED", "patient", data["patient_id"], {"provider": data["provider"]})
        await self.s.commit(); return obj, None

    async def list_external_links(self, org: uuid.UUID, patient_id: uuid.UUID):
        return await self.repo.list_external_links(org, patient_id), None