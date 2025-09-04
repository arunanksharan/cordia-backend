import uuid
from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.modules.consent.models import Consent

class ConsentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Consent:
        obj = Consent(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, consent_id: uuid.UUID) -> Consent | None:
        q = select(Consent).where(
            Consent.id == consent_id,
            Consent.org_id == org_id,
            Consent.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list_for_patient(self, org_id: uuid.UUID, patient_id: uuid.UUID) -> Sequence[Consent]:
        q = select(Consent).where(
            Consent.org_id == org_id,
            Consent.patient_id == patient_id,
            Consent.deleted_at.is_(None),
        ).order_by(Consent.created_at.desc())
        res = await self.session.execute(q)
        return res.scalars().all()

    async def revoke(self, org_id: uuid.UUID, consent_id: uuid.UUID, when: datetime) -> Consent | None:
        c = await self.get(org_id, consent_id)
        if not c:
            return None
        c.revoked_at = when
        c.active = False
        await self.session.flush()
        return c

    async def is_allowed(self, org_id: uuid.UUID, patient_id: uuid.UUID, scope: str, at: datetime | None = None) -> bool:
        # True if an active consent for scope exists at time `at` (or now),
        # not expired, not revoked.
        t = at or datetime.now(timezone.utc)
        q = select(Consent).where(
            Consent.org_id == org_id,
            Consent.patient_id == patient_id,
            Consent.scope == scope,
            Consent.deleted_at.is_(None),
            Consent.active.is_(True),
            Consent.effective_at <= t,
            or_(Consent.expires_at.is_(None), Consent.expires_at > t),
            Consent.revoked_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none() is not None