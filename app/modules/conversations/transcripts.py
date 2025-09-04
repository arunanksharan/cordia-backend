import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Text, Float
from app.core.base import Base, TimestampedTenantMixin

class Transcript(Base, TimestampedTenantMixin):
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("message.id"), nullable=True)
    media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mediaasset.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    text: Mapped[str] = mapped_column(Text)
    confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

class TranscriptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Transcript:
        obj = Transcript(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list_for_message(self, org_id: uuid.UUID, message_id: uuid.UUID):
        q = select(Transcript).where(
            Transcript.org_id == org_id,
            Transcript.message_id == message_id,
            Transcript.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalars().all()