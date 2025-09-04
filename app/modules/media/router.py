from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.media.schemas import MediaUploadOut
from app.modules.media.service import MediaService
from urllib.parse import unquote
from app.platform.provider_registry import registry
import hashlib


router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> MediaService:
    return MediaService(session)

@router.post("/presign", dependencies=[Depends(require_scopes("media:write"))])
async def presign_upload(principal: Principal = Depends(get_principal)):
    storage = registry.object_storage()
    # client can choose key; we return a safe prefix
    key_prefix = f"uploads/{principal.org_id}/"
    # provide sample key suggestion; frontend can change
    sample_key = key_prefix + "client-upload.bin"
    return {"key_prefix": key_prefix, "example": storage.presign_post(sample_key)}

@router.put("/direct_put", dependencies=[Depends(require_scopes("media:write"))])
async def direct_put(key: str, body: bytes = Body(...), principal: Principal = Depends(get_principal), service: MediaService = Depends(svc)):
    # accept bytes, store, and register MediaAsset
    file_like = type("UF",(object,),{"filename":key.split("/")[-1],"content_type":"application/octet-stream","read":lambda self: body})()
    obj, url = await service.upload_file(principal.org_id, file_like)
    return {"id": str(obj.id), "download_url": url, "key": obj.key, "size": obj.size_bytes, "sha256": obj.sha256}

@router.post("/upload", response_model=MediaUploadOut, dependencies=[Depends(require_scopes("media:write"))])
async def upload_media(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    service: MediaService = Depends(svc),
):
    if file.size is not None and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (>100MB)")
    obj, url = await service.upload_file(principal.org_id, file)
    return {
        "id": obj.id,
        "org_id": obj.org_id,
        "key": obj.key,
        "mime_type": obj.mime_type,
        "size_bytes": obj.size_bytes,
        "download_url": url,
    }