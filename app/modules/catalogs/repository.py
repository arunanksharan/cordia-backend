import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.catalogs.models import CodeSet, CodeValue

class CatalogRepository:
    def __init__(self, s: AsyncSession): self.s = s
    async def upsert_value(self, org: uuid.UUID, *, set_name: str, code: str, display: str, active: bool=True) -> CodeValue:
        res = await self.s.execute(select(CodeValue).where(CodeValue.org_id==org, CodeValue.set_name==set_name, CodeValue.code==code, CodeValue.deleted_at.is_(None)))
        row = res.scalar_one_or_none()
        if row:
            row.display = display; row.active = active
            await self.s.flush(); return row
        obj = CodeValue(org_id=org, set_name=set_name, code=code, display=display, active=active)
        self.s.add(obj); await self.s.flush(); return obj
    async def list_values(self, org: uuid.UUID, set_name: str) -> Sequence[CodeValue]:
        r = await self.s.execute(select(CodeValue).where(CodeValue.org_id==org, CodeValue.set_name==set_name, CodeValue.active.is_(True), CodeValue.deleted_at.is_(None)))
        return r.scalars().all()