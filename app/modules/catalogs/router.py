from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.catalogs.schemas import CodeValueCreate, CodeValueOut
from app.modules.catalogs.repository import CatalogRepository

router = APIRouter()
async def get_session():
    async with SessionLocal() as s: yield s

@router.post("/catalogs/values", response_model=CodeValueOut, dependencies=[Depends(require_scopes("admin:write"))])
async def upsert_value(payload: CodeValueCreate, principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    repo = CatalogRepository(s); obj = await repo.upsert_value(principal.org_id, **payload.model_dump()); await s.commit(); return obj

@router.get("/catalogs/{set_name}", response_model=list[CodeValueOut], dependencies=[Depends(require_scopes("admin:read"))])
async def list_values(set_name: str, principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    return await CatalogRepository(s).list_values(principal.org_id, set_name)