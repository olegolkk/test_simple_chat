from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.managers import ConnectionManager, WebRTCManager
from app.auth.auth import AuthHandler
from app.utils.logger import logger

websocket_router = APIRouter()
manager = ConnectionManager()
webrtc_manager = WebRTCManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        session: AsyncSession = Depends(get_session),
        token: str = Query(None)
) -> None:
    """WebSocket эндпоинт для личных чатов"""

    # Проверяем токен
    try:
        user = await AuthHandler.get_current_user(session, token) if token else None
        if not user:
            await websocket.close(code=1008, reason="Authentication required")
            return

        user_id = user.username

    except Exception as e:
        await websocket.close(code=1008, reason="Invalid token")
        logger.error(f"Authentication error: {e}")
        return

    try:
        await manager.connect(websocket, user_id)

        # Отправляем приветственное сообщение
        await manager.send_personal_message({
            "type": "system",
            "content": f"Добро пожаловать, {user_id}!",
            "timestamp": datetime.now().isoformat()
        }, user_id)

        # Отправляем список онлайн пользователей
        await broadcast_online_users()

        # Уведомляем всех о новом пользователе
        await broadcast_to_all({
            "type": "system",
            "content": f"Пользователь {user_id} вошел в чат",
            "timestamp": datetime.now().isoformat()
        }, exclude=user_id)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            message_type = message.get("type")

            if message_type == "chat":
                # Личное сообщение
                target_user = message.get("target")
                content = message.get("content", "")

                if target_user:
                    # Отправляем отправителю подтверждение
                    await manager.send_personal_message({
                        "type": "chat",
                        "content": content,
                        "from": user_id,
                        "to": target_user,
                        "timestamp": datetime.now().isoformat(),
                        "is_own": True
                    }, user_id)

                    # Отправляем получателю
                    success = await manager.send_personal_message({
                        "type": "chat",
                        "content": content,
                        "from": user_id,
                        "to": target_user,
                        "timestamp": datetime.now().isoformat()
                    }, target_user)

                    if not success:
                        await manager.send_personal_message({
                            "type": "system",
                            "content": f"Пользователь {target_user} не в сети",
                            "timestamp": datetime.now().isoformat()
                        }, user_id)

            elif message_type in ["webrtc_offer", "webrtc_answer", "webrtc_ice"]:
                # Перенаправляем WebRTC сигналы
                target = message.get("target")
                if target:
                    await webrtc_manager.send_to_user(target, {
                        "type": message_type,
                        "from": user_id,
                        "data": message.get("data")
                    })

    except WebSocketDisconnect:
        manager.disconnect(user_id)

        # Уведомляем всех о выходе пользователя
        await broadcast_to_all({
            "type": "system",
            "content": f"Пользователь {user_id} покинул чат",
            "timestamp": datetime.now().isoformat()
        })

        # Обновляем список онлайн пользователей
        await broadcast_online_users()

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id)


@websocket_router.websocket("/ws/webrtc")
async def webrtc_signaling(
        websocket: WebSocket,
        session: AsyncSession = Depends(get_session),
        token: str = Query(None)
) -> None:
    """WebSocket эндпоинт для WebRTC сигналинга"""

    # Проверяем токен
    try:
        user = await AuthHandler.get_current_user(session, token) if token else None
        if not user:
            await websocket.close(code=1008, reason="Authentication required")
            return

        user_id = user.username

    except Exception as e:
        await websocket.close(code=1008, reason="Invalid token")
        logger.error(f"WebRTC authentication error: {e}")
        return

    try:
        await webrtc_manager.connect(websocket, user_id)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("target"):
                target = message["target"]
                message["from"] = user_id
                await webrtc_manager.send_to_user(target, message)

    except WebSocketDisconnect:
        webrtc_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebRTC error: {e}")
        webrtc_manager.disconnect(user_id)


async def broadcast_online_users():
    """Отправляет список онлайн пользователей всем"""
    online_users = manager.get_online_users()
    await broadcast_to_all({
        "type": "users_list",
        "users": online_users,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_to_all(message: dict, exclude: str = None):
    """Отправляет сообщение всем онлайн пользователям"""
    for user_id, ws in manager.active_connections.items():
        if user_id != exclude:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")