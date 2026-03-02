import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.db.models import User
from app.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)
from app.repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"])


class AuthService:
    def __init__(self, repo: UserRepo) -> None:
        self._repo = repo

    async def register(self, username: str, password: str) -> User:
        existing = await self._repo.get_by_username(username)
        if existing:
            raise UserAlreadyExistsError(f"User '{username}' already exists.")

        hashed = pwd_context.hash(password)
        user = await self._repo.create(username, hashed)
        logger.info("User registered: %s", username)
        return user

    async def login(self, username: str, password: str) -> dict:
        user = await self._repo.get_by_username(username)
        if not user or not pwd_context.verify(password, user.hashed_password):
            logger.warning("Failed login attempt for: %s", username)
            raise InvalidCredentialsError("Invalid username or password.")

        access_token = self._create_access_token(user)
        token_id = uuid.uuid4()

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._repo.create_refresh_token(user.id, token_id, expires_at)

        logger.info("User logged in: %s", username)
        return {
            "access_token": access_token,
            "refresh_token": str(token_id),
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token_str: str) -> dict:
        try:
            token_id = uuid.UUID(refresh_token_str)
        except ValueError:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        now = datetime.now(timezone.utc)

        # Атомарно забираем токен (DELETE ... RETURNING) — защита от race condition
        token = await self._repo.take_refresh_token(token_id)
        if not token or token.expires_at < now:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired.")

        user = await self._repo.get_by_id(token.user_id)
        if not user:
            raise InvalidRefreshTokenError("User not found.")

        access_token = self._create_access_token(user)
        new_token_id = uuid.uuid4()
        new_expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        await self._repo.create_refresh_token(user.id, new_token_id, new_expires)

        logger.info("Token refreshed for user: %s", user.username)
        return {
            "access_token": access_token,
            "refresh_token": str(new_token_id),
            "token_type": "bearer",
        }

    @staticmethod
    def decode_access_token(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise InvalidCredentialsError("Access token has expired.")
        except jwt.InvalidTokenError:
            raise InvalidCredentialsError("Invalid access token.")

    @staticmethod
    def _create_access_token(user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": now,
        }
        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
