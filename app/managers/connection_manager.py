from typing import Dict, Set, List, Optional
from fastapi import WebSocket
from app.utils.logger import logger


class ConnectionManager:
    """Менеджер WebSocket соединений для чата"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, room: str = "general") -> str:
        """Подключение клиента к комнате"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(client_id)

        logger.info(f"Client {client_id} connected to room {room}")
        return client_id

    def disconnect(self, client_id: str, room: str = "general") -> None:
        """Отключение клиента от комнаты"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if room in self.rooms and client_id in self.rooms[room]:
            self.rooms[room].remove(client_id)
            if not self.rooms[room]:
                del self.rooms[room]

        logger.info(f"Client {client_id} disconnected from room {room}")

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Отправка личного сообщения клиенту"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")

    async def broadcast_to_room(
            self,
            message: dict,
            room: str = "general",
            exclude: Optional[str] = None
    ) -> None:
        """Отправка сообщения всем в комнате"""
        if room in self.rooms:
            for client_id in self.rooms[room]:
                if client_id != exclude and client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id}: {e}")

    def get_room_users(self, room: str) -> List[str]:
        """Получение списка пользователей в комнате"""
        if room in self.rooms:
            return list(self.rooms[room])
        return []

    def get_stats(self) -> dict:
        """Получение статистики"""
        return {
            "total_connections": len(self.active_connections),
            "active_rooms": len(self.rooms),
            "rooms_details": {
                room: len(clients) for room, clients in self.rooms.items()
            }
        }