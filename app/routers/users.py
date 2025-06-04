from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin_user
from app.models.user import User
from app.schemas.user import (
    UserRead, UserUpdate, UserAdminRead, PasswordChange,
    APIResponse, PaginatedResponse
)
from app.auth.security import hash_password, verify_password
from app.utils.limits import get_user_limits
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get("/me",
            response_model=UserRead,
            summary="Получить информацию о текущем пользователе",
            description="Возвращает профиль текущего авторизованного пользователя"
            )
async def get_current_user_profile(
        current_user: User = Depends(get_current_user)
):
    """Получение профиля текущего пользователя"""
    return current_user


@router.put("/me",
            response_model=UserRead,
            summary="Обновить профиль",
            description="Обновление профиля текущего пользователя"
            )
async def update_current_user_profile(
        user_data: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обновление профиля пользователя"""
    try:
        # Обновляем только переданные поля
        if user_data.first_name is not None:
            current_user.first_name = user_data.first_name
        if user_data.last_name is not None:
            current_user.last_name = user_data.last_name
        if user_data.language is not None:
            current_user.language = user_data.language

        db.commit()
        db.refresh(current_user)

        logger.info(f"User {current_user.email} updated profile")
        return current_user

    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении профиля"
        )


@router.post("/me/change-password",
             response_model=APIResponse[str],
             summary="Изменить пароль",
             description="Смена пароля текущего пользователя"
             )
async def change_password(
        password_data: PasswordChange,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Смена пароля пользователя"""
    try:
        # Проверяем текущий пароль
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный текущий пароль"
            )

        # Хешируем новый пароль
        new_hashed_password = hash_password(password_data.new_password)
        current_user.hashed_password = new_hashed_password

        db.commit()

        logger.info(f"User {current_user.email} changed password")
        return APIResponse(
            success=True,
            message="Пароль успешно изменен",
            data="Password changed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при смене пароля"
        )


@router.get("/me/limits",
            summary="Получить лимиты пользователя",
            description="Возвращает лимиты текущего пользователя в зависимости от подписки"
            )
async def get_user_limits_info(
        current_user: User = Depends(get_current_user)
):
    """Получение лимитов пользователя"""
    limits = get_user_limits(current_user.is_premium)

    return {
        "user_type": "premium" if current_user.is_premium else "free",
        "limits": limits,
        "user_info": {
            "email": current_user.email,
            "is_premium": current_user.is_premium,
            "created_at": current_user.created_at
        }
    }


@router.post("/me/deactivate",
             response_model=APIResponse[str],
             summary="Деактивировать аккаунт",
             description="Деактивация собственного аккаунта пользователя"
             )
async def deactivate_account(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Деактивация аккаунта пользователя"""
    try:
        current_user.is_active = False
        db.commit()

        logger.info(f"User {current_user.email} deactivated account")
        return APIResponse(
            success=True,
            message="Аккаунт успешно деактивирован",
            data="Account deactivated"
        )

    except Exception as e:
        logger.error(f"Error deactivating account: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при деактивации аккаунта"
        )

@router.get("/",
            response_model=PaginatedResponse[UserAdminRead],
            summary="Список всех пользователей (Админ)",
            description="Получение списка всех пользователей с пагинацией"
            )
async def get_all_users(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        search: Optional[str] = Query(None, description="Поиск по email или имени"),
        is_premium: Optional[bool] = Query(None, description="Фильтр по типу подписки"),
        is_active: Optional[bool] = Query(None, description="Фильтр по статусу активности"),
        db: Session = Depends(get_db),
        admin_user: User = Depends(get_current_admin_user)
):
    """Получение списка всех пользователей (только для админов)"""
    try:
        query = db.query(User)

        # Применяем фильтры
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )

        if is_premium is not None:
            query = query.filter(User.is_premium == is_premium)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # Подсчитываем общее количество
        total = query.count()

        # Применяем пагинацию
        offset = (page - 1) * size
        users = query.offset(offset).limit(size).all()

        # Добавляем permissions_list для каждого пользователя
        users_with_permissions = []
        for user in users:
            user_dict = user.__dict__.copy()
            user_dict['permissions'] = user.permissions_list
            users_with_permissions.append(user_dict)

        pages = (total + size - 1) // size

        return PaginatedResponse(
            items=users_with_permissions,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next = page < pages,
            has_prev=page > 1
        )

    except Exception as e:
        logger.error(f"Error getting users list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка пользователей"
        )


@router.get("/{user_id}",
            response_model=UserAdminRead,
            summary="Получить пользователя по ID (Админ)",
            description="Получение детальной информации о пользователе"
            )
async def get_user_by_id(
        user_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(get_current_admin_user)
):
    """Получение пользователя по ID (только для админов)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Добавляем permissions для отображения
        user_dict = user.__dict__.copy()
        user_dict['permissions'] = user.permissions_list

        return user_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении пользователя"
        )


@router.put("/{user_id}/toggle-premium",
            response_model=APIResponse[UserRead],
            summary="Переключить премиум статус (Админ)",
            description="Активация/деактивация премиум подписки пользователя"
            )
async def toggle_user_premium(
        user_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(get_current_admin_user)
):
    """Переключение премиум статуса пользователя (только для админов)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        user.is_premium = not user.is_premium
        db.commit()
        db.refresh(user)

        action = "activated" if user.is_premium else "deactivated"
        logger.info(f"Admin {admin_user.email} {action} premium for user {user.email}")

        return APIResponse(
            success=True,
            message=f"Премиум статус {'активирован' if user.is_premium else 'деактивирован'}",
            data=user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling premium for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при изменении премиум статуса"
        )


@router.put("/{user_id}/toggle-active",
            response_model=APIResponse[UserRead],
            summary="Переключить активность пользователя (Админ)",
            description="Активация/деактивация пользователя"
            )
async def toggle_user_active(
        user_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(get_current_admin_user)
):
    """Переключение активности пользователя (только для админов)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Нельзя деактивировать самого себя
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя деактивировать собственный аккаунт"
            )

        user.is_active = not user.is_active
        db.commit()
        db.refresh(user)

        action = "activated" if user.is_active else "deactivated"
        logger.info(f"Admin {admin_user.email} {action} user {user.email}")

        return APIResponse(
            success=True,
            message=f"Пользователь {'активирован' if user.is_active else 'деактивирован'}",
            data=user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling active status for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при изменении статуса активности"
        )


@router.get("/stats/overview",
            summary="Статистика пользователей (Админ)",
            description="Общая статистика по пользователям"
            )
async def get_users_stats(
        db: Session = Depends(get_db),
        admin_user: User = Depends(get_current_admin_user)
):
    """Получение статистики пользователей (только для админов)"""
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        premium_users = db.query(User).filter(User.is_premium == True).count()
        verified_users = db.query(User).filter(User.is_verified == True).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "premium_users": premium_users,
            "free_users": total_users - premium_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
            "premium_conversion_rate": round((premium_users / total_users) * 100, 2) if total_users > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting users stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )
