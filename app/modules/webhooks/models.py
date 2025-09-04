from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, Boolean
from app.core.base import Base, TimestampedTenantMixin

class WebhookSubscription(Base, TimestampedTenantMixin):
    endpoint_url: Mapped[str] = mapped_column(String(300))
    secret: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # e.g., {"event_types":["TICKET_*"]}