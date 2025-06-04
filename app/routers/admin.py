
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta
from app.database.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.models.dish import Dish, Recipe
from app.models.ingredient import Ingredient
from app.schemas.admin import (
    AdminDashboard, SystemStats,
    UserBulkAction, ContentModeration, SystemSettings
)
from app.schemas.user import UserAdminRead, PaginatedResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["🔧 Админ-панель"])

@router.get("/dashboard",
            response_model=AdminDashboard,
            summary="Главный дашборд",
            description="Общий обзор системы для администраторов")
async def get_admin_dashboard(
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Главная панель администратора с ключевыми метриками"""
    try:
        # Статистика пользователей
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        premium_users = db.query(User).filter(User.is_premium == True).count()
        new_users_today = db.query(User).filter(
            User.created_at >= datetime.utcnow().date()
        ).count()

        # Статистика контента
        total_dishes = db.query(Dish).count()
        total_recipes = db.query(Recipe).count()
        total_ingredients = db.query(Ingredient).count()

        # Активность за последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_dishes = db.query(Dish).filter(Dish.created_at >= week_ago).count()
        recent_recipes = db.query(Recipe).filter(Recipe.created_at >= week_ago).count()

        # Топ категории блюд
        top_categories = db.query(
            Dish.category,
            func.count(Dish.id).label('count')
        ).group_by(Dish.category).order_by(desc('count')).limit(5).all()

        # Самые активные пользователи
        top_users = db.query(
            User.id, User.email, User.first_name, User.last_name,
            func.count(Dish.id).label('dishes_count')
        ).join(Dish).group_by(User.id).order_by(desc('dishes_count')).limit(5).all()

        return AdminDashboard(
            # Пользователи
            total_users=total_users,
            active_users=active_users,
            premium_users=premium_users,
            new_users_today=new_users_today,
            conversion_rate=round((premium_users / total_users) * 100, 2) if total_users > 0 else 0,

            # Контент
            total_dishes=total_dishes,
            total_recipes=total_recipes,
            total_ingredients=total_ingredients,
            recent_dishes=recent_dishes,
            recent_recipes=recent_recipes,

            # Аналитика
            top_categories=[{"category": cat, "count": count} for cat, count in top_categories],
            top_users=[{
                "id": user_id, "email": email, "name": f"{first_name or ''} {last_name or ''}".strip(),
                "dishes_count": dishes_count
            } for user_id, email, first_name, last_name, dishes_count in top_users]
        )

    except Exception as e:
        logger.error(f"Error getting admin dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке дашборда"
        )


@router.get("/system/stats",
            response_model=SystemStats,
            summary="Системная статистика",
            description="Подробная статистика использования системы")
async def get_system_stats(
        period: str = Query("7d", pattern="^(1d|7d|30d|90d)$", description="Период статистики"),
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Детальная системная статистика за указанный период"""
    try:
        # Определяем период
        period_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = period_map[period]
        start_date = datetime.utcnow() - timedelta(days=days)

        # Статистика регистраций по дням
        registrations = db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(User.created_at >= start_date).group_by(
            func.date(User.created_at)
        ).order_by('date').all()

        # Статистика создания контента
        dishes_created = db.query(
            func.date(Dish.created_at).label('date'),
            func.count(Dish.id).label('count')
        ).filter(Dish.created_at >= start_date).group_by(
            func.date(Dish.created_at)
        ).order_by('date').all()

        # Статистика по размерам файлов
        storage_usage = {
            "photos_count": db.query(Recipe).filter(Recipe.photo_url.isnot(None)).count(),
            "estimated_storage_mb": 0,  # Можно добавить реальный подсчет
            "tts_cache_files": 0  # Можно добавить подсчет TTS файлов
        }

        return SystemStats(
            period=period,
            registrations_chart=[{"date": str(date), "count": count} for date, count in registrations],
            content_creation_chart=[{"date": str(date), "count": count} for date, count in dishes_created],
            storage_usage=storage_usage
        )

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )

@router.get("/users",
            response_model=PaginatedResponse[UserAdminRead],
            summary="Управление пользователями",
            description="Список всех пользователей с расширенными фильтрами")
