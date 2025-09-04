import uuid
from pydantic import BaseModel, Field

class IntakeSessionCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    context: dict | None = None

class IntakeSessionOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    status: str
    patient_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    context: dict | None
    class Config: from_attributes = True

class ChiefComplaint(BaseModel):
    text: str
    codes: dict | None = None

class SymptomItem(BaseModel):
    client_item_id: str | None = None
    code: dict | None = None
    onset: str | None = None
    duration: str | None = None
    severity: str | None = Field(default=None, pattern="^(mild|moderate|severe|unknown)?$")
    frequency: str | None = None
    laterality: str | None = None
    notes: str | None = None

class AllergyItem(BaseModel):
    client_item_id: str | None = None
    substance: str
    reaction: str | None = None
    severity: str | None = None

class MedicationItem(BaseModel):
    client_item_id: str | None = None
    name: str
    dose: str | None = None
    schedule: str | None = None
    adherence: str | None = None

class ConditionHistoryItem(BaseModel):
    client_item_id: str | None = None
    condition: str
    status: str | None = None
    year_or_age: str | None = None

class FamilyHistoryItem(BaseModel):
    client_item_id: str | None = None
    relative: str
    condition: str
    age_of_onset: str | None = None

class SocialHistory(BaseModel):
    smoking_status: str | None = None
    alcohol_use: str | None = None
    occupation: str | None = None
    other: dict | None = None

class NoteItem(BaseModel):
    text: str
    visibility: str = Field(default="internal", pattern="^(internal|external)$")

class IntakeRecordsUpsert(BaseModel):
    chief_complaint: ChiefComplaint | None = None
    symptoms: list[SymptomItem] | None = None
    allergies: list[AllergyItem] | None = None
    medications: list[MedicationItem] | None = None
    condition_history: list[ConditionHistoryItem] | None = None
    family_history: list[FamilyHistoryItem] | None = None
    social_history: SocialHistory | None = None
    notes: list[NoteItem] | None = None

class IntakeSummaryUpdate(BaseModel):
    text: str

class IntakeSubmit(BaseModel):
    ready_for_booking: bool = True