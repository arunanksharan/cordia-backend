import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, ForeignKey
from app.core.base import Base, TimestampedTenantMixin

class Team(Base, TimestampedTenantMixin):
    name: Mapped[str] = mapped_column(String(64))

class TeamMember(Base, TimestampedTenantMixin):
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id"))
    user_id: Mapped[uuid.UUID] = mapped_column()

class RoutingRule(Base, TimestampedTenantMixin):
    # simple rule: if ticket.category == X and ticket.priority == Y -> workqueue.name
    match: Mapped[dict] = mapped_column(JSON)   # {"category":"billing","priority":"p1"}
    queue_name: Mapped[str] = mapped_column(String(64))