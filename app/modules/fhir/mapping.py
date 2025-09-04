from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

# Internal models (imports are local to avoid circulars)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.patients.models import Patient as DbPatient
from app.modules.appointments.models import Appointment as DbAppointment
from app.modules.conversations.models import Message as DbMessage, Conversation as DbConversation
from app.modules.media.models import MediaAsset as DbMedia
from app.modules.consent.models import Consent as DbConsent

# -------------------- helpers --------------------
def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None

def _uuid(v: str | uuid.UUID | None) -> str | None:
    return str(v) if v else None

# -------------------- Patient --------------------
def patient_to_fhir(p: DbPatient) -> dict[str, Any]:
    names = []
    if p.legal_name:
        # naive split: first token -> given, last -> family
        parts = p.legal_name.split()
        given = parts[:-1] or parts
        family = parts[-1] if len(parts) > 1 else parts[0]
        names = [{"use":"official","given":given,"family":family,"text":p.legal_name}]
    telecom = []
    if p.primary_phone: telecom.append({"system":"phone","value":p.primary_phone,"use":"mobile"})
    if getattr(p, "primary_email", None): telecom.append({"system":"email","value":p.primary_email})
    return {
        "resourceType": "Patient",
        "id": str(p.id),
        "active": True,
        "name": names or [{"text": p.legal_name}],
        "telecom": telecom,
        "gender": getattr(p, "gender", None) or "unknown",
        "meta": {"lastUpdated": _iso(p.updated_at) or _iso(p.created_at)},
        "extension": [
            {"url":"urn:prm:org","valueString": str(p.org_id)}
        ]
    }

def fhir_to_patient_payload(doc: dict[str, Any]) -> dict[str, Any]:
    # map minimal subset to our PatientCreate/Update
    legal_name = None
    if "name" in doc and doc["name"]:
        nm = doc["name"][0]
        legal_name = nm.get("text") or " ".join(nm.get("given", []) + ([nm.get("family")] if nm.get("family") else [])) or None
    phones = [t for t in doc.get("telecom", []) if t.get("system") == "phone"]
    emails = [t for t in doc.get("telecom", []) if t.get("system") == "email"]
    return {
        "legal_name": legal_name,
        "primary_phone": phones[0]["value"] if phones else None,
        "primary_email": emails[0]["value"] if emails else None,
    }

# -------------------- Appointment --------------------
def appointment_to_fhir(a: DbAppointment) -> dict[str, Any]:
    participants = []
    if a.patient_id:
        participants.append({"actor": {"reference": f"Patient/{a.patient_id}"}, "status": "accepted"})
    if a.practitioner_name:
        participants.append({"actor": {"display": a.practitioner_name}, "status":"accepted"})
    return {
        "resourceType": "Appointment",
        "id": str(a.id),
        "status": {
            "requested":"proposed",
            "pending_confirm":"proposed",
            "confirmed":"booked",
            "rescheduled":"proposed",
            "canceled":"cancelled",
            "no_show":"noshow",
            "completed":"fulfilled",
        }.get(a.status, "proposed"),
        "description": a.reason_code or None,
        "start": _iso(a.confirmed_start or a.requested_start),
        "end": _iso(a.confirmed_end or a.requested_end),
        "participant": participants,
        "serviceType": [{"text": a.reason_code}] if a.reason_code else None,
        "slot": None,
        "comment": (a.meta or {}).get("note"),
        "extension": [
            {"url":"urn:prm:location","valueString": a.location_name},
            {"url":"urn:prm:origin","valueString": a.channel_origin},
        ],
        "meta":{"lastUpdated": _iso(a.updated_at) or _iso(a.created_at)}
    }

def fhir_to_appointment_payload(doc: dict[str, Any]) -> dict[str, Any]:
    start = doc.get("start"); end = doc.get("end")
    desc = doc.get("description")
    # get patient from participants if present
    pat = None
    for pr in doc.get("participant", []):
        ref = pr.get("actor", {}).get("reference")
        if ref and ref.startswith("Patient/"):
            pat = ref.split("/",1)[1]
            break
    location = None
    origin = None
    for ext in doc.get("extension", []):
        if ext.get("url") == "urn:prm:location": location = ext.get("valueString")
        if ext.get("url") == "urn:prm:origin": origin = ext.get("valueString")
    return {
        "patient_id": uuid.UUID(pat) if pat else None,
        "reason_code": desc,
        "channel_origin": origin,
        "requested_start": datetime.fromisoformat(start) if start else None,
        "requested_end": datetime.fromisoformat(end) if end else None,
        "location_name": location,
        "practitioner_name": None,
        "meta": {},
    }

# -------------------- Communication (Message) --------------------
def message_to_fhir(m: DbMessage, conversation_patient_id: uuid.UUID | None) -> dict[str, Any]:
    payload = []
    if m.content_type == "text" and m.text_body:
        payload.append({"contentString": m.text_body})
    elif m.content_type == "media" and m.media_id:
        payload.append({"contentAttachment":{"url": f"/api/v1/messages/{m.id}/media/download_url", "title":"attachment"}})

    subject_ref = f"Patient/{conversation_patient_id}" if conversation_patient_id else None
    return {
        "resourceType": "Communication",
        "id": str(m.id),
        "status": "completed",
        "category": [{"text": m.actor_type}],
        "language": m.locale or "en",
        "subject": {"reference": subject_ref} if subject_ref else None,
        "sent": _iso(m.created_at),
        "payload": payload or None,
        "extension":[{"url":"urn:prm:direction","valueString": m.direction}]
    }

# -------------------- DocumentReference (Media) --------------------
def media_to_fhir(media: DbMedia) -> dict[str, Any]:
    return {
        "resourceType": "DocumentReference",
        "id": str(media.id),
        "status": "current",
        "type": {"text": media.mime_type},
        "content": [{
            "attachment":{
                "contentType": media.mime_type,
                "url": f"/api/v1/media/{media.id}/download",
                "size": media.size_bytes
            }
        }],
        "meta":{"lastUpdated": _iso(media.updated_at) or _iso(media.created_at)}
    }

# -------------------- Consent --------------------
def consent_to_fhir(c: DbConsent) -> dict[str, Any]:
    # Scope to FHIR category/policy
    category = [{"coding":[{"system":"urn:prm:scope","code":c.scope}]}]
    return {
        "resourceType":"Consent",
        "id": str(c.id),
        "status": "active" if c.active and not c.revoked_at else "inactive",
        "patient": {"reference": f"Patient/{c.patient_id}"},
        "dateTime": _iso(c.effective_at),
        "scope":{"text": c.scope},
        "category": category,
        "provision": {
            "type":"permit",
            "period": {
                "start": _iso(c.effective_at),
                "end": _iso(c.expires_at)
            }
        },
        "meta":{"lastUpdated": _iso(c.updated_at) or _iso(c.created_at)}
    }