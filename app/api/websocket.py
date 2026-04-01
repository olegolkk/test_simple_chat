from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from datetime import datetime
from app.api.routes import connection_manager, webrtc_manager
from app.utils.logger import logger

websocket_router = APIRouter()


@websocket_router.websocket("/ws/{client_id}/{room}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    room: str = "general"
) -> None:
    """WebSocket эндпоинт для чата"""
    try:
        await connection_manager.connect(websocket, client_id, room)

        # Приветственное сообщение
        await connection_manager.send_personal_message({
            "type": "system",
            "content": f"Добро пожаловать в комнату {room}!",
            "timestamp": datetime.now().isoformat()
        }, client_id)

        # Уведомление о новом пользователе
        await connection_manager.broadcast_to_room({
            "type": "system",
            "content": f"Пользователь {client_id} присоединился к чату",
            "timestamp": datetime.now().isoformat()
        }, room, exclude=client_id)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            message["client_id"] = client_id
            message["room"] = room
            message["timestamp"] = datetime.now().isoformat()

            await connection_manager.broadcast_to_room({
                "type": "chat",
                "content": message.get("content", ""),
                "client_id": client_id,
                "timestamp": message["timestamp"]
            }, room)

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id, room)
        await connection_manager.broadcast_to_room({
            "type": "system",
            "content": f"Пользователь {client_id} покинул чат",
            "timestamp": datetime.now().isoformat()
        }, room)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(client_id, room)


@websocket_router.websocket("/ws/webrtc/{room}/{client_id}")
async def webrtc_signaling(
    websocket: WebSocket,
    room: str,
    client_id: str
) -> None:
    """WebSocket эндпоинт для WebRTC сигналинга"""
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