import uuid
from pydantic import BaseModel, Field

class IngestTranscriptsByConversation(BaseModel):
    conversation_id: uuid.UUID
    chunk_chars: int = Field(default=800, ge=200, le=4000)
    overlap: int = Field(default=120, ge=0, le=1000)

class IngestMessageTranscript(BaseModel):
    message_id: uuid.UUID
    chunk_chars: int = Field(default=800, ge=200, le=4000)
    overlap: int = Field(default=120, ge=0, le=1000)

class IngestTicketNotes(BaseModel):
    ticket_id: uuid.UUID
    chunk_chars: int = 800
    overlap: int = 120

class IngestKnowledge(BaseModel):
    title: str | None = None
    text: str
    patient_id: uuid.UUID | None = None
    chunk_chars: int = 1000
    overlap: int = 150

class SearchQuery(BaseModel):
    q: str
    top_k: int = Field(default=10, ge=1, le=50)
    patient_id: uuid.UUID | None = None
    source_type: str | None = Field(default=None, pattern="^(transcript|ticket_note|knowledge)$")

class ChunkOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    source_type: str
    source_id: str
    patient_id: uuid.UUID | None
    locator: dict | None
    text: str
    chunk_index: int
    score: float

    class Config:
        from_attributes = True