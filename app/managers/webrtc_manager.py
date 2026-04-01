from typing import Dict, Optional
from fastapi import WebSocket
from app.utils.logger import logger


class WebRTCManager:
    """Менеджер WebRTC сигналинга для личных звонков"""

    def __init__(self):
        # Храним активные WebRTC соединения: user_id -> websocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Подключение WebRTC клиента"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebRTC: {user_id} connected")

    def disconnect(self, user_id: str) -> None:
        """Отключение WebRTC клиента"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebRTC: {user_id} disconnected")

    async def send_to_user(self, target_user: str, message: dict, from_user: Optional[str] = None) -> bool:
        """Отправка сигнала конкретному пользователю"""
        if target_user in self.active_connections:
            try:
                if from_user:
                    message["from"] = from_user
                await self.active_connections[target_user].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending WebRTC message to {target_user}: {e}")
        return False