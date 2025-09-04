import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.patient_context.service import PatientContextService
from app.modules.patient_context.schemas import (
    ProfileUpsert, ProfileOut,
    IdentifierCreate, IdentifierOut,
    AddressCreate, AddressOut,
    CoverageCreate, CoverageOut,
    TagCreate, TagOut,
    SdohUpsert, SdohOut,
    ExternalLinkCreate, ExternalLinkOut
)

router = APIRouter()
async def get_session():
    async with SessionLocal() as s: yield s
def svc(s: AsyncSession = Depends(get_session)) -> PatientContextService: return PatientContextService(s)

# Profile
@router.put("/patients/profile", response_model=ProfileOut, dependencies=[Depends(require_scopes("patients:write"))])
async def upsert_profile(payload: ProfileUpsert, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.upsert_profile(principal.org_id, payload.model_dump(exclude_unset=True))
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/profile", response_model=ProfileOut, dependencies=[Depends(require_scopes("patients:read"))])
async def get_profile(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.get_profile(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    if not obj: raise HTTPException(404, "not_found")
    return obj

# Identifiers
@router.post("/patients/identifiers", response_model=IdentifierOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_identifier(payload: IdentifierCreate, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.add_identifier(principal.org_id, payload.model_dump())
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/identifiers", response_model=list[IdentifierOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_identifiers(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    objs, err = await service.list_identifiers(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return objs

# Addresses
@router.post("/patients/addresses", response_model=AddressOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_address(payload: AddressCreate, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.add_address(principal.org_id, payload.model_dump())
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/addresses", response_model=list[AddressOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_addresses(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    objs, err = await service.list_addresses(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return objs

# Coverage
@router.post("/patients/coverages", response_model=CoverageOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_coverage(payload: CoverageCreate, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.add_coverage(principal.org_id, payload.model_dump())
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/coverages", response_model=list[CoverageOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_coverages(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    objs, err = await service.list_coverages(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return objs

# Tags
@router.post("/patients/tags", response_model=TagOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_tag(payload: TagCreate, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.add_tag(principal.org_id, payload.model_dump())
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/tags", response_model=list[TagOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_tags(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    objs, err = await service.list_tags(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return objs

# SDOH
@router.put("/patients/{patient_id}/sdoh", response_model=SdohOut, dependencies=[Depends(require_scopes("patients:write"))])
async def upsert_sdoh(patient_id: uuid.UUID, payload: SdohUpsert, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    if payload.patient_id != patient_id:
        raise HTTPException(400, "patient_id mismatch")
    obj, err = await service.upsert_sdoh(principal.org_id, patient_id, payload.data)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    return obj

@router.get("/patients/{patient_id}/sdoh", response_model=SdohOut, dependencies=[Depends(require_scopes("patients:read"))])
async def get_sdoh(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, err = await service.get_sdoh(principal.org_id, patient_id)
    if err == "consent_required": raise HTTPException(403, "consent_required")
    if not obj: raise HTTPException(404, "not_found")
    return obj

# External links
@router.post("/patients/external-links", response_model=ExternalLinkOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_external_link(payload: ExternalLinkCreate, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    obj, _ = await service.add_external_link(principal.org_id, payload.model_dump())
    return obj

@router.get("/patients/{patient_id}/external-links", response_model=list[ExternalLinkOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_external_links(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: PatientContextService = Depends(svc)):
    objs, _ = await service.list_external_links(principal.org_id, patient_id)
    return objs