import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.conversations.models import Channel, Conversation, Message
from app.modules.media.models import MediaAsset

class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Channel:
        obj = Channel(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list(self, org_id: uuid.UUID) -> Sequence[Channel]:
        res = await self.session.execute(select(Channel).where(Channel.org_id == org_id, Channel.deleted_at.is_(None)))
        return res.scalars().all()

class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Conversation:
        obj = Conversation(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, cid: uuid.UUID) -> Conversation | None:
        q = select(Conversation).where(
            Conversation.id == cid,
            Conversation.org_id == org_id,
            Conversation.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, **data) -> Message:
        obj = Message(org_id=org_id, **data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list_for_conversation(self, org_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 50, offset: int = 0):
        q = select(Message).where(
            Message.org_id == org_id,
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        ).order_by(Message.created_at.asc()).limit(limit).offset(offset)
        res = await self.session.execute(q)
        return res.scalars().all()