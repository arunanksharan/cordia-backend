from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal

# domain repos/services
from app.modules.patients.repository import PatientRepository
from app.modules.patients.service import PatientService
from app.modules.appointments.service import AppointmentService
from app.modules.appointments.repository import AppointmentRepository
from app.modules.conversations.repository import MessageRepository, ConversationRepository
from app.modules.media.repository import MediaRepository
from app.modules.consent.service import ConsentService
from app.modules.fhir.mapping import (
    patient_to_fhir, fhir_to_patient_payload,
    appointment_to_fhir, fhir_to_appointment_payload,
    message_to_fhir, media_to_fhir, consent_to_fhir
)

router = APIRouter()

async def get_session():
    async with SessionLocal() as s:
        yield s

# ------------- Patient -------------
@router.get("/fhir/Patient/{id}", dependencies=[Depends(require_scopes("patients:read"))])
async def fhir_get_patient(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    p = await PatientRepository(session).get(principal.org_id, id)
    if not p: raise HTTPException(404, "Not found")
    return patient_to_fhir(p)

@router.get("/fhir/Patient", dependencies=[Depends(require_scopes("patients:read"))])
async def fhir_search_patient(name: str | None = None, phone: str | None = None, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    # very simple search (name/phone)
    repo = PatientRepository(session)
    pts = await repo.search(principal.org_id, name=name, phone=phone, limit=50, offset=0)  # assumes you implemented earlier; else fallback to list()
    return {"resourceType":"Bundle","type":"searchset","entry":[{"resource": patient_to_fhir(p)} for p in pts]}

@router.post("/fhir/Patient", dependencies=[Depends(require_scopes("patients:write"))], status_code=201)
async def fhir_create_patient(doc: dict, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    payload = fhir_to_patient_payload(doc)
    obj = await PatientService(session).create(principal.org_id, payload)  # our service accepts dict via model_dump
    return patient_to_fhir(obj)

@router.put("/fhir/Patient/{id}", dependencies=[Depends(require_scopes("patients:write"))])
async def fhir_update_patient(id: uuid.UUID, doc: dict, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    repo = PatientRepository(session)
    p = await repo.get(principal.org_id, id)
    if not p: raise HTTPException(404, "Not found")
    payload = fhir_to_patient_payload(doc)
    # use repo/service update if available
    p = await repo.update_fields(principal.org_id, id, **{k:v for k,v in payload.items() if v is not None})
    await session.commit()
    return patient_to_fhir(p)

@router.delete("/fhir/Patient/{id}", dependencies=[Depends(require_scopes("patients:write"))], status_code=204)
async def fhir_delete_patient(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    repo = PatientRepository(session)
    p = await repo.get(principal.org_id, id)
    if not p: raise HTTPException(404, "Not found")
    p.deleted_at = p.deleted_at or p.created_at  # soft delete
    await session.commit()
    return None

# ------------- Appointment -------------
@router.get("/fhir/Appointment/{id}", dependencies=[Depends(require_scopes("appointments:read"))])
async def fhir_get_appt(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    repo = AppointmentRepository(session)
    a = await repo.get(principal.org_id, id)
    if not a: raise HTTPException(404, "Not found")
    return appointment_to_fhir(a)

@router.get("/fhir/Appointment", dependencies=[Depends(require_scopes("appointments:read"))])
async def fhir_search_appt(patient: str | None = None, status: str | None = None, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    repo = AppointmentRepository(session)
    pid = uuid.UUID(patient) if patient else None
    appts = await repo.list(principal.org_id, status=status, patient_id=pid, limit=50, offset=0)
    return {"resourceType":"Bundle","type":"searchset","entry":[{"resource": appointment_to_fhir(a)} for a in appts]}

@router.post("/fhir/Appointment", dependencies=[Depends(require_scopes("appointments:write"))], status_code=201)
async def fhir_create_appt(doc: dict, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    payload = fhir_to_appointment_payload(doc)
    a = await AppointmentService(session).request(principal.org_id, payload)
    return appointment_to_fhir(a)

@router.put("/fhir/Appointment/{id}", dependencies=[Depends(require_scopes("appointments:write"))])
async def fhir_update_appt(id: uuid.UUID, doc: dict, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    svc = AppointmentService(session)
    # FHIR "booked" maps to confirmed; allow updating description/period or status
    payload = fhir_to_appointment_payload(doc)
    a = await svc.update_fields(principal.org_id, id, payload)
    if not a: raise HTTPException(404, "Not found or not updatable")
    return appointment_to_fhir(a)

@router.delete("/fhir/Appointment/{id}", dependencies=[Depends(require_scopes("appointments:write"))], status_code=204)
async def fhir_delete_appt(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    repo = AppointmentRepository(session)
    a = await repo.get(principal.org_id, id)
    if not a: raise HTTPException(404, "Not found")
    a.deleted_at = a.deleted_at or a.created_at
    await session.commit()
    return None

# ------------- Communication (Message) -------------
@router.get("/fhir/Communication/{id}", dependencies=[Depends(require_scopes("messages:read"))])
async def fhir_get_comm(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    m = await session.execute(select(DbMessage := __import__("app.modules.conversations.models", fromlist=["Message"]).Message).where(DbMessage.id==id, DbMessage.org_id==principal.org_id, DbMessage.deleted_at.is_(None)))
    msg = m.scalar_one_or_none()
    if not msg: raise HTTPException(404, "Not found")
    # find patient via conversation
    conv = await ConversationRepository(session).get(principal.org_id, msg.conversation_id)
    return message_to_fhir(msg, conv.patient_id if conv else None)

@router.delete("/fhir/Communication/{id}", dependencies=[Depends(require_scopes("messages:write"))], status_code=204)
async def fhir_delete_comm(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    # Soft delete message
    repo = MessageRepository(session)
    m = await repo.get(principal.org_id, id) if hasattr(repo, "get") else None
    if not m:
        # fallback select
        res = await session.execute(select(DbMessage).where(DbMessage.id==id, DbMessage.org_id==principal.org_id, DbMessage.deleted_at.is_(None)))
        m = res.scalar_one_or_none()
    if not m: raise HTTPException(404, "Not found")
    m.deleted_at = m.deleted_at or m.created_at
    await session.commit()
    return None

# ------------- DocumentReference (Media) -------------
@router.get("/fhir/DocumentReference/{id}", dependencies=[Depends(require_scopes("media:read"))])
async def fhir_get_docref(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    media = await MediaRepository(session).get(principal.org_id, id)
    if not media: raise HTTPException(404, "Not found")
    return media_to_fhir(media)

@router.delete("/fhir/DocumentReference/{id}", dependencies=[Depends(require_scopes("media:write"))], status_code=204)
async def fhir_delete_docref(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    media = await MediaRepository(session).get(principal.org_id, id)
    if not media: raise HTTPException(404, "Not found")
    media.deleted_at = media.deleted_at or media.created_at
    await session.commit()
    return None

# ------------- Consent -------------
@router.get("/fhir/Consent/{id}", dependencies=[Depends(require_scopes("consent:read"))])
async def fhir_get_consent(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    svc = ConsentService(session)
    # direct fetch by id:
    res = await session.execute(select(DbConsent := __import__("app.modules.consent.models", fromlist=["Consent"]).Consent).where(DbConsent.id==id, DbConsent.org_id==principal.org_id, DbConsent.deleted_at.is_(None)))
    c = res.scalar_one_or_none()
    if not c: raise HTTPException(404, "Not found")
    return consent_to_fhir(c)

@router.post("/fhir/Consent", dependencies=[Depends(require_scopes("consent:write"))], status_code=201)
async def fhir_create_consent(doc: dict, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    # expect {patient -> Patient/{id}, category/scope text}
    pat_ref = (doc.get("patient") or {}).get("reference")
    if not pat_ref or not pat_ref.startswith("Patient/"):
        raise HTTPException(400, "patient.reference required")
    patient_id = uuid.UUID(pat_ref.split("/",1)[1])
    scope = (doc.get("scope") or {}).get("text") or "data_processing"
    c = await ConsentService(session).create(principal.org_id, type("X",(object,),{"model_dump":lambda s,exclude_unset=True: {"patient_id": patient_id, "scope": scope}})())  # small shim
    return consent_to_fhir(c)

@router.delete("/fhir/Consent/{id}", dependencies=[Depends(require_scopes("consent:write"))], status_code=204)
async def fhir_delete_consent(id: uuid.UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(DbConsent).where(DbConsent.id==id, DbConsent.org_id==principal.org_id, DbConsent.deleted_at.is_(None)))
    c = res.scalar_one_or_none()
    if not c: raise HTTPException(404, "Not found")
    c.deleted_at = c.deleted_at or c.created_at
    await session.commit()
    return None