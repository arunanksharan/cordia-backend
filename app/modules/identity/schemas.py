import uuid
from pydantic import BaseModel, Field

class ContactPointCreate(BaseModel):
    system: str = Field(..., pattern="^(phone|email|whatsapp)$")
    value: str
    use: str = Field(default="mobile", pattern="^(mobile|home|work)$")
    primary: bool = False

class ContactPointOut(BaseModel):
    id: uuid.UUID
    system: str
    value: str
    use: str
    primary: bool

class RelatedPersonCreate(BaseModel):
    patient_id: uuid.UUID
    relationship: str
    name: str

class RelatedPersonOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    relationship: str
    name: str

class DirectoryCreate(BaseModel):
    display_name: str

class IdentityProviderOut(BaseModel):
    id: uuid.UUID
    display_name: str
    specialty: str | None

class IdentityLocationOut(BaseModel):
    id: uuid.UUID
    display_name: str
    address: str | None