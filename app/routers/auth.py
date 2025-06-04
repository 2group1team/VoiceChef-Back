from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, TokenResponse, UserRead
from app.models.user import User
from app.auth.security import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.database.session import get_db
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies.auth import get_current_user
from typing import Annotated
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создание нового аккаунта пользователя с указанным email и паролем"
)
async def register(
        user_data: UserCreate,
        response: Response,
        db: Annotated[Session, Depends(get_db)]
):
    try:
        email = str(user_data.email)

        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует"
            )

        user = User(
            email=email,
            hashed_password=hash_password(user_data.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response.headers["Location"] = f"/users/{user.id}"
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при регистрации"
        )

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
    description="Аутентификация пользователя и получение JWT токена"
)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[Session, Depends(get_db)]
):
    try:
        username = form_data.username.lower().strip()
        user = db.query(User).filter(User.email == username).first()

        if not user:
            logger.warning(f"Login attempt for non-existent user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Получаем хеш пароля
        stored_hash = user.hashed_password

        logger.info(f"Login attempt for user: {username}")

        if not verify_password(form_data.password, stored_hash):
            logger.warning(f"Invalid password for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if hasattr(user, 'update_last_login'):
            user.update_last_login()
            db.commit()

        # Создаем токен
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(hours=24)
        )

        logger.info(f"Successful login for user: {username}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=24 * 60 * 60,
            user=user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при входе в систему"
        )


@router.post(
    "/subscription/upgrade",
    status_code=status.HTTP_200_OK,
    summary="Активация премиум подписки",
    description="Активация премиум статуса для текущего пользователя"
)
async def upgrade(
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    try:
        if user.is_premium:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Премиум подписка уже активирована"
            )

        user.is_premium = True
        db.commit()
        return {"message": "Премиум подписка успешно активирована"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during premium upgrade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при активации премиум подписки"
        )
