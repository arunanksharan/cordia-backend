from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings
from .base import Base

engine = create_async_engine(settings.POSTGRES_DSN, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_models():
    # For dev: create tables automatically. In prod, use Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)