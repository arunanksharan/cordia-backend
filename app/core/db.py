from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings
from .base import Base

engine = create_async_engine(settings.POSTGRES_DSN, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_models():
    ## In dev-only "create_all" mode, keep old behavior; otherwise, migrations own the schema.
    if settings.DB_MANAGE.lower() == "create_all":
        from sqlalchemy import text
        from .base import Base
        async with engine.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS btree_gin")
            await conn.run_sync(Base.metadata.create_all)