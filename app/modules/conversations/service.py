import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.conversations.repository import (
    ChannelRepository, ConversationRepository, MessageRepository
)
from app.modules.conversations.transcripts import TranscriptRepository, Transcript
from app.modules.conversations.schemas import (
    ChannelCreate, ConversationCreate, MessageCreate, TranscriptCreate
)
from app.modules.media.repository import MediaRepository

class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.channels = ChannelRepository(session)
        self.convos = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.media = MediaRepository(session)
        self.transcripts = TranscriptRepository(session)

    # Channels
    async def create_channel(self, org_id: uuid.UUID, payload: ChannelCreate):
        obj = await self.channels.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def list_channels(self, org_id: uuid.UUID):
        return await self.channels.list(org_id)

    # Conversations
    async def create_conversation(self, org_id: uuid.UUID, payload: ConversationCreate):
        obj = await self.convos.create(org_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj

    async def get_conversation(self, org_id: uuid.UUID, cid: uuid.UUID):
        return await self.convos.get(org_id, cid)

    # Messages
    async def create_message(self, org_id: uuid.UUID, conversation_id: uuid.UUID, payload: MessageCreate):
        # Validate conversation exists
        conv = await self.convos.get(org_id, conversation_id)
        if not conv:
            return None, "conversation_not_found"

        # If content_type=media, validate media exists in same org
        if payload.content_type == "media":
            if not payload.media_id:
                return None, "media_required"
            m = await self.media.get(org_id, payload.media_id)
            if not m:
                return None, "media_not_found"

        obj = await self.messages.create(org_id, conversation_id=conversation_id, **payload.model_dump(exclude_unset=True))
        await self.session.commit()

        # If text_body present, auto-create a transcript row linked to message (useful for RAG)
        if payload.content_type == "text" and payload.text_body:
            await self.transcripts.create(org_id, message_id=obj.id, media_id=None, language=payload.locale or "en", text=payload.text_body, confidence_avg=None)
            await self.session.commit()

        return obj, None

    async def list_messages(self, org_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 50, offset: int = 0):
        return await self.messages.list_for_conversation(org_id, conversation_id, limit, offset)

    # Transcripts
    async def create_transcript(self, org_id: uuid.UUID, data: TranscriptCreate):
        if not data.message_id and not data.media_id:
            return None, "target_required"
        obj = await self.transcripts.create(org_id, **data.model_dump(exclude_unset=True))
        await self.session.commit()
        return obj, None