import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.consent.repository import ConsentRepository
from app.modules.consent.schemas import ConsentCreate, ConsentRevoke
from app.modules.consent.models import Consent
from app.modules.events.outbox import OutboxService

def _now(): return datetime.now(timezone.utc)

class ConsentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ConsentRepository(session)

    async def create(self, org_id: uuid.UUID, payload: ConsentCreate) -> Consent:
        data = payload.model_dump(exclude_unset=True)
        if data.get("effective_at") is None:
            data["effective_at"] = _now()
        obj = await self.repo.create(org_id, **data)
        await OutboxService(self.session).enqueue(
            org_id, "CONSENT_CAPTURED", "consent", obj.id,
            {"patient_id": str(obj.patient_id), "scope": obj.scope, "channel": obj.channel}
        )
        await self.session.commit()
        return obj

    async def list_for_patient(self, org_id: uuid.UUID, patient_id: uuid.UUID):
        return await self.repo.list_for_patient(org_id, patient_id)

    async def revoke(self, org_id: uuid.UUID, consent_id: uuid.UUID, payload: ConsentRevoke) -> Consent | None:
        when = payload.revoked_at or _now()
        obj = await self.repo.revoke(org_id, consent_id, when)
        if obj:
            await OutboxService(self.session).enqueue(
                org_id, "CONSENT_REVOKED", "consent", obj.id,
                {"patient_id": str(obj.patient_id), "scope": obj.scope}
            )
            await self.session.commit()
        return obj

    async def is_allowed(self, org_id: uuid.UUID, patient_id: uuid.UUID, scope: str) -> bool:
        return await self.repo.is_allowed(org_id, patient_id, scope, at=_now())