from fastapi import FastAPI
from app.core.config import settings
from app.modules.appointments.router import router as appointments_router

app = FastAPI(title="Debug App")

app.include_router(appointments_router, prefix="/api/v1/appointments")
