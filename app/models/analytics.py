from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, DateTime, Float, Text, Boolean, JSON
from app.database.session import Base
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import enum
import json


class ActivityType(str, enum.Enum):
    VIEW_RECIPE = "view_recipe"
    START_COOKING = "start_cooking"
    COMPLETE_COOKING = "complete_cooking"
    PAUSE_COOKING = "pause_cooking"
    STEP_COMPLETED = "step_completed"
    TTS_PLAYED = "tts_played"
    PHOTO_TAKEN = "photo_taken"
    RECIPE_SHARED = "recipe_shared"
    INGREDIENT_SEARCHED = "ingredient_searched"


class UserActivity(Base):
    __tablename__ = "user_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    activity_type: Mapped[ActivityType] = mapped_column()

    # ИСПРАВЛЕНО: переименовано metadata -> activity_data
    activity_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Отношения
    user = relationship("User", backref="activities")
    recipe = relationship("Recipe", backref="activities")

    @property
    def activity_data_dict(self) -> Optional[Dict[str, Any]]:
        if isinstance(self.activity_data, str):
            try:
                return json.loads(self.activity_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return self.activity_data


class CookingSession(Base):
    __tablename__ = "cooking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    # Статус сессии
    is_completed: Mapped[bool] = mapped_column(default=False)
    current_step: Mapped[int] = mapped_column(default=1)
    total_steps: Mapped[int] = mapped_column()

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Дополнительная информация
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(nullable=True)  # 1-5 звезд

    # Отношения
    user = relationship("User", backref="cooking_sessions")
    recipe = relationship("Recipe", back_populates="cooking_sessions")


class RecipeRecommendation(Base):
    """Персональные рекомендации"""
    __tablename__ = "recipe_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    score: Mapped[float] = mapped_column(Float)

    reason: Mapped[str] = mapped_column(String(200))

    is_shown: Mapped[bool] = mapped_column(default=False)
    is_clicked: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    user = relationship("User", backref="recommendations")
    recipe = relationship("Recipe", backref="recommendations")


class IngredientPreference(Base):
    """Предпочтения пользователей по ингредиентам"""
    __tablename__ = "ingredient_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"))

    # Скор предпочтения (-1.0 до 1.0: -1 не нравится, 0 нейтрально, 1 нравится)
    preference_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Количество раз использовал ингредиент
    usage_count: Mapped[int] = mapped_column(default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Отношения
    user = relationship("User", backref="ingredient_preferences")
    ingredient = relationship("Ingredient", backref="user_preferences")