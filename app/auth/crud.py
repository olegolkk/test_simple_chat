from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, users_db
from app.auth.utils import verify_password, hash_password


class UserCRUD:
    """CRUD операции с пользователями"""

    @staticmethod
    async def create_user(session: AsyncSession, username: str, email: str, password: str) -> Optional[User]:
        """Создание нового пользователя"""
        user = User(username=username,
                    email=email,
                    password_hash=hash_password(password))

        session.add(user)
        await session.commit()
        return user


    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        query = select(User).where(User.username == username)
        result = await session.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """Получение пользователя по email"""
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = await UserCRUD.get_user_by_username(session, username)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    async def get_all_users(session: AsyncSession) -> Sequence[User]:
        """Получение всех пользователей"""
        query = select(User).order_by(User.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()