from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from pydantic import BaseModel
from app.modules.webhooks.repository import WebhookRepository

router = APIRouter()
async def get_session(): 
    async with SessionLocal() as s: 
        yield s

class WebhookCreate(BaseModel):
    endpoint_url: str
    secret: str | None = None
    filters: dict | None = None
class WebhookOut(WebhookCreate):
    id: str
    org_id: str
    class Config: from_attributes = True

@router.post("/webhooks", response_model=WebhookOut, dependencies=[Depends(require_scopes("admin:write"))])
async def create_webhook(payload: WebhookCreate, principal: Principal = Depends(get_principal), s: AsyncSession = Depends(get_session)):
    repo = WebhookRepository(s); obj = await repo.create(principal.org_id, **payload.model_dump()); await s.commit(); return obj