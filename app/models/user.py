from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy import Integer, String, Boolean, DateTime, Text
from app.database.session import Base
from datetime import datetime, UTC
from typing import Optional, List
import re
import json


class User(Base):
    """
    Модель пользователя.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Настройки пользователя
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    @validates('email')
    def validate_email(self, _, email: str) -> str:
        """Валидация email адреса"""
        if not email or not email.strip():
            raise ValueError("Email не может быть пустым")
        email = email.strip().lower()
        if len(email) > 255:
            raise ValueError("Email не может быть длиннее 255 символов")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Некорректный формат email")
        return email

    @validates('hashed_password')
    def validate_hashed_password(self, _, hashed_password: str) -> str:
        """Валидация хэша пароля"""
        if not hashed_password:
            raise ValueError("Хэш пароля не может быть пустым")
        if len(hashed_password) > 1024:
            raise ValueError("Хэш пароля не может быть длиннее 1024 символов")
        return hashed_password

    @validates('first_name', 'last_name')
    def validate_names(self, key, value: Optional[str]) -> Optional[str]:
        """Валидация имени и фамилии"""
        if value is not None:
            value = value.strip()
            if len(value) == 0:
                return None
            if len(value) > 100:
                raise ValueError(f"{key} не может быть длиннее 100 символов")
            if not re.match(r"^[a-zA-Zа-яА-ЯёЁ\s-]+$", value):
                raise ValueError(f"{key} может содержать только буквы, пробелы и дефисы")
            return value
        return None

    @validates('language')
    def validate_language(self, _, language: str) -> str:
        """Валидация кода языка"""
        allowed_languages = ['ru', 'en', 'es', 'fr', 'de', 'it']
        if language not in allowed_languages:
            raise ValueError(f"Неподдерживаемый язык. Доступны: {', '.join(allowed_languages)}")
        return language

    @property
    def permissions_list(self) -> List[str]:
        """
        Возвращает список прав пользователя.
        """
        if not self.permissions:
            return ["user"]  # базовые права

        try:
            perms = json.loads(self.permissions)
            return perms if isinstance(perms, list) else ["user"]
        except (json.JSONDecodeError, TypeError):
            return ["user"]

    @permissions_list.setter
    def permissions_list(self, permissions: List[str]) -> None:
        """Устанавливает права пользователя"""
        if isinstance(permissions, list):
            self.permissions = json.dumps(permissions)
        else:
            raise ValueError("Права должны быть списком строк")

    @property
    def full_name(self) -> str:
        """Возвращает полное имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0]  # Используем часть email как имя

    @property
    def display_name(self) -> str:
        """Возвращает отображаемое имя для UI"""
        return self.full_name

    @property
    def is_superuser(self) -> bool:
        """Проверяет, является ли пользователь суперпользователем"""
        return self.is_admin and "admin" in self.permissions_list

    def has_permission(self, permission: str) -> bool:
        if not self.is_active:
            return False

        if self.is_admin:
            return True  # Админы имеют все права

        return permission in self.permissions_list

    def add_permission(self, permission: str) -> None:
        """Добавляет право пользователю"""
        current_perms = self.permissions_list
        if permission not in current_perms:
            current_perms.append(permission)
            self.permissions_list = current_perms

    def remove_permission(self, permission: str) -> None:
        """Удаляет право у пользователя"""
        current_perms = self.permissions_list
        if permission in current_perms:
            current_perms.remove(permission)
            self.permissions_list = current_perms

    def update_last_login(self) -> None:
        """Обновляет время последнего входа"""
        self.last_login = datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', is_premium={self.is_premium})>"

    def __str__(self) -> str:
        return f"{self.display_name} ({self.email})"
