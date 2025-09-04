from fastapi import APIRouter
from app.modules.patients.router import router as patients_router
from app.modules.media.router import router as media_router
from app.modules.conversations.router import router as conversations_router
from app.modules.tickets.router import router as tickets_router
from app.modules.appointments.router import router as appointments_router
from app.modules.consent.router import router as consent_router
from app.modules.audit.router import router as audit_router
from app.modules.vector.router import router as vector_router
from app.modules.fhir.router import router as fhir_router
from app.modules.identity.router import router as identity_router
from app.modules.catalogs.router import router as catalogs_router
from app.modules.notifications.router import router as notifications_router
from app.modules.exports.router import router as exports_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.realtime.router import router as realtime_router
from app.modules.reports.router import router as reports_router
from app.modules.agents.router import router as agents_router
from app.modules.intake.router import router as intake_router
from app.modules.availability.router import router as availability_router
from app.modules.patient_context.router import router as patient_context_router




api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(conversations_router, tags=["conversations"])
api_router.include_router(tickets_router, tags=["tickets"])
api_router.include_router(appointments_router, tags=["appointments"])
api_router.include_router(consent_router, tags=["consent"])
api_router.include_router(audit_router, tags=["audit"])
api_router.include_router(vector_router, tags=["search"])
api_router.include_router(fhir_router, tags=["fhir"])
api_router.include_router(identity_router, tags=["identity"])
api_router.include_router(catalogs_router, tags=["catalogs"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(exports_router, tags=["exports"])
api_router.include_router(webhooks_router, tags=["webhooks"])
api_router.include_router(realtime_router, tags=["realtime"])
api_router.include_router(reports_router, tags=["reports"])
api_router.include_router(agents_router, tags=["agents"])
api_router.include_router(intake_router, tags=["intake"])
api_router.include_router(availability_router, tags=["availability"])
api_router.include_router(patient_context_router, tags=["patient_context"])

@api_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}