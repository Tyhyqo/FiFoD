import uuid

import pytest
from httpx import AsyncClient

from app.repositories.user_repo import UserRepo
from app.services.auth_service import AuthService, pwd_context


class TestAuthRegister:

    async def test_register_success(self, auth_client: AsyncClient):
        username = f"user_{uuid.uuid4().hex[:8]}"
        response = await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert "id" in data

    async def test_register_duplicate(self, auth_client: AsyncClient):
        username = f"dup_{uuid.uuid4().hex[:8]}"
        await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        response = await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        assert response.status_code == 409

    async def test_register_short_password(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/auth/register",
            json={"username": "someuser", "password": "12345"},
        )
        assert response.status_code == 422

    async def test_register_short_username(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "secret123"},
        )
        assert response.status_code == 422


class TestAuthLogin:

    async def test_login_success(self, auth_client: AsyncClient):
        username = f"login_{uuid.uuid4().hex[:8]}"
        await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        response = await auth_client.post(
            "/api/auth/login",
            data={"username": username, "password": "secret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, auth_client: AsyncClient):
        username = f"wrong_{uuid.uuid4().hex[:8]}"
        await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        response = await auth_client.post(
            "/api/auth/login",
            data={"username": username, "password": "wrongpass"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "secret123"},
        )
        assert response.status_code == 401


class TestAuthRefresh:

    async def test_refresh_success(self, auth_client: AsyncClient):
        username = f"refresh_{uuid.uuid4().hex[:8]}"
        await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        login_resp = await auth_client.post(
            "/api/auth/login",
            data={"username": username, "password": "secret123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["refresh_token"] != refresh_token

    async def test_refresh_reuse_rejected(self, auth_client: AsyncClient):
        username = f"reuse_{uuid.uuid4().hex[:8]}"
        await auth_client.post(
            "/api/auth/register",
            json={"username": username, "password": "secret123"},
        )
        login_resp = await auth_client.post(
            "/api/auth/login",
            data={"username": username, "password": "secret123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        # Повторное использование того же токена должно быть отклонено
        response = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401

    async def test_refresh_invalid_token(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "not-a-uuid"},
        )
        assert response.status_code == 401


class TestDecodeAccessToken:

    def test_decode_valid_token(self):
        from app.db.models import User

        user = User(
            id=uuid.uuid4(),
            username="testuser",
            hashed_password="hashed",
        )
        token = AuthService._create_access_token(user)
        payload = AuthService.decode_access_token(token)
        assert payload["sub"] == str(user.id)
        assert payload["username"] == "testuser"

    def test_decode_invalid_token(self):
        from app.exceptions import InvalidCredentialsError

        with pytest.raises(InvalidCredentialsError):
            AuthService.decode_access_token("invalid.token.here")
