import uuid
from pydantic import BaseModel, Field

class ContactPointCreate(BaseModel):
    owner_type: str = Field(..., pattern="^(patient|related_person)$")
    owner_id: uuid.UUID
    system: str = Field(..., pattern="^(phone|email|whatsapp)$")
    value: str
    use: str = Field(default="mobile", pattern="^(mobile|home|work)$")
    primary: bool = False

class ContactPointOut(ContactPointCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config: from_attributes = True

class RelatedPersonCreate(BaseModel):
    patient_id: uuid.UUID
    relationship: str
    name: str

class RelatedPersonOut(RelatedPersonCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config: from_attributes = True

class DirectoryCreate(BaseModel):
    display_name: str
    specialty: str | None = None
    address: str | None = None

class PractitionerOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    display_name: str
    specialty: str | None
    class Config: from_attributes = True

class LocationOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    display_name: str
    address: str | None
    class Config: from_attributes = True