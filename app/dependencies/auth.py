import logging
from typing import List, Optional
from functools import wraps
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from app.auth.jwt import decode_access_token
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={
        "admin": "Full access",
        "user": "Normal user access",
        "readonly": "Read-only access"
    }
)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Некорректный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка аутентификации",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_scopes(
        security_scopes: SecurityScopes,
        request: Request,
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        token_scopes = payload.get("scopes", [])

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Некорректный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Проверяем права доступа
        if security_scopes.scopes:
            if not any(scope in token_scopes for scope in security_scopes.scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав доступа",
                    headers={"WWW-Authenticate": f"Bearer scope={','.join(security_scopes.scopes)}"},
                )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(
            f"User {user.email} accessed {request.url.path} "
            f"with scopes {security_scopes.scopes}"
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка аутентификации",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


def check_permissions(required_permissions: List[str]):

    def decorator(func):
        @wraps(func)
        async def wrapper(
                current_user: User = Security(get_current_user_with_scopes),
                *args,
                **kwargs
        ):
            return await func(current_user=current_user, *args, **kwargs)

        return wrapper

    return decorator