import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, TIMESTAMP, text, ForeignKey, JSON, Boolean
from app.core.base import Base, TimestampedTenantMixin

class Appointment(Base, TimestampedTenantMixin):
    # Relationships kept lightweight (nullable FK to patient; others as plain fields for now)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)

    # Scheduling
    status: Mapped[str] = mapped_column(String(24), default="requested")  # requested, pending_confirm, confirmed, rescheduled, canceled, no_show, completed
    reason_code: Mapped[str | None] = mapped_column(String(48), nullable=True)  # consult, followup, diagnostics, admission, discharge_meet, other
    channel_origin: Mapped[str | None] = mapped_column(String(24), nullable=True)  # phone, whatsapp, web, in_person, email

    # Preferences and final slot
    requested_start: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    requested_end: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    confirmed_start: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    confirmed_end: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    location_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # keeping simple; can FK to location later
    practitioner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # can FK to practitioner later

    reschedule_count: Mapped[int] = mapped_column(default=0)
    no_show_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    # Freeform metadata container (forms completed, notes, etc.)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class WaitlistEntry(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    # Preferences (days/times/provider/location) encoded as JSON for flexibility
    preferences: Mapped[dict] = mapped_column(JSON)  # e.g., {"days":["Mon","Tue"],"times":["morning"],"location":"Koramangala"}
    reason_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    practitioner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rank: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CheckinMeta(Base, TimestampedTenantMixin):
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointment.id"))
    forms_completed: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # e.g., {"demographics": true, "consent": true}
    payment_collected: Mapped[bool] = mapped_column(Boolean, default=False)