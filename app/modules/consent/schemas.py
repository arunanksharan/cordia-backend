import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class ConsentCreate(BaseModel):
    patient_id: uuid.UUID
    scope: str = Field(..., pattern="^(recording|marketing|reminders|data_processing)$")
    channel: str | None = Field(default=None, pattern="^(whatsapp|phone|email|web|any)$")
    lawful_basis: str = Field(default="consent", pattern="^(consent|contract|legitimate_interest|legal_obligation)$")
    evidence_media_id: uuid.UUID | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None

class ConsentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID
    scope: str
    channel: str | None
    lawful_basis: str
    evidence_media_id: uuid.UUID | None
    effective_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    active: bool

    class Config:
        from_attributes = True

class ConsentRevoke(BaseModel):
    revoked_at: datetime | None = None