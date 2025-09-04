import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, TIMESTAMP, text, Boolean
from app.core.base import Base, TimestampedTenantMixin

class AuditEvent(Base, TimestampedTenantMixin):
    # who / tenant
    actor_user_id: Mapped[uuid.UUID] = mapped_column()
    # What happened
    action: Mapped[str] = mapped_column(String(24))  # read | write | export | delete | admin
    resource_type: Mapped[str] = mapped_column(String(48))  # patient | media | message | ticket | appointment | consent | ...
    resource_id: Mapped[str] = mapped_column(String(64))     # UUID as string (kept text for cross-resource), or "-"
    purpose: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))