import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.identity.service import IdentityService
from app.modules.identity.schemas import (
    ContactPointCreate, ContactPointOut,
    RelatedPersonCreate, RelatedPersonOut,
    DirectoryCreate, PractitionerOut, LocationOut
)

router = APIRouter()
async def get_session():
    async with SessionLocal() as s: yield s
def svc(s: AsyncSession = Depends(get_session)) -> IdentityService: return IdentityService(s)

@router.post("/identity/contacts", response_model=ContactPointOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_contact(payload: ContactPointCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_contact(principal.org_id, payload)

@router.get("/identity/contacts/{owner_type}/{owner_id}", response_model=list[ContactPointOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_contacts(owner_type: str, owner_id: uuid.UUID, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_contacts(principal.org_id, owner_type, owner_id)

@router.post("/identity/related", response_model=RelatedPersonOut, dependencies=[Depends(require_scopes("patients:write"))])
async def add_related(payload: RelatedPersonCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_related(principal.org_id, payload)

@router.get("/identity/related/{patient_id}", response_model=list[RelatedPersonOut], dependencies=[Depends(require_scopes("patients:read"))])
async def list_related(patient_id: uuid.UUID, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_related(principal.org_id, patient_id)

@router.post("/directory/practitioners", response_model=PractitionerOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def create_practitioner(payload: DirectoryCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_practitioner(principal.org_id, payload)

@router.get("/directory/practitioners", response_model=list[PractitionerOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def list_practitioners(principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_practitioners(principal.org_id)

@router.post("/directory/locations", response_model=LocationOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def create_location(payload: DirectoryCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_location(principal.org_id, payload)

@router.get("/directory/locations", response_model=list[LocationOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def list_locations(principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_locations(principal.org_id)