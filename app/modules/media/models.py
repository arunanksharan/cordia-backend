import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, BigInteger
from app.core.base import Base, TimestampedTenantMixin

class MediaAsset(Base, TimestampedTenantMixin):
    # The "key" is the storage object key relative to provider (e.g., s3 key or local path key).
    key: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # for audio/video if known
    source: Mapped[str] = mapped_column(String(64), default="upload")  # upload, recording, attachment, import