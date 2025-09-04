import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Enum, Integer, Text
from app.core.base import Base, TimestampedTenantMixin

class Channel(Base, TimestampedTenantMixin):
    # type: phone, whatsapp, sms, email, webchat, in_person
    type: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recording_allowed: Mapped[bool] = mapped_column(default=True)

class Conversation(Base, TimestampedTenantMixin):
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_owner_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open, pending, snoozed, closed
    priority: Mapped[str] = mapped_column(String(8), default="p2")

class Message(Base, TimestampedTenantMixin):
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation.id"))
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channel.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String(16))  # inbound/outbound
    actor_type: Mapped[str] = mapped_column(String(16))  # patient, related_person, agent, bot, system
    content_type: Mapped[str] = mapped_column(String(16), default="text")  # text/media
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mediaasset.id"), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)