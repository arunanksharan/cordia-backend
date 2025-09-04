import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.intake.service import IntakeService
from app.modules.intake.schemas import (
    IntakeSessionCreate, IntakeSessionOut, IntakeRecordsUpsert, IntakeSummaryUpdate, IntakeSubmit
)

router = APIRouter()

async def get_session():
    async with SessionLocal() as s: yield s

def svc(s: AsyncSession = Depends(get_session)) -> IntakeService:
    return IntakeService(s)

@router.post("/intake/sessions", response_model=IntakeSessionOut, dependencies=[Depends(require_scopes("intake:write"))])
async def create_session(payload: IntakeSessionCreate, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    obj = await service.create_session(principal.org_id, patient_id=payload.patient_id, conversation_id=payload.conversation_id, context=payload.context)
    return obj

@router.get("/intake/sessions/{session_id}", response_model=IntakeSessionOut, dependencies=[Depends(require_scopes("intake:read"))])
async def get_session(session_id: uuid.UUID, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    obj = await service.get_session(principal.org_id, session_id)
    if not obj: raise HTTPException(404, "not_found")
    return obj

@router.get("/intake/sessions", response_model=list[IntakeSessionOut], dependencies=[Depends(require_scopes("intake:read"))])
async def list_sessions(patient_id: uuid.UUID | None = None, conversation_id: uuid.UUID | None = None, status: str | None = None, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    return await service.list_sessions(principal.org_id, patient_id=patient_id, conversation_id=conversation_id, status=status)

@router.put("/intake/sessions/{session_id}/patient/{patient_id}", response_model=IntakeSessionOut, dependencies=[Depends(require_scopes("intake:write"))])
async def set_session_patient(session_id: uuid.UUID, patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    obj, err = await service.set_session_patient(principal.org_id, session_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    if err: raise HTTPException(404, err)
    return obj

@router.put("/intake/sessions/{session_id}/records", dependencies=[Depends(require_scopes("intake:write"))])
async def upsert_records(session_id: uuid.UUID, payload: IntakeRecordsUpsert, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    res, err = await service.upsert_records(principal.org_id, session_id, payload)
    if err == "not_found": raise HTTPException(404, "not_found")
    return res

@router.put("/intake/sessions/{session_id}/summary", dependencies=[Depends(require_scopes("intake:write"))])
async def set_summary(session_id: uuid.UUID, payload: IntakeSummaryUpdate, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    obj, err = await service.set_summary(principal.org_id, session_id, payload.text)
    if err == "not_found": raise HTTPException(404, "not_found")
    return {"id": str(obj.id), "session_id": str(obj.session_id)}

@router.post("/intake/sessions/{session_id}/submit", dependencies=[Depends(require_scopes("intake:write"))])
async def submit(session_id: uuid.UUID, payload: IntakeSubmit, principal: Principal = Depends(get_principal), service: IntakeService = Depends(svc)):
    obj = await service.submit(principal.org_id, session_id)
    if not obj: raise HTTPException(404, "not_found")
    return {"status": obj.status}