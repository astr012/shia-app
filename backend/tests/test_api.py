# ============================================================
# Tests â€” REST API Endpoints
# ============================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    """Test the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        res = await client.get("/health")
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_health_contains_fields(self, client):
        res = await client.get("/health")
        data = res.json()
        assert "status" in data
        assert "version" in data
        assert "uptime" in data
        assert "services" in data
        assert "config" in data

    @pytest.mark.asyncio
    async def test_health_status_online(self, client):
        res = await client.get("/health")
        assert res.json()["status"] == "online"


class TestTranslateEndpoint:
    """Test the /api/translate endpoint."""

    @pytest.mark.asyncio
    async def test_sign_to_speech(self, client):
        res = await client.post("/api/translate", json={
            "text": "hello",
            "mode": "SIGN_TO_SPEECH",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "SIGN_TO_SPEECH"
        assert data["translated_text"] == "Hello!"

    @pytest.mark.asyncio
    async def test_speech_to_sign(self, client):
        res = await client.post("/api/translate", json={
            "text": "hello",
            "mode": "SPEECH_TO_SIGN",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "SPEECH_TO_SIGN"
        assert "WAVE_HELLO" in data["translated_text"]

    @pytest.mark.asyncio
    async def test_invalid_mode_rejected(self, client):
        res = await client.post("/api/translate", json={
            "text": "hello",
            "mode": "INVALID",
        })
        assert res.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_text_rejected(self, client):
        res = await client.post("/api/translate", json={
            "text": "",
            "mode": "SIGN_TO_SPEECH",
        })
        assert res.status_code == 422


class TestVocabularyEndpoint:

    @pytest.mark.asyncio
    async def test_vocabulary_returns_data(self, client):
        res = await client.get("/api/vocabulary")
        assert res.status_code == 200
        data = res.json()
        assert "vocabulary" in data
        assert "total_words" in data
        assert data["total_words"] > 50

    @pytest.mark.asyncio
    async def test_vocabulary_has_hello(self, client):
        res = await client.get("/api/vocabulary")
        vocab = res.json()["vocabulary"]
        assert "hello" in vocab


class TestGrammarRulesEndpoint:

    @pytest.mark.asyncio
    async def test_grammar_rules_returns_data(self, client):
        res = await client.get("/api/grammar-rules")
        assert res.status_code == 200
        data = res.json()
        assert "rules" in data
        assert "total_rules" in data
        assert data["total_rules"] >= 25


class TestCacheEndpoint:

    @pytest.mark.asyncio
    async def test_cache_stats(self, client):
        res = await client.get("/api/cache")
        assert res.status_code == 200
        data = res.json()
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate_pct" in data

    @pytest.mark.asyncio
    async def test_cache_clear_requires_auth(self, client):
        """DELETE /api/cache now requires authentication."""
        res = await client.delete("/api/cache")
        assert res.status_code == 401



