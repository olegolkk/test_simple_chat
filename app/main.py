from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.auth import router as auth_router
from app.api.routes import router as http_router
from app.api.websocket import websocket_router
from app.utils.logger import logger

# Создание FastAPI приложения
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(auth_router)
app.include_router(http_router)
app.include_router(websocket_router)

logger.info("Application started successfully")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )