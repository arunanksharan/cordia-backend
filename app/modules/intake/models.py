import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, ForeignKey, TIMESTAMP, text, Boolean, Integer
from app.core.base import Base, TimestampedTenantMixin

# A session groups everything captured for a patient/lead before booking.
class IntakeSession(Base, TimestampedTenantMixin):
    # optional references
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversation.id"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(16), default="open")  # open | submitted | closed
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # channel/locale/etc.

class IntakeSummary(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    text: Mapped[str] = mapped_column(Text)

# Generic pattern: each record type references the session and stores both text and optional code(s).

class IntakeChiefComplaint(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"set":"complaint","code":"headache"}

class IntakeSymptom(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    client_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # idempotency key per-item
    code: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"set":"symptom","code":"headache"}
    onset: Mapped[str | None] = mapped_column(String(32), nullable=True)      # ISO date or relative text
    duration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)   # e.g., mild/moderate/severe
    frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    laterality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class IntakeAllergy(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    client_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)

class IntakeMedication(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    client_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str | None] = mapped_column(String(120), nullable=True)
    schedule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    adherence: Mapped[str | None] = mapped_column(String(64), nullable=True)

class IntakeConditionHistory(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    client_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    condition: Mapped[str] = mapped_column(String(160))
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # active/resolved/unknown
    year_or_age: Mapped[str | None] = mapped_column(String(32), nullable=True)

class IntakeFamilyHistory(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    client_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relative: Mapped[str] = mapped_column(String(64))    # father/mother/sibling/child/etc.
    condition: Mapped[str] = mapped_column(String(160))
    age_of_onset: Mapped[str | None] = mapped_column(String(32), nullable=True)

class IntakeSocialHistory(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    data: Mapped[dict] = mapped_column(JSON)  # {"smoking_status":"never","alcohol_use":"occasional","occupation":"..."}

class IntakeNote(Base, TimestampedTenantMixin):
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intakesession.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(16), default="internal")  # internal|external