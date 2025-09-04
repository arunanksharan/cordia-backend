import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, Principal, require_scopes
from app.modules.consent.schemas import ConsentCreate, ConsentOut, ConsentRevoke
from app.modules.consent.service import ConsentService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> ConsentService:
    return ConsentService(session)

@router.post("/consents", response_model=ConsentOut, dependencies=[Depends(require_scopes("consent:write"))])
async def create_consent(
    payload: ConsentCreate,
    principal: Principal = Depends(get_principal),
    service: ConsentService = Depends(svc),
):
    return await service.create(principal.org_id, payload)

@router.get("/patients/{patient_id}/consents", response_model=list[ConsentOut], dependencies=[Depends(require_scopes("consent:read"))])
async def list_consents(
    patient_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: ConsentService = Depends(svc),
):
    return await service.list_for_patient(principal.org_id, patient_id)

@router.post("/consents/{consent_id}/revoke", response_model=ConsentOut, dependencies=[Depends(require_scopes("consent:write"))])
async def revoke_consent(
    consent_id: uuid.UUID,
    payload: ConsentRevoke,
    principal: Principal = Depends(get_principal),
    service: ConsentService = Depends(svc),
):
    obj = await service.revoke(principal.org_id, consent_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Consent not found")
    return obj