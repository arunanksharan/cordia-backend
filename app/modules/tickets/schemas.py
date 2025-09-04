import uuid
from datetime import datetime
from pydantic import BaseModel, Field

# ---- Tickets ----

class TicketCreate(BaseModel):
    category: str = Field(..., pattern="^(appointment|billing|insurance|facilities|information|complaint|feedback|other)$")
    sub_category: str | None = None
    priority: str = Field(default="p2", pattern="^p[0-3]$")
    severity: str = Field(default="sev3", pattern="^sev[1-4]$")
    patient_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    summary_human: str | None = None

class TicketUpdate(BaseModel):
    category: str | None = None
    sub_category: str | None = None
    priority: str | None = Field(default=None, pattern="^p[0-3]$")
    severity: str | None = Field(default=None, pattern="^sev[1-4]$")
    status: str | None = Field(default=None, pattern="^(new|triaged|in_progress|waiting_on_patient|waiting_on_payer|resolved|closed)$")
    summary_human: str | None = None
    summary_auto: str | None = None

class TicketOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    category: str
    sub_category: str | None
    priority: str
    severity: str
    status: str
    patient_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    summary_human: str | None
    summary_auto: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True

# ---- Notes ----

class TicketNoteCreate(BaseModel):
    body: str
    visibility: str = Field(default="internal", pattern="^(internal|public)$")
    author_id: uuid.UUID

class TicketNoteOut(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    org_id: uuid.UUID
    body: str
    visibility: str
    author_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ---- Tasks ----

class TaskCreate(BaseModel):
    type: str = Field(..., pattern="^(callback|doc_collect|schedule_appt|send_estimate|preauth_followup|refund_check)$")
    assignee_id: uuid.UUID | None = None
    due_at: datetime | None = None

class TaskUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|blocked|done|canceled)$")
    assignee_id: uuid.UUID | None = None
    due_at: datetime | None = None

class TaskOut(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    org_id: uuid.UUID
    type: str
    status: str
    assignee_id: uuid.UUID | None
    due_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

# ---- Assignment ----

class AssignmentCreate(BaseModel):
    assignee_id: uuid.UUID
    reason: str | None = None

class AssignmentOut(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    org_id: uuid.UUID
    assignee_id: uuid.UUID
    reason: str | None
    assigned_at: datetime

    class Config:
        from_attributes = True

# ---- SLA ----

class SlaPolicyCreate(BaseModel):
    applies_to: str = Field(default="ticket", pattern="^ticket$")
    category_filter: str | None = None
    priority_filter: str | None = Field(default=None, pattern="^p[0-3]$")
    respond_within_minutes: int = Field(..., ge=1)
    resolve_within_minutes: int = Field(..., ge=1)
    pause_statuses: dict | None = Field(default={"list": ["waiting_on_patient", "waiting_on_payer"]})

class SlaPolicyOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    applies_to: str
    category_filter: str | None
    priority_filter: str | None
    respond_within_minutes: int
    resolve_within_minutes: int
    pause_statuses: dict | None

    class Config:
        from_attributes = True

class SlaRecalcResult(BaseModel):
    ticket_id: uuid.UUID
    breach_state: str
    due_response_at: datetime
    due_resolution_at: datetime
    last_recalc_at: datetime