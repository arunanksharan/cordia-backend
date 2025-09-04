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
from fastapi import Request
from app.modules.media.repository import MediaRepository
from app.platform.provider_registry import registry
from app.modules.consent.service import ConsentService
from app.modules.conversations.models import Message, Conversation
from sqlalchemy import select
from app.modules.audit.service import AuditService

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

@router.get("/messages/{message_id}/media/download_url", dependencies=[Depends(require_scopes("media:read"))])
async def get_message_media_download_url(
    message_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
):
    # Resolve message -> media -> conversation -> patient
    res = await session.execute(select(Message).where(
        Message.id == message_id,
        Message.org_id == principal.org_id,
        Message.deleted_at.is_(None),
    ))
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if not msg.media_id:
        raise HTTPException(status_code=400, detail="Message has no media attachment")

    res2 = await session.execute(select(Conversation).where(
        Conversation.id == msg.conversation_id,
        Conversation.org_id == principal.org_id,
        Conversation.deleted_at.is_(None),
    ))
    convo = res2.scalar_one_or_none()
    patient_id = convo.patient_id if convo else None

    # If linked to a patient, enforce consent
    if patient_id:
        consent = ConsentService(session)
        # Choose scope: audio/video => 'recording' else 'data_processing'
        # We need mime_type; load the media row
        media_repo = MediaRepository(session)
        media = await media_repo.get(principal.org_id, msg.media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        scope = "recording" if (media.mime_type or "").startswith(("audio", "video")) else "data_processing"
        allowed = await consent.is_allowed(principal.org_id, patient_id, scope)
        if not allowed:
            # Audit denial
            await AuditService(session).log(
                principal.org_id, principal.user_id,
                action="read", resource_type="media", resource_id=str(media.id),
                purpose=f"download_{scope}", request=request, success=False
            )
            raise HTTPException(status_code=403, detail=f"Consent required for scope '{scope}'")

        # presign URL and audit
        url = registry.object_storage().presign_download(media.key, expires_seconds=600)
        await AuditService(session).log(
            principal.org_id, principal.user_id,
            action="read", resource_type="media", resource_id=str(media.id),
            purpose=f"download_{scope}", request=request, success=True
        )
        return {"media_id": str(media.id), "key": media.key, "mime_type": media.mime_type, "download_url": url}

    # If no patient linked (lead/anonymous), allow download (still audit)
    media_repo = MediaRepository(session)
    media = await media_repo.get(principal.org_id, msg.media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    url = registry.object_storage().presign_download(media.key, expires_seconds=600)
    await AuditService(session).log(
        principal.org_id, principal.user_id,
        action="read", resource_type="media", resource_id=str(media.id),
        purpose="download_unlinked", request=request, success=True
    )
    return {"media_id": str(media.id), "key": media.key, "mime_type": media.mime_type, "download_url": url}