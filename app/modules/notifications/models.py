from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON
from app.core.base import Base, TimestampedTenantMixin

class MessageTemplate(Base, TimestampedTenantMixin):
    channel: Mapped[str] = mapped_column(String(16))  # sms | email | whatsapp
    name: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text)

class OutboundMessage(Base, TimestampedTenantMixin):
    channel: Mapped[str] = mapped_column(String(16))
    to: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | sent | failed