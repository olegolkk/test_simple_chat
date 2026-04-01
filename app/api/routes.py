from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth.dependencies import get_current_user
from app.managers import ConnectionManager, WebRTCManager
import os

router = APIRouter()
connection_manager = ConnectionManager()
webrtc_manager = WebRTCManager()


@router.get("/")
async def get_root() -> HTMLResponse:
    """Главная страница"""
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    template_path = os.path.abspath(template_path)

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(html_content)
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: Template not found</h1>", status_code=404)


@router.get("/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


@router.get("/users")
async def get_users():
    """Получить список всех пользователей"""
    from app.auth.crud import UserCRUD
    return UserCRUD.get_all_users()


@router.get("/online")
async def get_online_users():
    """Получить список онлайн пользователей"""
    return {"online_users": connection_manager.get_online_users()}