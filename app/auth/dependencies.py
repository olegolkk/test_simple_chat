from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.auth import AuthHandler

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Зависимость для получения текущего пользователя"""
    token = credentials.credentials
    return AuthHandler.get_current_user(token)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Опциональная зависимость для получения пользователя"""
    try:
        token = credentials.credentials
        return AuthHandler.get_current_user(token)
    except HTTPException:
        return None