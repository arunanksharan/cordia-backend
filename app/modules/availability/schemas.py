import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class ScheduleCreate(BaseModel):
    practitioner_id: uuid.UUID
    location_id: uuid.UUID
    day_of_week: int = Field(ge=0, le=6)
    start_minute: int = Field(ge=0, le=24*60-1)
    end_minute: int = Field(ge=1, le=24*60)
    slot_minutes: int = Field(default=30, ge=5, le=240)
    active: bool = True

class ScheduleOut(ScheduleCreate):
    id: uuid.UUID
    org_id: uuid.UUID
    class Config: from_attributes = True

class SlotsQuery(BaseModel):
    practitioner_id: uuid.UUID
    location_id: uuid.UUID
    start: datetime
    end: datetime
    duration: int = 30  # minutes
    reason_code: str | None = None

class SlotOut(BaseModel):
    id: str
    start: datetime
    end: datetime
    practitioner_id: uuid.UUID
    location_id: uuid.UUID
    state: str

class HoldCreate(BaseModel):
    slot_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    practitioner_id: uuid.UUID
    location_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    intake_session_id: uuid.UUID | None = None

class HoldOut(BaseModel):
    hold_token: str
    expires_at: datetime

class BookRequest(BaseModel):
    hold_token: str
    patient_id: uuid.UUID
    intake_session_id: uuid.UUID | None = None
    reason_code: str | None = None
    contact: dict | None = None
    metadata: dict | None = None