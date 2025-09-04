import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from app.core.base import Base, TimestampedTenantMixin

class TextChunk(Base, TimestampedTenantMixin):
    """
    Indexable chunk of text with vector + FTS.
    Sources:
      - transcript (message/conversation)
      - ticket_note
      - knowledge (free text ingestion)
    """
    source_type: Mapped[str] = mapped_column(String(32))  # transcript | ticket_note | knowledge
    source_id: Mapped[str] = mapped_column(String(64))    # UUID string or custom id
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient.id"), nullable=True)

    # Optional cross-links for provenance
    locator: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # e.g., {"conversation_id": "...", "message_id": "..."}

    text: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)

    # Vector column (pgvector)
    embedding: Mapped[list[float]] = mapped_column(Vector(dim=384))