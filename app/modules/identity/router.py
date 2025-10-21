import uuid
from fastapi import APIRouter, Depends
from app.core.db import get_session
from app.core.security import get_principal, Principal, require_scopes
from app.modules.identity.service import IdentityService
from app.modules.identity.schemas import (
    ContactPointCreate, ContactPointOut,
    RelatedPersonCreate, RelatedPersonOut,
    DirectoryCreate, IdentityProviderOut, IdentityLocationOut
)

router = APIRouter()

def svc(s = Depends(get_session)) -> IdentityService: return IdentityService(s)

@router.post("/contact_points", response_model=ContactPointOut, dependencies=[Depends(require_scopes("patient:write"))])
async def create_contact_point(payload: ContactPointCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_contact_point(principal.org_id, payload)

@router.post("/related_persons", response_model=RelatedPersonOut, dependencies=[Depends(require_scopes("patient:write"))])
async def create_related_person(payload: RelatedPersonCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_related_person(principal.org_id, payload)

@router.post("/directory/identity-providers", response_model=IdentityProviderOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def create_identity_provider(payload: DirectoryCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_practitioner(principal.org_id, payload)

@router.get("/directory/identity-providers", response_model=list[IdentityProviderOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def list_identity_providers(principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_practitioners(principal.org_id)

@router.post("/directory/identity-locations", response_model=IdentityLocationOut, dependencies=[Depends(require_scopes("appointments:write"))])
async def create_identity_location(payload: DirectoryCreate, principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.add_location(principal.org_id, payload)

@router.get("/directory/identity-locations", response_model=list[IdentityLocationOut], dependencies=[Depends(require_scopes("appointments:read"))])
async def list_identity_locations(principal: Principal = Depends(get_principal), service: IdentityService = Depends(svc)):
    return await service.list_locations(principal.org_id)