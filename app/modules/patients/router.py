import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.patients.schemas import PatientCreate, PatientUpdate, PatientOut
from app.modules.patients.service import PatientService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> PatientService:
    return PatientService(session)

@router.post("", response_model=PatientOut, dependencies=[Depends(require_scopes("patients:write"))])
async def create_patient(
    payload: PatientCreate,
    principal: Principal = Depends(get_principal),
    service: PatientService = Depends(svc),
):
    obj = await service.create(principal.org_id, payload)
    return obj

@router.get("/{patient_id}", response_model=PatientOut, dependencies=[Depends(require_scopes("patients:read"))])
async def get_patient(
    patient_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: PatientService = Depends(svc),
):
    obj = await service.get(principal.org_id, patient_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return obj

@router.get("", response_model=list[PatientOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_patients(
    limit: int = 50, offset: int = 0,
    principal: Principal = Depends(get_principal),
    service: PatientService = Depends(svc),
):
    return await service.list(principal.org_id, limit, offset)

@router.patch("/{patient_id}", response_model=PatientOut, dependencies=[Depends(require_scopes("patients:write"))])
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    principal: Principal = Depends(get_principal),
    service: PatientService = Depends(svc),
):
    obj = await service.update(principal.org_id, patient_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Patient not found")
    return obj

@router.delete("/{patient_id}", status_code=204, dependencies=[Depends(require_scopes("patients:write"))])
async def delete_patient(
    patient_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: PatientService = Depends(svc),
):
    ok = await service.delete(principal.org_id, patient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Patient not found")
    return