import os
from typing import List


class Settings:
    """Настройки приложения"""

    # Общие настройки
    APP_TITLE: str = "WebSocket + WebRTC Chat Server"
    APP_VERSION: str = "1.0.0"

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


settings = Settings()