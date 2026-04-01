from typing import Dict, Optional
from fastapi import WebSocket
from app.utils.logger import logger


class ConnectionManager:
    """Менеджер WebSocket соединений для личных чатов"""

    def __init__(self):
        # Храним активные соединения: user_id -> websocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Подключение пользователя"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected")
        return user_id

    def disconnect(self, user_id: str) -> None:
        """Отключение пользователя"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str) -> bool:
        """Отправка личного сообщения"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
        return False

    async def send_to_user(self, message: dict, user_id: str) -> bool:
        """Отправка сообщения пользователю"""
        return await self.send_personal_message(message, user_id)

    def get_online_users(self) -> list:
        """Получение списка онлайн пользователей"""
        return list(self.active_connections.keys())

    def is_online(self, user_id: str) -> bool:
        """Проверка, онлайн ли пользователь"""
        return user_id in self.active_connections