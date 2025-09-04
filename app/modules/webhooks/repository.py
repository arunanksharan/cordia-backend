import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.webhooks.models import WebhookSubscription

class WebhookRepository:
    def __init__(self, s: AsyncSession): self.s = s
    async def create(self, org: uuid.UUID, **data) -> WebhookSubscription:
        obj = WebhookSubscription(org_id=org, **data); self.s.add(obj); await self.s.flush(); return obj
    async def list_active(self, org: uuid.UUID) -> Sequence[WebhookSubscription]:
        r = await self.s.execute(select(WebhookSubscription).where(WebhookSubscription.org_id==org, WebhookSubscription.active.is_(True), WebhookSubscription.deleted_at.is_(None)))
        return r.scalars().all()