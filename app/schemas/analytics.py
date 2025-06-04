from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.models.analytics import ActivityType
import json

class ActivityCreate(BaseModel):
    """Создание записи активности"""
    recipe_id: Optional[int] = None
    activity_type: ActivityType
    activity_data: Optional[Dict[str, Any]] = None


class ActivityRead(BaseModel):
    """Чтение активности"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    recipe_id: Optional[int]
    activity_type: ActivityType
    activity_data: Optional[Dict[str, Any]]
    created_at: datetime

    @classmethod
    @field_validator('activity_data', mode='before')
    def parse_activity_data(cls, v):
        """Парсим JSON строку в словарь если нужно"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

class CookingSessionCreate(BaseModel):
    """Создание сессии готовки"""
    recipe_id: int
    total_steps: int


class CookingSessionUpdate(BaseModel):
    """Обновление сессии готовки"""
    current_step: Optional[int] = None
    is_completed: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    rating: Optional[int] = Field(None, ge=1, le=5)


class CookingSessionRead(BaseModel):
    """Чтение сессии готовки"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    recipe_id: int
    is_completed: bool
    current_step: int
    total_steps: int
    started_at: datetime
    completed_at: Optional[datetime]
    paused_at: Optional[datetime]
    notes: Optional[str]
    rating: Optional[int]

class RecommendationRead(BaseModel):
    """Рекомендация рецепта"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    score: float
    reason: str
    created_at: datetime

    # Данные рецепта
    recipe_name: Optional[str] = None
    recipe_category: Optional[str] = None
    cook_time: Optional[int] = None


class RecommendationInteraction(BaseModel):
    """Взаимодействие с рекомендацией"""
    recommendation_id: int
    action: str = Field(pattern="^(shown|clicked|dismissed)$")

class IngredientPreferenceUpdate(BaseModel):
    """Обновление предпочтений по ингредиенту"""
    ingredient_id: int
    preference_score: float = Field(ge=-1.0, le=1.0)


class IngredientPreferenceRead(BaseModel):
    """Чтение предпочтений"""
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    ingredient_name: str
    preference_score: float
    usage_count: int
    updated_at: datetime

class UserAnalytics(BaseModel):
    """Аналитика пользователя"""
    total_recipes_viewed: int
    total_cooking_sessions: int
    completed_recipes: int
    favorite_category: Optional[str]
    favorite_ingredients: List[str]
    avg_session_duration: Optional[float]  # в минутах
    last_activity: Optional[datetime]


class RecipeAnalytics(BaseModel):
    """Аналитика рецепта"""
    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    recipe_name: str
    views_count: int
    cooking_sessions: int
    completion_rate: float  # процент завершенных сессий
    avg_rating: Optional[float]
    popular_with_age_groups: List[str]
    last_cooked: Optional[datetime]


class TrendingRecipe(BaseModel):
    """Популярный рецепт"""
    recipe_id: int
    recipe_name: str
    category: str
    trend_score: float
    views_last_week: int
    cooking_sessions_last_week: int


class PersonalizedDashboard(BaseModel):
    """Персонализированная панель"""
    recommended_recipes: List[RecommendationRead]
    recent_cooking_sessions: List[CookingSessionRead]
    cooking_streak: int  # дни подряд готовки
    achievements: List[Dict[str, Any]]
    weekly_stats: Dict[str, int]

class CookingInsight(BaseModel):
    """Инсайт о готовке пользователя"""
    type: str  # "streak", "new_ingredient", "category_preference", etc.
    title: str
    description: str
    data: Dict[str, Any]
    created_at: datetime


class WeeklyReport(BaseModel):
    """Еженедельный отчет"""
    week_start: datetime
    recipes_cooked: int
    new_recipes_tried: int
    favorite_category_this_week: Optional[str]
    cooking_time_minutes: int
    most_used_ingredients: List[str]
    achievements_unlocked: List[str]