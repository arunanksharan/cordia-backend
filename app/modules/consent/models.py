import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, TIMESTAMP, Boolean, ForeignKey, text
from app.core.base import Base, TimestampedTenantMixin

class Consent(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"))
    scope: Mapped[str] = mapped_column(String(32))      # recording | marketing | reminders | data_processing
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)  # whatsapp | phone | email | web | any
    lawful_basis: Mapped[str] = mapped_column(String(32), default="consent")  # consent | contract | legitimate_interest | legal_obligation
    evidence_media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mediaasset.id"), nullable=True)

    effective_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)