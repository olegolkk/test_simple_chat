from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import asyncio
import json
import os
from typing import Dict, Set, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="WebSocket Chat Server", version="1.0.0")

# Настройки для продакшена
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=ALLOWED_HOSTS
    )


# Хранилище активных соединений чата
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, room: str = "general"):
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(client_id)

        return client_id

    def disconnect(self, client_id: str, room: str = "general"):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if room in self.rooms and client_id in self.rooms[room]:
            self.rooms[room].remove(client_id)
            if not self.rooms[room]:
                del self.rooms[room]

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except:
                pass

    async def broadcast_to_room(self, message: dict, room: str = "general", exclude: str = None):
        if room in self.rooms:
            for client_id in self.rooms[room]:
                if client_id != exclude and client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_json(message)
                    except:
                        pass

    def get_room_users(self, room: str) -> List[str]:
        if room in self.rooms:
            return list(self.rooms[room])
        return []


manager = ConnectionManager()


# Глобальное хранилище для WebRTC сигналинга
class WebRTCManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str, client_id: str):
        await websocket.accept()

        if room not in self.rooms:
            self.rooms[room] = {}

        self.rooms[room][client_id] = websocket
        print(f"WebRTC: {client_id} connected to room {room}")

        # Отправляем новому клиенту список всех участников WebRTC в комнате
        participants = list(self.rooms[room].keys())
        await websocket.send_json({
            "type": "participants",
            "participants": participants
        })

    def disconnect(self, room: str, client_id: str):
        if room in self.rooms and client_id in self.rooms[room]:
            del self.rooms[room][client_id]
            print(f"WebRTC: {client_id} disconnected from room {room}")

            if not self.rooms[room]:
                del self.rooms[room]

    async def send_to_client(self, room: str, target_client: str, message: dict, from_client: str = None):
        if room in self.rooms and target_client in self.rooms[room]:
            try:
                if from_client:
                    message["from"] = from_client
                await self.rooms[room][target_client].send_json(message)
                return True
            except:
                pass
        return False


webrtc_manager = WebRTCManager()

# HTML страница (та же, что и в предыдущей версии)
HTML_TEMPLATE = """..."""  # Здесь ваш HTML код


@app.get("/")
async def get_root():
    """Главная страница"""
    return HTMLResponse(HTML_TEMPLATE)


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/stats")
async def get_stats():
    """Получить статистику сервера"""
    return {
        "total_connections": len(manager.active_connections),
        "active_rooms": len(manager.rooms),
        "rooms_details": {
            room: len(clients) for room, clients in manager.rooms.items()
        },
        "webrtc_rooms": {
            room: list(clients.keys()) for room, clients in webrtc_manager.rooms.items()
        }
    }


@app.get("/rooms")
async def get_rooms():
    """Получить список всех комнат"""
    return {
        "rooms": list(manager.rooms.keys()),
        "room_details": {
            room: {
                "clients_count": len(clients),
                "clients": list(clients)
            } for room, clients in manager.rooms.items()
        }
    }


@app.websocket("/ws/{client_id}/{room}")
async def websocket_endpoint(
        websocket: WebSocket,
        client_id: str,
        room: str = "general"
):
    try:
        await manager.connect(websocket, client_id, room)

        welcome_message = {
            "type": "system",
            "content": f"Добро пожаловать в комнату {room}!",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "room": room
        }
        await manager.send_personal_message(welcome_message, client_id)

        user_joined = {
            "type": "system",
            "content": f"Пользователь {client_id} присоединился к чату",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "room": room
        }
        await manager.broadcast_to_room(user_joined, room, exclude=client_id)

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                message["client_id"] = client_id
                message["room"] = room
                message["timestamp"] = datetime.now().isoformat()

                if message.get("type") == "private":
                    target_client = message.get("target")
                    private_message = {
                        "type": "private",
                        "content": message.get("content", ""),
                        "from": client_id,
                        "timestamp": message["timestamp"]
                    }
                    await manager.send_personal_message(private_message, target_client)

                    await manager.send_personal_message({
                        "type": "private_sent",
                        "content": message.get("content", ""),
                        "to": target_client,
                        "timestamp": message["timestamp"]
                    }, client_id)

                else:
                    chat_message = {
                        "type": "chat",
                        "content": message.get("content", ""),
                        "client_id": client_id,
                        "timestamp": message["timestamp"],
                        "room": room
                    }
                    await manager.broadcast_to_room(chat_message, room)

            except json.JSONDecodeError:
                text_message = {
                    "type": "chat",
                    "content": data,
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat(),
                    "room": room
                }
                await manager.broadcast_to_room(text_message, room)

    except WebSocketDisconnect:
        manager.disconnect(client_id, room)

        user_left = {
            "type": "system",
            "content": f"Пользователь {client_id} покинул чат",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "room": room
        }
        await manager.broadcast_to_room(user_left, room)

    except Exception as e:
        print(f"Ошибка: {e}")
        manager.disconnect(client_id, room)


@app.websocket("/ws/webrtc/{room}/{client_id}")
async def webrtc_signaling(
        websocket: WebSocket,
        room: str,
        client_id: str
):
    try:
        await webrtc_manager.connect(websocket, room, client_id)

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("target"):
                    target_client = message["target"]
                    message["from"] = client_id

                    success = await webrtc_manager.send_to_client(room, target_client, message)
                    if not success:
                        print(f"WebRTC: Не удалось отправить сообщение от {client_id} к {target_client}")

            except json.JSONDecodeError:
                print(f"WebRTC: Получен некорректный JSON от {client_id}")

    except WebSocketDisconnect:
        webrtc_manager.disconnect(room, client_id)

    except Exception as e:
        print(f"WebRTC ошибка: {e}")
        webrtc_manager.disconnect(room, client_id)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=ENVIRONMENT == "development"
    )