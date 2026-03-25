import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("signai.database")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/signai")

Base = declarative_base()

try:
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    db_available = True
except Exception as e:
    logger.error(f"[Database] Failed to initialize PostgreSQL engine: {e}")
    db_available = False
    
async def get_db():
    if not db_available:
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"[Database] Session error: {e}")
            raise
