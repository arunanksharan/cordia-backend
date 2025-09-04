import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.admin.models import Team, TeamMember, RoutingRule

class AdminRepository:
    def __init__(self, s: AsyncSession): self.s = s
    async def add_team(self, org: uuid.UUID, name: str) -> Team:
        t = Team(org_id=org, name=name); self.s.add(t); await self.s.flush(); return t
    async def add_member(self, org: uuid.UUID, team_id: uuid.UUID, user_id: uuid.UUID) -> TeamMember:
        m = TeamMember(org_id=org, team_id=team_id, user_id=user_id); self.s.add(m); await self.s.flush(); return m
    async def add_rule(self, org: uuid.UUID, match: dict, queue_name: str) -> RoutingRule:
        r = RoutingRule(org_id=org, match=match, queue_name=queue_name); self.s.add(r); await self.s.flush(); return r
    async def list_rules(self, org: uuid.UUID) -> Sequence[RoutingRule]:
        res = await self.s.execute(select(RoutingRule).where(RoutingRule.org_id==org, RoutingRule.deleted_at.is_(None))); return res.scalars().all()