import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Use SQLite by default for development; can be easily swapped to PostgreSQL
# e.g., postgresql+asyncpg://user:pass@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./signai.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    # connect_args={"check_same_thread": False} is needed for SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Create all tables if they don't exist"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
