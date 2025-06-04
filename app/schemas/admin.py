from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.models.dish import DishCategory
from app.models.ingredient import IngredientType

class AdminDashboard(BaseModel):
    """Главный дашборд администратора"""
    model_config = ConfigDict(from_attributes=True)

    # Статистика пользователей
    total_users: int
    active_users: int
    premium_users: int
    new_users_today: int
    conversion_rate: float = Field(description="Процент премиум пользователей")

    # Статистика контента
    total_dishes: int
    total_recipes: int
    total_ingredients: int
    recent_dishes: int = Field(description="Блюда за неделю")
    recent_recipes: int = Field(description="Рецепты за неделю")

    # Топ данные
    top_categories: List[Dict[str, Any]] = Field(description="Популярные категории")
    top_users: List[Dict[str, Any]] = Field(description="Самые активные пользователи")


class SystemStats(BaseModel):
    """Системная статистика за период"""
    model_config = ConfigDict(from_attributes=True)

    period: str = Field(description="Период статистики (1d, 7d, 30d, 90d)")
    registrations_chart: List[Dict[str, Any]] = Field(description="График регистраций")
    content_creation_chart: List[Dict[str, Any]] = Field(description="График создания контента")
    storage_usage: Dict[str, Any] = Field(description="Использование хранилища")

class UserBulkAction(BaseModel):
    """Массовые операции над пользователями"""
    user_ids: List[int] = Field(..., min_length=1, max_length=100, description="ID пользователей")
    action: str = Field(..., pattern="^(activate|deactivate|premium_on|premium_off)$", description="Действие")


class UserManagement(BaseModel):
    """Расширенная информация о пользователе для админов"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_premium: bool
    is_admin: bool
    is_verified: bool

    # Статистика активности
    dishes_count: int = 0
    recipes_count: int = 0
    favorite_recipes_count: int = 0

    # Временные метки
    created_at: datetime
    last_login: Optional[datetime]

    # Дополнительная информация
    permissions: List[str] = []
    language: str = "ru"
    timezone: str = "UTC"

class ContentModeration(BaseModel):
    """Контент для модерации"""
    model_config = ConfigDict(from_attributes=True)

    recent_dishes: List[Dict[str, Any]] = Field(description="Недавно созданные блюда")
    recipes_with_photos: List[Dict[str, Any]] = Field(description="Рецепты с фотографиями")
    power_users: List[Dict[str, Any]] = Field(description="Очень активные пользователи")
    new_ingredients: List[Dict[str, Any]] = Field(description="Новые ингредиенты")


class ModerationAction(BaseModel):
    """Действие модератора"""
    content_type: str = Field(..., pattern="^(dish|recipe|user|ingredient)$")
    content_id: int
    action: str = Field(..., pattern="^(approve|reject|hide|delete)$")
    reason: Optional[str] = Field(None, max_length=500, description="Причина действия")

class SystemSettings(BaseModel):
    """Системные настройки"""
    model_config = ConfigDict(from_attributes=True)

    # Лимиты пользователей
    free_user_limits: Dict[str, Any]
    premium_user_limits: Dict[str, Any]

    # Безопасность
    jwt_expire_minutes: int
    hash_rounds: int
    min_password_length: int

    # Файлы
    max_photo_size_free: int
    max_photo_size_premium: int
    allowed_photo_formats: List[str]

    # База данных
    db_pool_size: int
    db_pool_timeout: int

    # API
    cors_origins: List[str]
    api_version: str


class SystemSettingsUpdate(BaseModel):
    """Обновление системных настроек"""
    # Лимиты
    max_dishes_free: Optional[int] = Field(None, ge=1, le=100)
    max_dishes_premium: Optional[int] = Field(None, ge=1, le=1000)
    max_recipes_per_dish_free: Optional[int] = Field(None, ge=1, le=10)
    max_recipes_per_dish_premium: Optional[int] = Field(None, ge=1, le=20)

    # Безопасность
    jwt_expire_minutes: Optional[int] = Field(None, ge=60, le=10080)  # 1 час - 7 дней
    min_password_length: Optional[int] = Field(None, ge=6, le=32)

    # Файлы
    max_photo_size_free_mb: Optional[int] = Field(None, ge=1, le=10)
    max_photo_size_premium_mb: Optional[int] = Field(None, ge=1, le=50)

class AnalyticsReport(BaseModel):
    """Отчет по аналитике"""
    model_config = ConfigDict(from_attributes=True)

    period: str
    start_date: datetime
    end_date: datetime

    # Пользователи
    new_registrations: int
    active_users: int
    premium_conversions: int

    # Контент
    new_dishes: int
    new_recipes: int
    photos_uploaded: int
    tts_generations: int

    # Популярное
    top_dish_categories: List[Dict[str, Any]]
    top_ingredients: List[Dict[str, Any]]
    most_active_users: List[Dict[str, Any]]


class ExportRequest(BaseModel):
    """Запрос на экспорт данных"""
    export_type: str = Field(..., pattern="^(users|dishes|recipes|analytics)$")
    format: str = Field("csv", pattern="^(csv|xlsx|json)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None

class SystemAlert(BaseModel):
    """Системное уведомление"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str = Field(pattern="^(info|warning|error|success)$")
    title: str = Field(max_length=100)
    message: str = Field(max_length=500)
    created_at: datetime
    is_read: bool = False
    action_url: Optional[str] = None


