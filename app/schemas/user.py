from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime

DataT = TypeVar('DataT')

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль (минимум 8 символов)"
    )
    first_name: Optional[str] = Field(None, max_length=100, description="Имя")
    last_name: Optional[str] = Field(None, max_length=100, description="Фамилия")
    language: str = Field("ru", description="Предпочитаемый язык")

    @classmethod
    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        """Проверка сложности пароля"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        return v


class UserRead(BaseModel):
    """Схема для чтения информации о пользователе"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_premium: bool
    is_active: bool
    is_verified: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    language: str
    created_at: datetime
    last_login: Optional[datetime] = None


class UserUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, description="Код языка")


class UserAdminRead(UserRead):
    """Расширенная схема для админов"""
    is_admin: bool
    permissions: List[str]
    timezone: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class PasswordChange(BaseModel):
    """Схема для смены пароля"""
    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль"
    )

    @classmethod
    @field_validator('new_password')
    def validate_password(cls, v: str) -> str:
        """Проверка сложности нового пароля"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        return v

class APIResponse(BaseModel, Generic[DataT]):
    """Базовая схема ответа API"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[DataT] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Схема для пагинированных ответов"""
    items: List[DataT]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool


class ErrorResponse(BaseModel):
    """Схема для ошибок"""
    success: bool = False
    message: str
    errors: Optional[List[str]] = None
    error_code: Optional[str] = None

class UserStats(BaseModel):
    """Статистика пользователя"""
    total_dishes: int
    total_recipes: int
    favorite_recipes: int
    premium_since: Optional[datetime]
    last_activity: Optional[datetime]


class UserLimits(BaseModel):
    """Лимиты пользователя"""
    user_type: str
    max_dishes: int
    max_recipes_per_dish: int
    max_photo_size: int
    can_use_premium_tts: bool
    max_ingredients_per_recipe: int
    can_export_recipes: bool


class EmailVerification(BaseModel):
    """Схема для верификации email"""
    email: EmailStr
    verification_code: str = Field(..., min_length=6, max_length=6)


class PasswordReset(BaseModel):
    """Схема для сброса пароля"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Подтверждение сброса пароля"""
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @classmethod
    @field_validator('new_password')
    def validate_password(cls, v: str) -> str:
        """Проверка сложности пароля"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        return v