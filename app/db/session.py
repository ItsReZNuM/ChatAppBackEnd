from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from typing import AsyncGenerator

# Async engine for FastAPI
async_engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

# Sync engine/session for Celery & Alembic
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