class NotificationSettings(BaseModel):
    """Настройки уведомлений"""
    email_notifications: bool = True
    new_user_alerts: bool = True
    system_errors: bool = True
    content_moderation: bool = True
    performance_alerts: bool = True

    # Пороги для алертов
    high_cpu_threshold: int = Field(80, ge=50, le=95)
    high_memory_threshold: int = Field(80, ge=50, le=95)
    error_rate_threshold: float = Field(5.0, ge=1.0, le=20.0)


class SystemHealth(BaseModel):
    """Здоровье системы"""
    model_config = ConfigDict(from_attributes=True)

    # Статус сервисов
    api_status: str = Field(pattern="^(healthy|degraded|down)$")
    database_status: str = Field(pattern="^(healthy|degraded|down)$")
    storage_status: str = Field(pattern="^(healthy|degraded|down)$")

    # Метрики производительности
    response_time_ms: float
    cpu_usage_percent: float
    memory_usage_percent: float
    storage_usage_percent: float

    # Счетчики
    active_connections: int
    requests_per_minute: int
    error_count_last_hour: int

    # Время работы
    uptime_seconds: int
    last_restart: datetime


class PerformanceMetrics(BaseModel):
    """Метрики производительности"""
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime

    # API метрики
    total_requests: int
    successful_requests: int
    error_requests: int
    avg_response_time: float

    # База данных
    db_connections_active: int
    db_connections_idle: int
    slow_queries_count: int

    # Хранилище
    storage_reads_per_sec: int
    storage_writes_per_sec: int
    cache_hit_rate: float

class AuditLog(BaseModel):
    """Запись аудита"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    admin_id: int
    admin_email: str
    action: str = Field(description="Выполненное действие")
    resource_type: str = Field(description="Тип ресурса (user, dish, recipe, etc.)")
    resource_id: Optional[int] = Field(None, description="ID ресурса")
    details: Dict[str, Any] = Field(description="Детали операции")
    ip_address: str
    user_agent: Optional[str] = None


class LogFilter(BaseModel):
    """Фильтр для логов"""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    admin_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    level: Optional[str] = Field(None, pattern="^(info|warning|error|critical)$")


class BackupInfo(BaseModel):
    """Информация о бэкапе"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str = Field(pattern="^(full|incremental|schema_only)$")
    size_mb: float
    created_at: datetime
    status: str = Field(pattern="^(completed|in_progress|failed)$")
    file_path: str
    created_by: str = Field(description="Админ создавший бэкап")


class BackupRequest(BaseModel):
    """Запрос на создание бэкапа"""
    name: str = Field(max_length=100, description="Название бэкапа")
    type: str = Field("full", pattern="^(full|incremental|schema_only)$")
    include_media: bool = Field(True, description="Включить медиафайлы")
    include_logs: bool = Field(False, description="Включить логи")


class RestoreRequest(BaseModel):
    """Запрос на восстановление"""
    backup_id: str
    confirm: bool = Field(description="Подтверждение операции")
    restore_media: bool = Field(True, description="Восстановить медиафайлы")
    restore_settings: bool = Field(True, description="Восстановить настройки")

class APIKey(BaseModel):
    """API ключ для интеграций"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(max_length=100, description="Название интеграции")
    key_preview: str = Field(description="Первые/последние символы ключа")
    permissions: List[str] = Field(description="Разрешения ключа")
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    usage_count: int = 0

class APIKeyCreate(BaseModel):
    """Создание API ключа"""
    name: str = Field(max_length=100, description="Название")
    permissions: List[str] = Field(description="Список разрешений")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Срок действия в днях")
    description: Optional[str] = Field(None, max_length=500)

class Migration(BaseModel):
    """Информация о миграции"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    version: str
    status: str = Field(pattern="^(pending|running|completed|failed)$")
    applied_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


class SystemUpdate(BaseModel):
    """Обновление системы"""
    model_config = ConfigDict(from_attributes=True)

    version: str
    release_date: datetime
    description: str
    changes: List[str] = Field(description="Список изменений")
    breaking_changes: List[str] = Field(description="Критичные изменения")
    migration_required: bool = False
    backup_recommended: bool = True