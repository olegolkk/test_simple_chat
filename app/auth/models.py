from typing import Dict, Any
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy import String, func

from app.config import settings
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Временное хранилище пользователей (в памяти)
# В реальном проекте замените на базу данных
users_db: Dict[str, Dict[str, Any]] = {}


class Base(DeclarativeBase):
    pass


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True)