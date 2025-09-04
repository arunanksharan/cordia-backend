import hashlib
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.provider_registry import registry
from app.modules.media.repository import MediaRepository
from app.modules.media.models import MediaAsset

class MediaService:
    def __init__(self, session: AsyncSession):
        self.repo = MediaRepository(session)
        self.session = session

    async def upload_file(self, org_id: uuid.UUID, file: UploadFile, *, prefix: str = "uploads/") -> tuple[MediaAsset, str]:
        # Read file fully (for production consider streaming + multipart direct-to-S3)
        data = await file.read()
        size = len(data)
        sha = hashlib.sha256(data).hexdigest()

        # Normalize key: prefix/org_id/sha.ext
        ext = ""
        if file.filename and "." in file.filename:
            ext = file.filename.rsplit(".", 1)[1].lower()
        key = f"{prefix}{org_id}/{sha}{('.' + ext) if ext else ''}"

        storage = registry.object_storage()
        storage.put_bytes(key, data, content_type=file.content_type or "application/octet-stream")
        obj = await self.repo.create(
            org_id,
            key=key,
            sha256=sha,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=size,
            duration_ms=None,
            source="upload",
        )
        await self.session.commit()

        download_url = storage.presign_download(key, expires_seconds=600)
        return obj, download_url