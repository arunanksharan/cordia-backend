from fastapi import APIRouter
from app.modules.patients.router import router as patients_router
from app.modules.media.router import router as media_router
from app.modules.conversations.router import router as conversations_router

api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(conversations_router, tags=["conversations"])
# conversations_router already includes /channels, /conversations, etc.

@api_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}