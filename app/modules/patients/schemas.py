import uuid
from pydantic import BaseModel, EmailStr, Field

class PatientCreate(BaseModel):
    legal_name: str = Field(..., min_length=1, max_length=200)
    preferred_name: str | None = None
    primary_phone: str | None = None
    primary_email: EmailStr | None = None
    lang: str | None = None
    timezone: str | None = None

class PatientUpdate(BaseModel):
    legal_name: str | None = None
    preferred_name: str | None = None
    primary_phone: str | None = None
    primary_email: EmailStr | None = None
    lang: str | None = None
    timezone: str | None = None

class PatientOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    legal_name: str
    preferred_name: str | None
    primary_phone: str | None
    primary_email: str | None
    lang: str | None
    timezone: str | None

    class Config:
        from_attributes = True