import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from app.core.base import Base, TimestampedTenantMixin

class Practitioner(Base, TimestampedTenantMixin):
    __tablename__ = "practitioner"  # <— matches ForeignKey("practitioner.id")
    name: Mapped[str] = mapped_column(String(160), index=True)
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

class Location(Base, TimestampedTenantMixin):
    __tablename__ = "location"      # <— matches ForeignKey("location.id")
    name: Mapped[str] = mapped_column(String(160), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)