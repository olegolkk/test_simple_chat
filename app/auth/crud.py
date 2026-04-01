from typing import Optional
from app.auth.models import User, users_db


class UserCRUD:
    """CRUD операции с пользователями"""

    @staticmethod
    def create_user(username: str, email: str, password: str) -> Optional[User]:
        """Создание нового пользователя"""
        # Проверка существования пользователя
        if username in users_db:
            return None

        # Создаем пользователя
        user = User(username, email, password)
        users_db[username] = user
        return user

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Получение пользователя по username"""
        return users_db.get(username)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Получение пользователя по email"""
        for user in users_db.values():
            if user.email == email:
                return user
        return None

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = users_db.get(username)
        if not user:
            return None

        if not User.verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    def get_all_users() -> list:
        """Получение всех пользователей"""
        return [user.to_dict() for user in users_db.values()]