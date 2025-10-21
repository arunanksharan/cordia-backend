from pydantic import BaseModel, Field
import uuid
from datetime import datetime

# ---- Appointments ----

class AppointmentRequest(BaseModel):
    patient_id: uuid.UUID
    requested_start: datetime
    requested_end: datetime | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    practitioner_name: str | None = None
    location_name: str | None = None

class AppointmentConfirm(BaseModel):
    confirmed_start: datetime
    confirmed_end: datetime | None = None
    practitioner_name: str | None = None
    location_name: str | None = None

class AppointmentUpdate(BaseModel):
    # allow updating a subset of fields
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    practitioner_name: str | None = None
    location_name: str | None = None

class AppointmentStatusChange(BaseModel):
    status: str

class AppointmentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    # TODO: add all fields

# ---- Waitlist ----

class WaitlistCreate(BaseModel):
    patient_id: uuid.UUID
    reason_code: str | None = None
    reason_text: str | None = None
    practitioner_name: str | None = None
    location_name: str | None = None
    earliest_start: datetime | None = None
    latest_end: datetime | None = None

class WaitlistUpdate(BaseModel):
    rank: int | None = None
    status: str | None = None

class WaitlistOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID
    rank: int
    status: str
    created_at: datetime
    updated_at: datetime

# ---- Check-in ----

class CheckinCreate(BaseModel):
    forms_completed: bool = False
    payment_collected: bool = False

class CheckinOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    appointment_id: uuid.UUID
    created_at: datetime

class BookAppointmentRequest(BaseModel):
    conversation_id: uuid.UUID
    preferred_time: str | None = None

class N8nBookingResponse(BaseModel):
    intent: str | None = None
    preferred_time: str | None = None
    preferred_location: str | None = None

class N8nBookingResponsePayload(BaseModel):
    conversation_id: uuid.UUID
    booking_response: N8nBookingResponse | None = None
    reply_to_user: str | None = None

class DepartmentInfo(BaseModel):
    name: str
    reason: str

class N8nDepartmentTriagePayload(BaseModel):
    conversation_id: uuid.UUID
    best_department: DepartmentInfo