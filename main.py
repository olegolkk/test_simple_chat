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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket + WebRTC Чат</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
        }

        .container {
            display: flex;
            height: 100vh;
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }

        .sidebar {
            width: 280px;
            background: #2c3e50;
            color: white;
            display: flex;
            flex-direction: column;
        }

        .user-info {
            padding: 20px;
            background: #34495e;
            border-bottom: 1px solid #3e5a6f;
        }

        .user-info h3 {
            margin-bottom: 10px;
            font-size: 14px;
            opacity: 0.8;
        }

        .user-id {
            background: #1abc9c;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
        }

        .rooms-section {
            flex: 1;
            padding: 20px;
        }

        .rooms-section h3 {
            margin-bottom: 15px;
            font-size: 14px;
            opacity: 0.8;
        }

        .room-item {
            padding: 10px;
            margin-bottom: 8px;
            background: #34495e;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .room-item:hover {
            background: #1abc9c;
            transform: translateX(5px);
        }

        .room-item.active {
            background: #1abc9c;
            border-left: 3px solid #fff;
        }

        .users-list {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #3e5a6f;
        }

        .users-list h3 {
            margin-bottom: 10px;
            font-size: 14px;
            opacity: 0.8;
        }

        .user-item {
            padding: 6px 10px;
            margin-bottom: 4px;
            background: #34495e;
            border-radius: 4px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .call-btn {
            background: #1abc9c;
            border: none;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
        }

        .call-btn:hover {
            background: #16a085;
        }

        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .chat-header {
            background: white;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }

        .chat-header h2 {
            color: #2c3e50;
            font-size: 20px;
        }

        .chat-header p {
            color: #7f8c8d;
            font-size: 12px;
            margin-top: 5px;
        }

        .video-area {
            background: #1a1a2e;
            padding: 20px;
            display: none;
        }

        .video-area.active {
            display: block;
        }

        .videos-container {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }

        .video-wrapper {
            flex: 1;
            min-width: 300px;
            position: relative;
            background: #16213e;
            border-radius: 8px;
            overflow: hidden;
        }

        .video-wrapper video {
            width: 100%;
            background: #0f0f1f;
            border-radius: 8px;
        }

        .video-label {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }

        .call-controls {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }

        .call-btn-large {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }

        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }

        .message {
            margin-bottom: 15px;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .message.system {
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
            font-style: italic;
        }

        .message-header {
            font-size: 12px;
            margin-bottom: 4px;
        }

        .message-sender {
            font-weight: bold;
            color: #3498db;
        }

        .message-time {
            color: #95a5a6;
            margin-left: 8px;
        }

        .message-content {
            background: white;
            padding: 8px 12px;
            border-radius: 8px;
            display: inline-block;
            max-width: 70%;
            word-wrap: break-word;
        }

        .message.own {
            text-align: right;
        }

        .message.own .message-content {
            background: #3498db;
            color: white;
        }

        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }

        .input-area input {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }

        .input-area button {
            padding: 12px 24px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }

        .input-area button:hover {
            background: #2980b9;
        }

        .status {
            padding: 8px 20px;
            background: #ecf0f1;
            font-size: 12px;
            color: #2c3e50;
            border-top: 1px solid #ddd;
        }

        .online-count {
            font-size: 11px;
            color: #1abc9c;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="user-info">
                <h3>Ваш ID</h3>
                <div class="user-id" id="clientId">Загрузка...</div>
                <div class="online-count" id="onlineCount">👥 0 онлайн</div>
            </div>
            <div class="rooms-section">
                <h3>Комнаты</h3>
                <div class="room-item active" data-room="general"># general</div>
                <div class="room-item" data-room="random"># random</div>
                <div class="room-item" data-room="tech"># tech</div>

                <div class="users-list">
                    <h3>Пользователи онлайн</h3>
                    <div id="usersList">Загрузка...</div>
                </div>
            </div>
        </div>

        <div class="chat-area">
            <div class="chat-header">
                <h2 id="currentRoom">general</h2>
                <p>WebSocket + WebRTC Чат</p>
            </div>

            <div class="video-area" id="videoArea">
                <div class="videos-container" id="videosContainer"></div>
                <div class="call-controls">
                    <button class="call-btn-large" id="endCallBtn" style="display: none;">Завершить звонок</button>
                </div>
            </div>

            <div class="messages-area" id="messages">
                <div class="message system">
                    <div class="message-content">💬 Добро пожаловать в чат! Начните общение прямо сейчас.</div>
                </div>
            </div>

            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Введите сообщение...">
                <button id="sendBtn">Отправить</button>
            </div>

            <div class="status" id="status">🟡 Подключение к серверу...</div>
        </div>
    </div>

    <script>
        // Глобальные переменные
        let ws = null;
        let clientId = localStorage.getItem('clientId') || 'user_' + Math.random().toString(36).substr(2, 8);
        let currentRoom = 'general';

        // DOM элементы
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusDiv = document.getElementById('status');
        const currentRoomSpan = document.getElementById('currentRoom');
        const usersListDiv = document.getElementById('usersList');
        const onlineCountSpan = document.getElementById('onlineCount');
        const videoArea = document.getElementById('videoArea');
        const endCallBtn = document.getElementById('endCallBtn');
        const videosContainer = document.getElementById('videosContainer');

        // Сохраняем ID
        localStorage.setItem('clientId', clientId);
        document.getElementById('clientId').textContent = clientId;

        // Получение WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}`;

        console.log('Client ID:', clientId);
        console.log('WebSocket URL:', wsUrl);

        // Подключение к WebSocket
        function connectWebSocket() {
            const url = `${wsUrl}/ws/${clientId}/${currentRoom}`;
            console.log('Connecting to:', url);

            try {
                ws = new WebSocket(url);

                ws.onopen = () => {
                    console.log('✅ WebSocket connected');
                    statusDiv.innerHTML = '✅ Подключен к чату';
                    statusDiv.style.background = '#d4edda';
                    statusDiv.style.color = '#155724';
                    addSystemMessage('Подключение к серверу установлено');
                };

                ws.onmessage = (event) => {
                    console.log('📨 Received:', event.data);
                    try {
                        const message = JSON.parse(event.data);
                        handleMessage(message);
                    } catch (e) {
                        console.error('Error parsing message:', e);
                    }
                };

                ws.onclose = () => {
                    console.log('❌ WebSocket disconnected');
                    statusDiv.innerHTML = '❌ Отключен. Переподключение через 3 сек...';
                    statusDiv.style.background = '#f8d7da';
                    statusDiv.style.color = '#721c24';
                    addSystemMessage('Соединение потеряно, переподключение...');
                    setTimeout(() => connectWebSocket(), 3000);
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    statusDiv.innerHTML = '⚠️ Ошибка подключения';
                };
            } catch (error) {
                console.error('Error creating WebSocket:', error);
            }
        }

        // Обработка сообщений
        function handleMessage(message) {
            console.log('Handling message:', message);

            switch(message.type) {
                case 'system':
                    addSystemMessage(message.content);
                    break;

                case 'chat':
                    addChatMessage(message.client_id, message.content, message.timestamp);
                    break;

                default:
                    console.log('Unknown message type:', message.type);
            }

            // Обновляем список пользователей
            fetchUsers();
        }

        // Добавление сообщения в чат
        function addChatMessage(sender, content, timestamp) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender === clientId ? 'own' : ''}`;

            const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            const senderName = sender === clientId ? 'Вы' : escapeHtml(sender);

            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="message-sender">${senderName}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${escapeHtml(content)}</div>
            `;

            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function addSystemMessage(content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message system';
            messageDiv.innerHTML = `<div class="message-content">📢 ${escapeHtml(content)}</div>`;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Отправка сообщения
        function sendMessage() {
            const content = messageInput.value.trim();
            if (!content) return;

            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'chat',
                    content: content
                }));
                messageInput.value = '';
                console.log('Message sent:', content);
            } else {
                addSystemMessage('❌ Нет подключения к серверу');
                console.log('WebSocket not open, state:', ws ? ws.readyState : 'null');
            }
        }

        // Получение списка пользователей
        async function fetchUsers() {
            try {
                const response = await fetch('/rooms');
                const data = await response.json();
                console.log('Rooms data:', data);

                if (data.room_details && data.room_details[currentRoom]) {
                    const users = data.room_details[currentRoom].clients || [];
                    updateUsersList(users);
                    onlineCountSpan.textContent = `👥 ${users.length} онлайн`;
                }
            } catch (error) {
                console.error('Error fetching users:', error);
            }
        }

        // Обновление списка пользователей
        function updateUsersList(users) {
            if (!usersListDiv) return;

            if (users.length === 0) {
                usersListDiv.innerHTML = '<div style="color: #95a5a6; text-align: center;">Нет пользователей</div>';
                return;
            }

            usersListDiv.innerHTML = '';
            users.forEach(user => {
                const userItem = document.createElement('div');
                userItem.className = 'user-item';
                if (user !== clientId) {
                    userItem.innerHTML = `
                        <span>👤 ${escapeHtml(user)}</span>
                        <button class="call-btn" onclick="startCall('${escapeHtml(user)}')">📞 Видеозвонок</button>
                    `;
                } else {
                    userItem.innerHTML = `<span>👤 ${escapeHtml(user)} (Вы)</span>`;
                }
                usersListDiv.appendChild(userItem);
            });
        }

        // WebRTC функции (заглушки для теста)
        async function startCall(targetClientId) {
            addSystemMessage(`📞 Видеозвонок ${targetClientId} (функция в разработке)`);
            alert('Видеозвонки требуют HTTPS. Функция будет доступна после настройки SSL.');
        }

        function endCall() {
            addSystemMessage('🔴 Звонок завершен');
        }

        // Смена комнаты
        function changeRoom(room) {
            if (room === currentRoom) return;

            console.log('Changing room from', currentRoom, 'to', room);
            currentRoom = room;
            currentRoomSpan.textContent = room;

            // Очищаем сообщения
            messagesDiv.innerHTML = '';
            addSystemMessage(`Переход в комнату ${room}...`);

            // Переподключаемся
            if (ws) {
                ws.close();
            }
            connectWebSocket();

            // Обновляем активную комнату в UI
            document.querySelectorAll('.room-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.room === room) {
                    item.classList.add('active');
                }
            });
        }

        // Экранирование HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Инициализация
        function init() {
            console.log('Initializing app...');
            connectWebSocket();

            // Обработчики событий
            sendBtn.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });

            // Обработчики смены комнаты
            document.querySelectorAll('.room-item').forEach(item => {
                item.addEventListener('click', () => changeRoom(item.dataset.room));
            });

            // Запрашиваем список пользователей каждые 5 секунд
            setInterval(fetchUsers, 5000);

            // Первоначальная загрузка
            setTimeout(fetchUsers, 1000);

            console.log('App initialized, clientId:', clientId);
        }

        // Запуск приложения
        init();
    </script>
</body>
</html>
"""


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