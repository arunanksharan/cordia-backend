from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.admin.service import AdminService

router = APIRouter()
async def get_session(): 
    async with SessionLocal() as s: yield s
def svc(s: AsyncSession = Depends(get_session)) -> AdminService: return AdminService(s)

class TeamCreate(BaseModel): name: str
class MemberCreate(BaseModel): team_id: str; user_id: str
class RuleCreate(BaseModel): match: dict; queue_name: str

@router.post("/admin/teams", dependencies=[Depends(require_scopes("admin:write"))])
async def create_team(payload: TeamCreate, principal: Principal = Depends(get_principal), service: AdminService = Depends(svc)):
    return await service.create_team(principal.org_id, payload.name)

@router.post("/admin/teams/members", dependencies=[Depends(require_scopes("admin:write"))])
async def add_member(payload: MemberCreate, principal: Principal = Depends(get_principal), service: AdminService = Depends(svc)):
    return await service.add_member(principal.org_id, payload.team_id, payload.user_id)

@router.post("/admin/routing/rules", dependencies=[Depends(require_scopes("admin:write"))])
async def add_rule(payload: RuleCreate, principal: Principal = Depends(get_principal), service: AdminService = Depends(svc)):
    return await service.add_rule(principal.org_id, payload.match, payload.queue_name)

@router.get("/admin/routing/rules", dependencies=[Depends(require_scopes("admin:read"))])
async def list_rules(principal: Principal = Depends(get_principal), service: AdminService = Depends(svc)):
    return await service.rules(principal.org_id)