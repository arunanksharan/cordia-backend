import uuid
from dataclasses import asdict, dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.platform.provider_registry import registry
from app.modules.vector.repository import VectorRepository
from app.modules.vector.models import TextChunk
from app.modules.vector.schemas import (
    IngestTranscriptsByConversation, IngestMessageTranscript, IngestTicketNotes, IngestKnowledge, SearchQuery
)
from app.modules.conversations.transcripts import Transcript
from app.modules.conversations.models import Conversation, Message
from app.modules.tickets.models import TicketNote
from app.modules.consent.service import ConsentService

@dataclass
class ChunkSpec:
    text: str
    locator: dict

class VectorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = VectorRepository(session)
        self.embedder = registry.embeddings()

    # ---------- Chunking ----------
    def _chunk_text(self, text: str, chunk_chars: int, overlap: int) -> list[str]:
        text = text or ""
        if len(text) <= chunk_chars:
            return [text]
        chunks: list[str] = []
        i = 0
        while i < len(text):
            chunk = text[i:i + chunk_chars]
            chunks.append(chunk)
            if i + chunk_chars >= len(text):
                break
            i += max(1, (chunk_chars - overlap))
        return chunks

    # ---------- Ingest sources ----------
    async def ingest_conversation(self, org_id: uuid.UUID, payload: IngestTranscriptsByConversation) -> dict:
        # gather transcripts for conversation
        convo = await self.session.execute(
            select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.org_id == org_id, Conversation.deleted_at.is_(None))
        )
        conv = convo.scalar_one_or_none()
        if not conv:
            return {"indexed": 0}

        # Consent check if patient-linked
        if conv.patient_id:
            allowed = await ConsentService(self.session).is_allowed(org_id, conv.patient_id, "data_processing")
            if not allowed:
                return {"indexed": 0, "skipped": "consent_required"}

        tx = await self.session.execute(
            select(Transcript, Message.id.label("message_id"))
            .join(Message, Transcript.message_id == Message.id, isouter=True)
            .where(
                Transcript.org_id == org_id,
                Transcript.deleted_at.is_(None),
                (Transcript.message_id == Message.id) & (Message.conversation_id == payload.conversation_id)
            )
        )
        rows = tx.all()
        specs: list[ChunkSpec] = []
        for t, message_id in rows:
            for idx, ch in enumerate(self._chunk_text(t.text, payload.chunk_chars, payload.overlap)):
                specs.append(ChunkSpec(text=ch, locator={
                    "conversation_id": str(payload.conversation_id),
                    "message_id": str(message_id) if message_id else None,
                    "transcript_id": str(t.id)
                }))

        # delete previous chunks for this source
        await self.repo.delete_by_source(org_id, "transcript", str(payload.conversation_id))

        if not specs:
            return {"indexed": 0}
        vectors = await self.embedder.embed([s.text for s in specs])
        objs = []
        for i, s in enumerate(specs):
            objs.append(TextChunk(
                org_id=org_id,
                source_type="transcript",
                source_id=str(payload.conversation_id),
                patient_id=conv.patient_id,
                locator=s.locator,
                text=s.text,
                chunk_index=i,
                embedding=vectors[i],
            ))
        await self.repo.insert_chunks(objs)
        await self.session.commit()
        return {"indexed": len(objs)}

    async def ingest_message(self, org_id: uuid.UUID, payload: IngestMessageTranscript) -> dict:
        # load transcript by message
        res = await self.session.execute(
            select(Transcript, Message, Conversation.patient_id)
            .join(Message, Transcript.message_id == Message.id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Transcript.org_id == org_id,
                Transcript.deleted_at.is_(None),
                Transcript.message_id == payload.message_id,
                Conversation.org_id == org_id,
                Conversation.deleted_at.is_(None),
            )
        )
        row = res.first()
        if not row:
            return {"indexed": 0}
        t, msg, patient_id = row

        if patient_id:
            allowed = await ConsentService(self.session).is_allowed(org_id, patient_id, "data_processing")
            if not allowed:
                return {"indexed": 0, "skipped": "consent_required"}

        specs = [ChunkSpec(text=ch, locator={
            "conversation_id": str(msg.conversation_id),
            "message_id": str(msg.id),
            "transcript_id": str(t.id),
        }) for ch in self._chunk_text(t.text, payload.chunk_chars, payload.overlap)]

        await self.repo.delete_by_source(org_id, "transcript", str(msg.conversation_id))
        if not specs:
            return {"indexed": 0}
        vectors = await self.embedder.embed([s.text for s in specs])
        objs = []
        for i, s in enumerate(specs):
            objs.append(TextChunk(
                org_id=org_id,
                source_type="transcript",
                source_id=str(msg.conversation_id),
                patient_id=patient_id,
                locator=s.locator,
                text=s.text,
                chunk_index=i,
                embedding=vectors[i],
            ))
        await self.repo.insert_chunks(objs)
        await self.session.commit()
        return {"indexed": len(objs)}

    async def ingest_ticket(self, org_id: uuid.UUID, payload: IngestTicketNotes) -> dict:
        # gather notes for ticket
        res = await self.session.execute(
            select(TicketNote).where(
                TicketNote.org_id == org_id,
                TicketNote.deleted_at.is_(None),
                TicketNote.ticket_id == payload.ticket_id
            ).order_by(TicketNote.created_at.asc())
        )
        notes = res.scalars().all()
        if not notes:
            return {"indexed": 0}
        # delete previous chunks for this ticket
        await self.repo.delete_by_source(org_id, "ticket_note", str(payload.ticket_id))

        specs: list[ChunkSpec] = []
        for n in notes:
            for idx, ch in enumerate(self._chunk_text(n.body, payload.chunk_chars, payload.overlap)):
                specs.append(ChunkSpec(text=ch, locator={"ticket_id": str(payload.ticket_id), "note_id": str(n.id)}))

        vectors = await self.embedder.embed([s.text for s in specs])
        objs = []
        for i, s in enumerate(specs):
            objs.append(TextChunk(
                org_id=org_id,
                source_type="ticket_note",
                source_id=str(payload.ticket_id),
                patient_id=None,
                locator=s.locator,
                text=s.text,
                chunk_index=i,
                embedding=vectors[i],
            ))
        await self.repo.insert_chunks(objs)
        await self.session.commit()
        return {"indexed": len(objs)}

    async def ingest_knowledge(self, org_id: uuid.UUID, payload: IngestKnowledge) -> dict:
        # free text knowledge document; generate a synthetic source_id
        import uuid as uuidlib
        source_id = str(uuidlib.uuid4())
        specs = [ChunkSpec(text=ch, locator={"title": payload.title}) for ch in self._chunk_text(payload.text, payload.chunk_chars, payload.overlap)]
        vectors = await self.embedder.embed([s.text for s in specs])
        objs = []
        for i, s in enumerate(specs):
            objs.append(TextChunk(
                org_id=org_id,
                source_type="knowledge",
                source_id=source_id,
                patient_id=payload.patient_id,
                locator=s.locator,
                text=s.text,
                chunk_index=i,
                embedding=vectors[i],
            ))
        await self.repo.insert_chunks(objs)
        await self.session.commit()
        return {"indexed": len(objs), "source_id": source_id}

    # ---------- Search ----------
    async def search(self, org_id: uuid.UUID, payload: SearchQuery):
        vectors = await self.embedder.embed([payload.q])
        hits = await self.repo.search_hybrid(org_id, vectors[0], payload.q, top_k=payload.top_k, patient_id=payload.patient_id, source_type=payload.source_type)

        # Consent check at retrieval (if chunk tied to patient)
        result = []
        consent = ConsentService(self.session)
        for chunk, score in hits:
            if chunk.patient_id:
                allowed = await consent.is_allowed(org_id, chunk.patient_id, "data_processing")
                if not allowed:
                    continue
            # package
            result.append({
                "id": str(chunk.id),
                "org_id": str(chunk.org_id),
                "source_type": chunk.source_type,
                "source_id": chunk.source_id,
                "patient_id": str(chunk.patient_id) if chunk.patient_id else None,
                "locator": chunk.locator,
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "score": round(score, 6),
            })
        return result