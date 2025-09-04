from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.core.base import Base, TimestampedTenantMixin

class Patient(Base, TimestampedTenantMixin):
    legal_name: Mapped[str] = mapped_column(String(200))
    preferred_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)