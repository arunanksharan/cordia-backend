import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.media.models import MediaAsset

class MediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, org_id: uuid.UUID, *, key: str, sha256: str, mime_type: str, size_bytes: int, duration_ms: int | None, source: str) -> MediaAsset:
        obj = MediaAsset(
            org_id=org_id, key=key, sha256=sha256, mime_type=mime_type,
            size_bytes=size_bytes, duration_ms=duration_ms, source=source
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, org_id: uuid.UUID, media_id: uuid.UUID) -> MediaAsset | None:
        q = select(MediaAsset).where(
            MediaAsset.id == media_id,
            MediaAsset.org_id == org_id,
            MediaAsset.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()