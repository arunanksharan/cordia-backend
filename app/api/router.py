from fastapi import APIRouter
from app.modules.patients.router import router as patients_router
from app.modules.media.router import router as media_router
from app.modules.conversations.router import router as conversations_router
from app.modules.tickets.router import router as tickets_router
from app.modules.appointments.router import router as appointments_router
from app.modules.consent.router import router as consent_router
from app.modules.audit.router import router as audit_router



api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(conversations_router, tags=["conversations"])
api_router.include_router(tickets_router, tags=["tickets"])
api_router.include_router(appointments_router, tags=["appointments"])
api_router.include_router(consent_router, tags=["consent"])
api_router.include_router(audit_router, tags=["audit"])

@api_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}