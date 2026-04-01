from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
from datetime import datetime
from app.managers import ConnectionManager, WebRTCManager
from app.auth.auth import AuthHandler
from app.utils.logger import logger

websocket_router = APIRouter()
manager = ConnectionManager()
webrtc_manager = WebRTCManager()


@websocket_router.websocket("/ws/{room}")
async def websocket_endpoint(
        websocket: WebSocket,
        room: str = "general",
        token: str = Query(None)
) -> None:
    """WebSocket эндпоинт для чата с аутентификацией"""

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

            elif message_type == "webrtc_offer" or message_type == "webrtc_answer" or message_type == "webrtc_ice":
                # Перенаправляем WebRTC сигналы через WebRTC менеджер
                target = message.get("target")
                if target:
                    await webrtc_manager.send_to_client(room, target, {
                        "type": message_type,
                        "from": client_id,
                        "data": message.get("data")
                    })

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


@websocket_router.websocket("/ws/webrtc/{room}")
async def webrtc_signaling(
        websocket: WebSocket,
        room: str,
        token: str = Query(None)
) -> None:
    """WebSocket эндпоинт для WebRTC сигналинга с аутентификацией"""

    # Проверяем токен
    try:
        user = AuthHandler.get_current_user(token) if token else None
        if not user:
            await websocket.close(code=1008, reason="Authentication required")
            return

        client_id = user["username"]

    except Exception as e:
        await websocket.close(code=1008, reason="Invalid token")
        logger.error(f"WebRTC authentication error: {e}")
        return

    try:
        await webrtc_manager.connect(websocket, room, client_id)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("target"):
                target = message["target"]
                message["from"] = client_id
                await webrtc_manager.send_to_client(room, target, message)

    except WebSocketDisconnect:
        webrtc_manager.disconnect(room, client_id)
    except Exception as e:
        logger.error(f"WebRTC error: {e}")
        webrtc_manager.disconnect(room, client_id)


async def broadcast_users_list(room: str):
    """Отправляет обновленный список пользователей всем в комнате"""
    users_in_room = manager.get_room_users(room)
    await manager.broadcast_to_room({
        "type": "users_list",
        "users": users_in_room,
        "timestamp": datetime.now().isoformat()
    }, room)