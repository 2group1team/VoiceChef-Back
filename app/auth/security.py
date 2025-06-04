import warnings
from typing import Union
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import settings

warnings.filterwarnings("ignore", message=".*trapped.*bcrypt.*")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.HASH_ROUNDS,
)


def hash_password(password: str) -> Union[str, None]:
    """
    Хеширует пароль с использованием bcrypt

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хешированный пароль

    Raises:
        HTTPException: Если возникла ошибка при хешировании
    """
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )

    try:
        return pwd_context.hash(password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error hashing password: {str(e)}"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля его хешу

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хешированный пароль

    Returns:
        bool: True если пароль верный, False если нет

    Raises:
        HTTPException: Если возникла ошибка при проверке
    """
    if not plain_password or not hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and hash must not be empty"
        )

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying password: {str(e)}"
        )


def check_password_strength(password: str) -> bool:
    """
    Проверяет надежность пароля

    Args:
        password: Пароль для проверки

    Returns:
        bool: True если пароль удовлетворяет требованиям

    Raises:
        HTTPException: Если пароль не соответствует требованиям
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"
        )

    if not any(char.isupper() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )

    if not any(char.islower() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )

    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )

    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )

    return True
