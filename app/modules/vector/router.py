from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, Principal, require_scopes
from app.modules.vector.service import VectorService
from app.modules.vector.schemas import (
    IngestTranscriptsByConversation, IngestMessageTranscript, IngestTicketNotes, IngestKnowledge,
    SearchQuery, ChunkOut
)

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> VectorService:
    return VectorService(session)

# ---- Ingest ----
@router.post("/search/ingest/conversation")
async def ingest_conversation(
    payload: IngestTranscriptsByConversation,
    principal: Principal = Depends(get_principal),
    service: VectorService = Depends(svc),
):
    return await service.ingest_conversation(principal.org_id, payload)

@router.post("/search/ingest/message")
async def ingest_message(
    payload: IngestMessageTranscript,
    principal: Principal = Depends(get_principal),
    service: VectorService = Depends(svc),
):
    return await service.ingest_message(principal.org_id, payload)

@router.post("/search/ingest/ticket")
async def ingest_ticket_notes(
    payload: IngestTicketNotes,
    principal: Principal = Depends(get_principal),
    service: VectorService = Depends(svc),
):
    return await service.ingest_ticket(principal.org_id, payload)

@router.post("/search/ingest/knowledge")
async def ingest_knowledge(
    payload: IngestKnowledge,
    principal: Principal = Depends(get_principal),
    service: VectorService = Depends(svc),
):
    return await service.ingest_knowledge(principal.org_id, payload)

# ---- Search ----
@router.post("/search", response_model=list[ChunkOut], dependencies=[Depends(require_scopes("search:read"))])
async def search(
    payload: SearchQuery,
    principal: Principal = Depends(get_principal),
    service: VectorService = Depends(svc),
):
    return await service.search(principal.org_id, payload)