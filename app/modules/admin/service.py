import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.admin.repository import AdminRepository

class AdminService:
    def __init__(self, s: AsyncSession):
        self.s = s; self.repo = AdminRepository(s)
    async def create_team(self, org: uuid.UUID, name: str):
        t = await self.repo.add_team(org, name); await self.s.commit(); return t
    async def add_member(self, org: uuid.UUID, team_id: uuid.UUID, user_id: uuid.UUID):
        m = await self.repo.add_member(org, team_id, user_id); await self.s.commit(); return m
    async def add_rule(self, org: uuid.UUID, match: dict, queue_name: str):
        r = await self.repo.add_rule(org, match, queue_name); await self.s.commit(); return r
    async def rules(self, org: uuid.UUID): return await self.repo.list_rules(org)