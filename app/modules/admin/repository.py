import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.admin.models import Team, TeamMember, RoutingRule

class AdminRepository:
    def __init__(self, session: AsyncSession): self.session = session
    async def add_team(self, org: uuid.UUID, name: str) -> Team:
        t = Team(org_id=org, name=name); self.session.add(t); await self.session.flush(); return t
    async def add_member(self, org: uuid.UUID, team_id: uuid.UUID, user_id: uuid.UUID) -> TeamMember:
        m = TeamMember(org_id=org, team_id=team_id, user_id=user_id); self.session.add(m); await self.session.flush(); return m
    async def add_rule(self, org: uuid.UUID, match: dict, queue_name: str) -> RoutingRule:
        r = RoutingRule(org_id=org, match=match, queue_name=queue_name); self.session.add(r); await self.session.flush(); return r
    async def list_rules(self, org: uuid.UUID) -> Sequence[RoutingRule]:
        res = await self.session.execute(select(RoutingRule).where(RoutingRule.org_id==org, RoutingRule.deleted_at.is_(None))); return res.scalars().all()