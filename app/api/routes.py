from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime
from app.managers import ConnectionManager, WebRTCManager

router = APIRouter()

# Глобальные экземпляры менеджеров
connection_manager = ConnectionManager()
webrtc_manager = WebRTCManager()


@router.get("/")
async def get_root() -> HTMLResponse:
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(html_content)


@router.get("/health")
async def health_check() -> dict:
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats")
async def get_stats() -> dict:
    """Статистика сервера"""
    return {
        **connection_manager.get_stats(),
        "webrtc_rooms": webrtc_manager.get_rooms_info()
    }


@router.get("/rooms")
async def get_rooms() -> dict:
    """Список комнат"""
    return {
        "rooms": list(connection_manager.rooms.keys()),
        "room_details": {
            room: {
                "clients_count": len(clients),
                "clients": list(clients)
            } for room, clients in connection_manager.rooms.items()
        }
    }