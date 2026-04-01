from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.auth.auth import AuthHandler

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Вход в систему"""
    return AuthHandler.login(request.username, request.password)


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Регистрация нового пользователя"""
    return AuthHandler.register(request.username, request.email, request.password)