import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshToken, User


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def create(self, username: str, hashed_password: str) -> User:
        user = User(username=username, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def create_refresh_token(
        self, user_id: uuid.UUID, token_id: uuid.UUID, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(id=token_id, user_id=user_id, expires_at=expires_at)
        self._session.add(token)
        await self._session.commit()
        return token

    async def take_refresh_token(self, token_id: uuid.UUID) -> RefreshToken | None:
        """Атомарно удалить и вернуть refresh-токен (DELETE ... RETURNING)."""
        result = await self._session.execute(
            delete(RefreshToken)
            .where(RefreshToken.id == token_id)
            .returning(RefreshToken)
        )
        await self._session.commit()
        return result.scalar_one_or_none()

    async def delete_expired_refresh_tokens(self) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < now)
        )
        await self._session.commit()
