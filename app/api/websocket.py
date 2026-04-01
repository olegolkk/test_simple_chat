from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
from datetime import datetime
from app.managers import ConnectionManager
from app.auth.auth import AuthHandler
from app.utils.logger import logger

websocket_router = APIRouter()
manager = ConnectionManager()


@websocket_router.websocket("/ws/{room}")
async def websocket_endpoint(
        websocket: WebSocket,
        room: str = "general",
        token: str = Query(None)
) -> None:
    """WebSocket эндпоинт с аутентификацией"""

    # Проверяем токен
    try:
        user = AuthHandler.get_current_user(token) if token else None
        if not user:
            await websocket.close(code=1008, reason="Authentication required")
            return

        client_id = user["username"]

    except Exception as e:
        await websocket.close(code=1008, reason="Invalid token")
        logger.error(f"Authentication error: {e}")
        return

    try:
        await manager.connect(websocket, client_id, room)

        # Отправляем приветственное сообщение
        await manager.send_personal_message({
            "type": "system",
            "content": f"Добро пожаловать в комнату {room}, {client_id}!",
            "timestamp": datetime.now().isoformat()
        }, client_id)

        # Отправляем текущий список пользователей новому клиенту
        users_in_room = manager.get_room_users(room)
        await manager.send_personal_message({
            "type": "users_list",
            "users": users_in_room,
            "timestamp": datetime.now().isoformat()
        }, client_id)

        # Уведомляем всех в комнате о новом пользователе
        await manager.broadcast_to_room({
            "type": "system",
            "content": f"Пользователь {client_id} присоединился к чату",
            "timestamp": datetime.now().isoformat()
        }, room, exclude=client_id)

        # Отправляем обновленный список пользователей всем в комнате
        await broadcast_users_list(room)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            message_type = message.get("type")

            if message_type == "chat":
                content = message.get("content", "")

                # Отправляем сообщение всем в комнате
                await manager.broadcast_to_room({
                    "type": "chat",
                    "content": content,
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat()
                }, room)

    except WebSocketDisconnect:
        manager.disconnect(client_id, room)

        # Уведомляем всех в комнате о выходе пользователя
        await manager.broadcast_to_room({
            "type": "system",
            "content": f"Пользователь {client_id} покинул чат",
            "timestamp": datetime.now().isoformat()
        }, room)

        # Отправляем обновленный список пользователей всем в комнате
        await broadcast_users_list(room)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id, room)


async def broadcast_users_list(room: str):
    """Отправляет обновленный список пользователей всем в комнате"""
    users_in_room = manager.get_room_users(room)
    await manager.broadcast_to_room({
        "type": "users_list",
        "users": users_in_room,
        "timestamp": datetime.now().isoformat()
    }, room)