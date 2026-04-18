# ============================================================
# Tests — Shared Fixtures
# ============================================================

import pytest
from app.db.database import init_db


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="function")
async def clear_db():
    from app.db.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
