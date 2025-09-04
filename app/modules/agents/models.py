from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON
from app.core.base import Base, TimestampedTenantMixin

class ToolRun(Base, TimestampedTenantMixin):
    tool: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSON)
    outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    error: Mapped[str | None] = mapped_column(String(400), nullable=True)