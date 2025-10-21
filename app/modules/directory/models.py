import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Text, ForeignKey
from app.core.base import Base, TimestampedTenantMixin

class Practitioner(Base, TimestampedTenantMixin):
    __tablename__ = "practitioner"
    name: Mapped[str] = mapped_column(String(160), index=True)
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    designation: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_of_expertise: Mapped[str | None] = mapped_column(Text, nullable=True)
    awards_recognition: Mapped[str | None] = mapped_column(Text, nullable=True)

class Location(Base, TimestampedTenantMixin):
    __tablename__ = "location"
    name: Mapped[str] = mapped_column(String(160), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)