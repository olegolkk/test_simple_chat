from typing import Dict, Any
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.config import settings

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Временное хранилище пользователей (в памяти)
# В реальном проекте замените на базу данных
users_db: Dict[str, Dict[str, Any]] = {}


class User:
    """Модель пользователя"""

    def __init__(self, username: str, email: str, password: str):
        self.username = username
        self.email = email
        self.password_hash = self.hash_password(password)
        self.created_at = datetime.now()
        self.is_active = True

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return pwd_context.verify(plain_password, hashed_password)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }


def create_access_token(data: dict) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None