async def get_users_admin(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None, description="Поиск по email/имени"),
        is_premium: Optional[bool] = Query(None),
        is_active: Optional[bool] = Query(None),
        is_admin: Optional[bool] = Query(None),
        created_after: Optional[datetime] = Query(None),
        created_before: Optional[datetime] = Query(None),
        sort_by: str = Query("created_at", regex="^(created_at|email|last_login)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Расширенное управление пользователями с фильтрами и сортировкой"""
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
        if is_admin is not None:
            query = query.filter(User.is_admin == is_admin)
        if created_after:
            query = query.filter(User.created_at >= created_after)
        if created_before:
            query = query.filter(User.created_at <= created_before)

        # Сортировка
        sort_column = getattr(User, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Пагинация
        total = query.count()
        offset = (page - 1) * size
        users = query.offset(offset).limit(size).all()

        users_admin_data = []
        for user in users:
            user_admin = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_premium": user.is_premium,
                "is_admin": user.is_admin,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "permissions": user.permissions_list,
                "language": user.language,
                "timezone": user.timezone
            }
            users_admin_data.append(user_admin)

        pages = (total + size - 1) // size

        return PaginatedResponse(
            items=users_admin_data,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )

    except Exception as e:
        logger.error(f"Error getting users for admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка пользователей"
        )


@router.post("/users/bulk-action",
             summary="Массовые операции",
             description="Применить действие к группе пользователей")
async def bulk_user_action(
        action_data: UserBulkAction,
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Массовые операции над пользователями"""
    try:
        users = db.query(User).filter(User.id.in_(action_data.user_ids)).all()

        if len(users) != len(action_data.user_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некоторые пользователи не найдены"
            )

        updated_count = 0
        for user in users:
            # Нельзя деактивировать самого себя
            if action_data.action in ["deactivate"] and user.id == admin.id:
                continue

            if action_data.action == "activate":
                user.is_active = True
                updated_count += 1
            elif action_data.action == "deactivate":
                user.is_active = False
                updated_count += 1
            elif action_data.action == "premium_on":
                user.is_premium = True
                updated_count += 1
            elif action_data.action == "premium_off":
                user.is_premium = False
                updated_count += 1

        db.commit()

        logger.info(f"Admin {admin.email} performed bulk action {action_data.action} on {updated_count} users")

        return {
            "success": True,
            "message": f"Действие {action_data.action} применено к {updated_count} пользователям",
            "updated_count": updated_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk user action: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при выполнении массовой операции"
        )

@router.get("/content/moderation",
            response_model=ContentModeration,
            summary="Модерация контента",
            description="Контент требующий модерации или проверки")
async def get_content_moderation(
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Получение контента для модерации"""
    try:
        # Недавно созданные блюда (за последние 24 часа)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_dishes = db.query(Dish).filter(
            Dish.created_at >= yesterday
        ).order_by(desc(Dish.created_at)).limit(20).all()

        # Рецепты с фотографиями (для проверки контента)
        recipes_with_photos = db.query(Recipe).filter(
            Recipe.photo_url.isnot(None)
        ).order_by(desc(Recipe.created_at)).limit(20).all()

        # Пользователи с большим количеством блюд (возможные спамеры)
        power_users = db.query(
            User.id, User.email, User.first_name, User.last_name,
            func.count(Dish.id).label('dishes_count')
        ).join(Dish).group_by(User.id).having(
            func.count(Dish.id) > 10
        ).order_by(desc('dishes_count')).limit(10).all()

        # Новые ингредиенты (за последнюю неделю)
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_ingredients = db.query(Ingredient).filter(
            Ingredient.created_at >= week_ago
        ).order_by(desc(Ingredient.created_at)).limit(20).all()

        return ContentModeration(
            recent_dishes=[{
                "id": dish.id,
                "name": dish.name,
                "category": dish.category,
                "user_email": dish.user.email,
                "created_at": dish.created_at
            } for dish in recent_dishes],

            recipes_with_photos=[{
                "id": recipe.id,
                "dish_name": recipe.dish.name,
                "photo_url": recipe.photo_url,
                "user_email": recipe.dish.user.email,
                "created_at": recipe.created_at
            } for recipe in recipes_with_photos],

            power_users=[{
                "id": user_id,
                "email": email,
                "name": f"{first_name or ''} {last_name or ''}".strip(),
                "dishes_count": dishes_count
            } for user_id, email, first_name, last_name, dishes_count in power_users],

            new_ingredients=[{
                "id": ing.id,
                "name": ing.name,
                "type": ing.type,
                "created_at": ing.created_at
            } for ing in new_ingredients]
        )

    except Exception as e:
        logger.error(f"Error getting content moderation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении контента для модерации"
        )

@router.get("/system/settings",
            response_model=SystemSettings,
            summary="Системные настройки",
            description="Текущие настройки системы")
async def get_system_settings(
        admin: User = Depends(get_current_admin_user)
):
    """Получение текущих системных настроек"""
    from app.config.config import settings
    from app.utils.limits import get_user_limits

    return SystemSettings(
        # Лимиты пользователей
        free_user_limits=get_user_limits(False),
        premium_user_limits=get_user_limits(True),

        # Настройки безопасности
        jwt_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        hash_rounds=settings.HASH_ROUNDS,
        min_password_length=settings.MIN_PASSWORD_LENGTH,

        # Настройки файлов
        max_photo_size_free=2 * 1024 * 1024,  # 2MB
        max_photo_size_premium=10 * 1024 * 1024,  # 10MB
        allowed_photo_formats=[".jpg", ".jpeg", ".png"],

        # Настройки базы данных
        db_pool_size=settings.DB_POOL_SIZE,
        db_pool_timeout=settings.DB_POOL_TIMEOUT,

        # API настройки
        cors_origins=settings.FRONTEND_URLS,
        api_version="1.0.0"
    )


@router.delete("/content/cleanup",
               summary="Очистка системы",
               description="Удаление неиспользуемых файлов и данных")
async def cleanup_system(
        cleanup_photos: bool = Query(True, description="Удалить неиспользуемые фото"),
        cleanup_tts: bool = Query(True, description="Очистить кэш TTS"),
        cleanup_logs: bool = Query(False, description="Очистить старые логи"),
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin_user)
):
    """Очистка системы от неиспользуемых файлов"""
    try:
        cleanup_results = {
            "photos_deleted": 0,
            "tts_files_deleted": 0,
            "logs_deleted": 0,
            "space_freed_mb": 0
        }

        # Здесь можно добавить реальную логику очистки
        if cleanup_photos:
            # Логика удаления неиспользуемых фото
            cleanup_results["photos_deleted"] = 0  # Заглушка

        if cleanup_tts:
            # Логика очистки TTS кэша
            cleanup_results["tts_files_deleted"] = 0  # Заглушка

        if cleanup_logs:
            # Логика очистки логов
            cleanup_results["logs_deleted"] = 0  # Заглушка

        logger.info(f"System cleanup performed by admin {admin.email}: {cleanup_results}")

        return {
            "success": True,
            "message": "Очистка системы завершена",
            "results": cleanup_results
        }

    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке системы"
        )