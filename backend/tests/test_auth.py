# ============================================================
# Tests — Authentication Endpoints
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


class TestAuthRegister:

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        res = await client.post("/api/auth/register", json={
            "username": "testuser_auth",
            "password": "securepassword123",
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
            "password": "pass123",
        })
        res = await client.post("/api/auth/register", json={
            "username": "duplicate_user",
            "password": "pass456",
        })
        assert res.status_code == 400


class TestAuthLogin:

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        # Register first
        await client.post("/api/auth/register", json={
            "username": "login_user",
            "password": "mypassword",
        })
        # Login with form data
        res = await client.post("/api/auth/login", data={
            "username": "login_user",
            "password": "mypassword",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "username": "wrong_pw_user",
            "password": "correct",
        })
        res = await client.post("/api/auth/login", data={
            "username": "wrong_pw_user",
            "password": "wrong",
        })
        assert res.status_code == 401


class TestAuthMe:

    @pytest.mark.asyncio
    async def test_me_with_token(self, client):
        reg = await client.post("/api/auth/register", json={
            "username": "me_user",
            "password": "pass",
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
    async def test_cache_delete_with_auth(self, client):
        reg = await client.post("/api/auth/register", json={
            "username": "admin_user",
            "password": "adminpass",
        })
        token = reg.json()["access_token"]
        res = await client.delete("/api/cache", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 200
        assert res.json()["status"] == "cleared"
