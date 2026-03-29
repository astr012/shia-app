# ============================================================
# Tests — Shared Fixtures
# ============================================================

import pytest
from app.db.database import init_db


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="session")
async def setup_db():
    """Create all database tables before any tests run."""
    await init_db()
