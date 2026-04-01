from fastapi import HTTPException, status
from app.auth.models import create_access_token, decode_access_token
from app.auth.crud import UserCRUD


class AuthHandler:
    """Обработчик аутентификации"""

    @staticmethod
    def login(username: str, password: str) -> dict:
        """Вход пользователя"""
        user = UserCRUD.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль"
            )

        # Создаем токен
        access_token = create_access_token(data={"sub": user.username})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.to_dict()
        }

    @staticmethod
    def register(username: str, email: str, password: str) -> dict:
        """Регистрация пользователя"""
        # Проверяем существует ли пользователь
        existing_user = UserCRUD.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )

        # Проверяем email
        existing_email = UserCRUD.get_user_by_email(email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        # Создаем пользователя
        user = UserCRUD.create_user(username, email, password)

        # Создаем токен
        access_token = create_access_token(data={"sub": user.username})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.to_dict()
        }

    @staticmethod
    def get_current_user(token: str) -> dict:
        """Получение текущего пользователя по токену"""
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или просроченный токен"
            )

        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен"
            )

        user = UserCRUD.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден"
            )

        return user.to_dict()