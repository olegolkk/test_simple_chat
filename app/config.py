import os
from typing import List
import dotenv

dotenv.load_dotenv()

class Settings:
    """Настройки приложения"""

    # Общие настройки
    APP_TITLE: str = "WebSocket + WebRTC Chat Server"
    APP_VERSION: str = "1.0.0"

    # DB настройки
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "chat_db")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "chat-db")

    # JWT настройки
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS настройки
    CORS_ALLOW_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # WebSocket настройки
    WS_MAX_SIZE: int = 1024 * 1024  # 1MB

    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))

    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def get_async_db_url(self):
        print(f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}")
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}"

    @property
    def get_sync_db_url(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}"

settings = Settings()