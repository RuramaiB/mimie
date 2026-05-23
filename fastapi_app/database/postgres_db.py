import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from typing import AsyncGenerator
from config import settings

logger = logging.getLogger("land_system.database.postgres")

# Construct PostgreSQL Async connection string using asyncpg
POSTGRES_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# Initialize Asynchronous Engine
engine = create_async_engine(
    POSTGRES_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_postgres_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency yielding scoped AsyncSession instances for PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def check_postgres_health() -> bool:
    """
    Performs quick SELECT query to verify PostgreSQL active state.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"PostgreSQL Health Check Failed: {e}")
        return False
