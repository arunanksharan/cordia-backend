from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.notifications.schemas import TemplateCreate, TemplateOut, SendMessage, OutboundOut
from app.modules.notifications.service import NotificationsService

router = APIRouter()
async def get_session():
    async with SessionLocal() as s: yield s
def svc(s: AsyncSession = Depends(get_session)) -> NotificationsService: return NotificationsService(s)

@router.post("/notifications/templates", response_model=TemplateOut, dependencies=[Depends(require_scopes("notify:write"))])
async def create_template(payload: TemplateCreate, principal: Principal = Depends(get_principal), service: NotificationsService = Depends(svc)):
    return await service.create_template(principal.org_id, **payload.model_dump())

@router.post("/notifications/send", response_model=OutboundOut, dependencies=[Depends(require_scopes("notify:write"))])
async def send_message(payload: SendMessage, principal: Principal = Depends(get_principal), service: NotificationsService = Depends(svc)):
    try:
        if payload.template_name:
            return await service.send_with_template(principal.org_id, channel=payload.channel, to=payload.to, template_name=payload.template_name, variables=payload.variables or {})
        elif payload.body:
            return await service.send(principal.org_id, channel=payload.channel, to=payload.to, subject=payload.subject, body=payload.body, variables=payload.variables or {})
        else:
            raise HTTPException(400, "Provide template_name or body")
    except ValueError as e:
        if str(e) == "template_not_found":
            raise HTTPException(404, "Template not found")
        raise