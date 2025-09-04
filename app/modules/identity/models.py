import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Boolean
from app.core.base import Base, TimestampedTenantMixin

class ContactPoint(Base, TimestampedTenantMixin):
    owner_type: Mapped[str] = mapped_column(String(16))  # patient | related_person
    owner_id: Mapped[uuid.UUID] = mapped_column()
    system: Mapped[str] = mapped_column(String(16))      # phone | email | whatsapp
    value: Mapped[str] = mapped_column(String(128))
    use: Mapped[str] = mapped_column(String(16), default="mobile")  # mobile | home | work
    primary: Mapped[bool] = mapped_column(default=False)

class RelatedPerson(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient.id"))
    relationship: Mapped[str] = mapped_column(String(32))  # guardian | caregiver | spouse | parent | child | other
    name: Mapped[str] = mapped_column(String(120))

class Practitioner(Base, TimestampedTenantMixin):
    display_name: Mapped[str] = mapped_column(String(120))
    specialty: Mapped[str | None] = mapped_column(String(64), nullable=True)

class Location(Base, TimestampedTenantMixin):
    display_name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)