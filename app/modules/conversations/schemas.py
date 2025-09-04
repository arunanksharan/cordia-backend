import uuid
from pydantic import BaseModel, Field

# Channels
class ChannelCreate(BaseModel):
    type: str = Field(..., pattern="^(phone|whatsapp|sms|email|webchat|in_person)$")
    provider: str | None = None
    account_id: str | None = None
    recording_allowed: bool = True

class ChannelOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    type: str
    provider: str | None
    account_id: str | None
    recording_allowed: bool

    class Config:
        from_attributes = True

# Conversations
class ConversationCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    subject: str | None = None
    priority: str = Field(default="p2", pattern="^p[0-3]$")

class ConversationOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID | None
    subject: str | None
    status: str
    priority: str

    class Config:
        from_attributes = True

# Messages
class MessageCreate(BaseModel):
    channel_id: uuid.UUID | None = None
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    actor_type: str = Field(..., pattern="^(patient|related_person|agent|bot|system)$")
    content_type: str = Field(default="text", pattern="^(text|media)$")
    text_body: str | None = None
    media_id: uuid.UUID | None = None
    locale: str | None = None

class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    org_id: uuid.UUID
    direction: str
    actor_type: str
    content_type: str
    text_body: str | None
    media_id: uuid.UUID | None
    locale: str | None

    class Config:
        from_attributes = True

# Transcripts
class TranscriptCreate(BaseModel):
    # Create a transcript for either message_id or media_id (one must be provided)
    message_id: uuid.UUID | None = None
    media_id: uuid.UUID | None = None
    language: str = "en"
    text: str
    confidence_avg: float | None = None

class TranscriptOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    message_id: uuid.UUID | None
    media_id: uuid.UUID | None
    language: str
    text: str
    confidence_avg: float | None

    class Config:
        from_attributes = True