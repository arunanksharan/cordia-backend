import uuid
from datetime import date
from pydantic import BaseModel, Field

# Base outs share from_attributes = True
class _Cfg: from_attributes = True

class ProfileUpsert(BaseModel):
    patient_id: uuid.UUID
    dob: date | None = None
    sex_at_birth: str | None = Field(default=None, pattern="^(male|female|intersex|unknown)?$")
    gender_identity: str | None = None
    pronouns: str | None = None
    language: str | None = None
    timezone: str | None = None
    interpreter_needed: bool | None = None
    accessibility: dict | None = None
    contact_preferences: dict | None = None

class ProfileOut(ProfileUpsert):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class IdentifierCreate(BaseModel):
    patient_id: uuid.UUID
    system: str
    type: str | None = None
    value: str

class IdentifierOut(IdentifierCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class AddressCreate(BaseModel):
    patient_id: uuid.UUID
    use: str = Field(..., pattern="^(home|work|mailing|temp)$")
    line1: str
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    geocode: dict | None = None

class AddressOut(AddressCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class CoverageCreate(BaseModel):
    patient_id: uuid.UUID
    payer: str
    plan: str | None = None
    member_id: str | None = None
    group_id: str | None = None
    period: dict | None = None
    relationship: str | None = Field(default=None, pattern="^(self|spouse|child|other)?$")
    is_primary: bool = True

class CoverageOut(CoverageCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class TagCreate(BaseModel):
    patient_id: uuid.UUID
    tag: str
    source: str | None = None

class TagOut(TagCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class SdohUpsert(BaseModel):
    patient_id: uuid.UUID
    data: dict

class SdohOut(SdohUpsert):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass

class ExternalLinkCreate(BaseModel):
    patient_id: uuid.UUID
    provider: str
    subject: str
    meta: dict | None = None

class ExternalLinkOut(ExternalLinkCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config(_Cfg): pass