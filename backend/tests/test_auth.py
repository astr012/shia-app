# ============================================================
# Tests â€” Authentication Endpoints
#
# All test passwords comply with the password policy:
#   min 8 chars, 1 uppercase, 1 digit.
# ============================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

# Password that satisfies all policy requirements
STRONG_PASSWORD = "TestPass1"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAuthRegister:

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        res = await client.post("/api/auth/register", json={
            "username": "testuser_auth",
            "password": STRONG_PASSWORD,
            "dialect": "ASL",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["username"] == "testuser_auth"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_fails(self, client):
        await client.post("/api/auth/register", json={
            "username": "duplicate_user",
            "password": STRONG_PASSWORD,
        })
        res = await client.post("/api/auth/register", json={
            "username": "duplicate_user",
            "password": STRONG_PASSWORD,
        })
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_register_weak_password_rejected(self, client):
        """Password policy enforcement: short password rejected."""
        res = await client.post("/api/auth/register", json={
            "username": "weak_pw_user",
            "password": "abc",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_register_no_uppercase_rejected(self, client):
        """Password policy enforcement: no uppercase rejected."""
        res = await client.post("/api/auth/register", json={
            "username": "no_upper_user",
            "password": "testpass1",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_register_no_digit_rejected(self, client):
        """Password policy enforcement: no digit rejected."""
        res = await client.post("/api/auth/register", json={
            "username": "no_digit_user",
            "password": "TestPass",
        })
        assert res.status_code == 422


class TestAuthLogin:

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        # Register first
        await client.post("/api/auth/register", json={
            "username": "login_user",
            "password": STRONG_PASSWORD,
        })
        # Login with form data
        res = await client.post("/api/auth/login", data={
            "username": "login_user",
            "password": STRONG_PASSWORD,
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "username": "wrong_pw_user",
            "password": STRONG_PASSWORD,
        })
        res = await client.post("/api/auth/login", data={
            "username": "wrong_pw_user",
            "password": "WrongPass1",
        })
        assert res.status_code == 401


class TestAuthMe:

    @pytest.mark.asyncio
    async def test_me_with_token(self, client):
        reg = await client.post("/api/auth/register", json={
            "username": "me_user",
            "password": STRONG_PASSWORD,
        })
        token = reg.json()["access_token"]
        res = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 200
        assert res.json()["username"] == "me_user"

    @pytest.mark.asyncio
    async def test_me_without_token(self, client):
        res = await client.get("/api/auth/me")
        assert res.status_code == 401


class TestProtectedEndpoints:

    @pytest.mark.asyncio
    async def test_cache_delete_requires_admin(self, client):
        """Regular user (role='user') should get 403 on admin-only endpoints."""
        reg = await client.post("/api/auth/register", json={
            "username": "regular_user",
            "password": STRONG_PASSWORD,
        })
        token = reg.json()["access_token"]
        res = await client.delete("/api/cache", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_cache_delete_unauthenticated(self, client):
        """Unauthenticated requests should get 401."""
        res = await client.delete("/api/cache")
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_analytics_requires_admin(self, client):
        """Regular user (role='user') should get 403 on analytics."""
        reg = await client.post("/api/auth/register", json={
            "username": "analytics_user",
            "password": STRONG_PASSWORD,
        })
        token = reg.json()["access_token"]
        res = await client.get("/api/analytics", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 403
