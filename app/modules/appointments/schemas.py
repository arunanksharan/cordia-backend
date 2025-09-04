import uuid
from datetime import datetime
from pydantic import BaseModel, Field

# ---- Appointment ----

class AppointmentRequest(BaseModel):
    patient_id: uuid.UUID | None = None
    reason_code: str | None = Field(default=None, pattern="^(consult|followup|diagnostics|admission|discharge_meet|other)$")
    channel_origin: str | None = Field(default=None, pattern="^(phone|whatsapp|web|in_person|email)$")
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    location_name: str | None = None
    practitioner_name: str | None = None
    meta: dict | None = None

class AppointmentConfirm(BaseModel):
    confirmed_start: datetime
    confirmed_end: datetime
    location_name: str | None = None
    practitioner_name: str | None = None

class AppointmentUpdate(BaseModel):
    # limited updates while in confirmed/pending states
    reason_code: str | None = Field(default=None, pattern="^(consult|followup|diagnostics|admission|discharge_meet|other)$")
    location_name: str | None = None
    practitioner_name: str | None = None
    meta: dict | None = None

class AppointmentStatusChange(BaseModel):
    status: str = Field(..., pattern="^(pending_confirm|confirmed|rescheduled|canceled|no_show|completed)$")

class AppointmentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID | None
    status: str
    reason_code: str | None
    channel_origin: str | None
    requested_start: datetime | None
    requested_end: datetime | None
    confirmed_start: datetime | None
    confirmed_end: datetime | None
    location_name: str | None
    practitioner_name: str | None
    reschedule_count: int
    no_show_flag: bool
    meta: dict | None
    created_at: datetime

    class Config:
        from_attributes = True

# ---- Waitlist ----

class WaitlistCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    preferences: dict = Field(default_factory=dict)
    reason_code: str | None = None
    location_name: str | None = None
    practitioner_name: str | None = None
    rank: int = 0
    expires_at: datetime | None = None

class WaitlistUpdate(BaseModel):
    preferences: dict | None = None
    rank: int | None = None
    active: bool | None = None
    expires_at: datetime | None = None

class WaitlistOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID | None
    preferences: dict
    reason_code: str | None
    location_name: str | None
    practitioner_name: str | None
    rank: int
    active: bool
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

# ---- Check-in ----

class CheckinCreate(BaseModel):
    forms_completed: dict | None = None
    payment_collected: bool = False

class CheckinOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    appointment_id: uuid.UUID
    forms_completed: dict | None
    payment_collected: bool

    class Config:
        from_attributes = True