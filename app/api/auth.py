from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.auth import AuthHandler
from app.database import get_session


router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserSchema(BaseModel):
    username: str
    email: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserSchema


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest,
                session: AsyncSession = Depends(get_session)):
    """Вход в систему"""
    return await AuthHandler.login(session, request.username, request.password)


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest,
                   session: AsyncSession = Depends(get_session)):
    """Регистрация нового пользователя"""
    return await AuthHandler.register(session, request.username, str(request.email), request.password)