import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.conversations.schemas import (
    ChannelCreate, ChannelOut,
    ConversationCreate, ConversationOut,
    MessageCreate, MessageOut,
    TranscriptCreate, TranscriptOut
)
from app.modules.conversations.service import ConversationService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> ConversationService:
    return ConversationService(session)

# Channels
@router.post("/channels", response_model=ChannelOut, dependencies=[Depends(require_scopes("channels:write"))])
async def create_channel(
    payload: ChannelCreate,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    obj = await service.create_channel(principal.org_id, payload)
    return obj

@router.get("/channels", response_model=list[ChannelOut], dependencies=[Depends(require_scopes("channels:read"))])
async def list_channels(
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    return await service.list_channels(principal.org_id)

# Conversations
@router.post("/conversations", response_model=ConversationOut, dependencies=[Depends(require_scopes("conversations:write"))])
async def create_conversation(
    payload: ConversationCreate,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    obj = await service.create_conversation(principal.org_id, payload)
    return obj

@router.get("/conversations/{conversation_id}", response_model=ConversationOut, dependencies=[Depends(require_scopes("conversations:read"))])
async def get_conversation(
    conversation_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    obj = await service.get_conversation(principal.org_id, conversation_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return obj

# Messages
@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, dependencies=[Depends(require_scopes("messages:write"))])
async def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    obj, err = await service.create_message(principal.org_id, conversation_id, payload)
    if err == "conversation_not_found":
        raise HTTPException(status_code=404, detail="Conversation not found")
    if err == "media_required":
        raise HTTPException(status_code=400, detail="media_id required for content_type=media")
    if err == "media_not_found":
        raise HTTPException(status_code=404, detail="Media not found")
    return obj

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut], dependencies=[Depends(require_scopes("messages:read"))])
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = 50, offset: int = 0,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    return await service.list_messages(principal.org_id, conversation_id, limit, offset)

# Transcripts
@router.post("/transcripts", response_model=TranscriptOut, dependencies=[Depends(require_scopes("transcripts:write"))])
async def create_transcript(
    payload: TranscriptCreate,
    principal: Principal = Depends(get_principal),
    service: ConversationService = Depends(svc),
):
    obj, err = await service.create_transcript(principal.org_id, payload)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return obj