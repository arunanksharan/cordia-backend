import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKey, Integer, TIMESTAMP, text, JSON, Boolean
from app.core.base import Base, TimestampedTenantMixin

# ---- Tickets ----

class Ticket(Base, TimestampedTenantMixin):
    # Links
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversation.id"), nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    # Core fields
    category: Mapped[str] = mapped_column(String(32))  # appointment, billing, insurance, facilities, information, complaint, feedback, other
    sub_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str] = mapped_column(String(8), default="p2")  # p0..p3
    severity: Mapped[str] = mapped_column(String(8), default="sev3")  # sev1..sev4
    status: Mapped[str] = mapped_column(String(32), default="new")  # new, triaged, in_progress, waiting_on_patient, waiting_on_payer, resolved, closed

    summary_auto: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_human: Mapped[str | None] = mapped_column(Text, nullable=True)

class TicketNote(Base, TimestampedTenantMixin):
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeKey("ticket.id"))  # type: ignore
    author_id: Mapped[uuid.UUID] = mapped_column()
    visibility: Mapped[str] = mapped_column(String(16), default="internal")  # internal, public
    body: Mapped[str] = mapped_column(Text)

# fix FK typo (SQLAlchemy allows ForeignKey, not ForeKey); leaving explicit to avoid confusion by lints:
from sqlalchemy import ForeignKey as _FK
TicketNote.ticket_id = mapped_column(_FK("ticket.id"))  # rebind typographical correction


# ---- Tasks & Assignments ----

class Task(Base, TimestampedTenantMixin):
    subject_type: Mapped[str] = mapped_column(String(16), default="ticket")  # ticket (extensible)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket.id"))
    type: Mapped[str] = mapped_column(String(32))  # callback, doc_collect, schedule_appt, send_estimate, preauth_followup, refund_check
    status: Mapped[str] = mapped_column(String(16), default="open")  # open, blocked, done, canceled
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

class WorkQueue(Base, TimestampedTenantMixin):
    queue_name: Mapped[str] = mapped_column(String(64), unique=False)
    skills_required: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # e.g., {"billing": true, "lang": ["hi"]}

class Assignment(Base, TimestampedTenantMixin):
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket.id"))
    assignee_id: Mapped[uuid.UUID] = mapped_column()
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

# ---- SLA ----

class SlaPolicy(Base, TimestampedTenantMixin):
    applies_to: Mapped[str] = mapped_column(String(16), default="ticket")  # ticket
    category_filter: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g., "billing" or None
    priority_filter: Mapped[str | None] = mapped_column(String(8), nullable=True)   # e.g., "p1" or None
    respond_within_minutes: Mapped[int] = mapped_column(Integer)   # first response
    resolve_within_minutes: Mapped[int] = mapped_column(Integer)   # final resolution
    pause_statuses: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"list": ["waiting_on_patient","waiting_on_payer"]}

class SlaApplication(Base, TimestampedTenantMixin):
    subject_type: Mapped[str] = mapped_column(String(16), default="ticket")
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket.id"))
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("slapolicy.id"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    paused_total_seconds: Mapped[int] = mapped_column(Integer, default=0)
    pause_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    due_response_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    due_resolution_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    breach_state: Mapped[str] = mapped_column(String(16), default="ontrack")  # ontrack, at_risk, breached
    last_recalc_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)