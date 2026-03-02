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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, repo: UserRepo) -> None:
        self._repo = repo

    async def register(self, username: str, password: str) -> User:
        existing = await self._repo.get_by_username(username)
        if existing:
            raise UserAlreadyExistsError(f"Пользователь '{username}' уже существует.")

        hashed = pwd_context.hash(password)
        return await self._repo.create(username, hashed)

    async def login(self, username: str, password: str) -> dict:
        user = await self._repo.get_by_username(username)
        if not user or not pwd_context.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Неверное имя пользователя или пароль.")

        access_token = self._create_access_token(user)
        refresh_token_id, refresh_token_str = self._generate_refresh_token_id()

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._repo.create_refresh_token(user.id, refresh_token_id, expires_at)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token_str: str) -> dict:
        try:
            token_id = uuid.UUID(refresh_token_str)
        except ValueError:
            raise InvalidRefreshTokenError("Некорректный refresh-токен.")

        now = datetime.now(timezone.utc)
        await self._repo.delete_expired_refresh_tokens(now)

        token = await self._repo.get_refresh_token(token_id)
        if not token or token.expires_at < now:
            raise InvalidRefreshTokenError("Refresh-токен недействителен или истёк.")

        user = await self._repo.get_by_id(token.user_id)
        if not user:
            raise InvalidRefreshTokenError("Пользователь не найден.")

        await self._repo.delete_refresh_token(token_id)

        access_token = self._create_access_token(user)
        new_token_id, new_token_str = self._generate_refresh_token_id()
        new_expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        await self._repo.create_refresh_token(user.id, new_token_id, new_expires)

        return {
            "access_token": access_token,
            "refresh_token": new_token_str,
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
            raise InvalidCredentialsError("Токен доступа истёк.")
        except jwt.InvalidTokenError:
            raise InvalidCredentialsError("Некорректный токен доступа.")

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

    @staticmethod
    def _generate_refresh_token_id() -> tuple[uuid.UUID, str]:
        token_id = uuid.uuid4()
        return token_id, str(token_id)
