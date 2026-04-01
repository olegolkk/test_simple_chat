from typing import Dict, Optional
from fastapi import WebSocket
from app.utils.logger import logger


class WebRTCManager:
    """Менеджер WebRTC сигналинга"""

    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str, client_id: str) -> None:
        """Подключение WebRTC клиента"""
        await websocket.accept()

        if room not in self.rooms:
            self.rooms[room] = {}

        self.rooms[room][client_id] = websocket
        logger.info(f"WebRTC: {client_id} connected to room {room}")

        # Отправляем новому клиенту список всех участников
        participants = list(self.rooms[room].keys())
        await websocket.send_json({
            "type": "participants",
            "participants": participants
        })

    def disconnect(self, room: str, client_id: str) -> None:
        """Отключение WebRTC клиента"""
        if room in self.rooms and client_id in self.rooms[room]:
            del self.rooms[room][client_id]
            logger.info(f"WebRTC: {client_id} disconnected from room {room}")

            if not self.rooms[room]:
                del self.rooms[room]

    async def send_to_client(
            self,
            room: str,
            target_client: str,
            message: dict,
            from_client: Optional[str] = None
    ) -> bool:
        """Отправка сигнала конкретному клиенту"""
        if room in self.rooms and target_client in self.rooms[room]:
            try:
                if from_client:
                    message["from"] = from_client
                await self.rooms[room][target_client].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending WebRTC message: {e}")
        return False

    def get_rooms_info(self) -> dict:
        """Получение информации о комнатах WebRTC"""
        return {
            room: list(clients.keys())
            for room, clients in self.rooms.items()
        }