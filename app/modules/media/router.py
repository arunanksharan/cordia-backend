from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import get_principal, require_scopes, Principal
from app.modules.media.schemas import MediaUploadOut
from app.modules.media.service import MediaService

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

def svc(session: AsyncSession = Depends(get_session)) -> MediaService:
    return MediaService(session)

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