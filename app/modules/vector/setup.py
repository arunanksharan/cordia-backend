from sqlalchemy import text
from app.core.db import engine

async def ensure_vector_indexes():
    # Create FTS + IVFFLAT indexes for TextChunk
    # Note: IVFFLAT requires ANALYZE after substantial inserts to be effective.
    async with engine.begin() as conn:
        # FTS index on to_tsvector('simple', text)
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS textchunk_fts_idx ON textchunk USING gin (to_tsvector('simple', text))"
        )
        # Vector index (L2 distance)
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS textchunk_embedding_idx ON textchunk USING ivfflat (embedding vector_l2_ops) WITH (lists=100)"
        )