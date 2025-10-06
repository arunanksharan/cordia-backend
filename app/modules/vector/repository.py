import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, literal, desc
from app.modules.vector.models import TextChunk

class VectorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_by_source(self, org_id: uuid.UUID, source_type: str, source_id: str) -> int:
        q = select(TextChunk).where(
            TextChunk.org_id == org_id,
            TextChunk.source_type == source_type,
            TextChunk.source_id == source_id,
            TextChunk.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        rows = res.scalars().all()
        for r in rows:
            r.deleted_at = func.now()  # soft delete
        await self.session.flush()
        return len(rows)

    async def insert_chunks(self, objs: list[TextChunk]) -> None:
        self.session.add_all(objs)
        await self.session.flush()

    async def search_hybrid(self, org_id: uuid.UUID, query_vec: list[float], query_text: str, *, top_k: int = 10, patient_id: uuid.UUID | None = None, source_type: str | None = None) -> list[tuple[TextChunk, float]]:
        conds = [TextChunk.org_id == org_id, TextChunk.deleted_at.is_(None)]
        if patient_id:
            conds.append(TextChunk.patient_id == patient_id)
        if source_type:
            conds.append(TextChunk.source_type == source_type)

        # vector distance (smaller is closer)
        dist = TextChunk.embedding.l2_distance(query_vec).label("dist")

        # FTS rank
        tsvec = func.to_tsvector(literal("simple"), TextChunk.text)
        tsq = func.plainto_tsquery(literal("simple"), query_text)
        rank = func.ts_rank_cd(tsvec, tsq).label("rank")

        # Hybrid score: sim from dist + weighted FTS rank
        sim = (1.0 / (1.0 + dist)).label("sim")
        score = (sim + (rank * 0.3)).label("score")

        q = (
            select(TextChunk, score)
            .where(and_(*conds))
            .order_by(desc(score))
            .limit(top_k)
        )
        res = await self.session.execute(q)
        rows = res.all()
        return [(row[0], float(row[1])) for row in rows]