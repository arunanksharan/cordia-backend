import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, TIMESTAMP, ForeignKey, text, Boolean
from app.core.base import Base, TimestampedTenantMixin

# Simple recurring schedule: day_of_week 0=Mon..6=Sun, minutes past midnight
class PractitionerSchedule(Base, TimestampedTenantMixin):
    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioner.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("location.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0..6
    start_minute: Mapped[int] = mapped_column(Integer)  # e.g., 9*60
    end_minute: Mapped[int] = mapped_column(Integer)    # e.g., 17*60
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    active: Mapped[bool] = mapped_column(default=True)

# Ephemeral hold to prevent race conditions
class AvailabilityHold(Base, TimestampedTenantMixin):
    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioner.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("location.id"))
    start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    intake_session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("intakesession.id"), nullable=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)