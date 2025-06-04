from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import Integer, String, ForeignKey, Enum, Text, CheckConstraint, DateTime
from app.database.session import Base
from app.models.ingredient import Ingredient
import enum
from typing import List, Optional
from datetime import datetime, UTC

class DishCategory(str, enum.Enum):
    """Категории блюд"""
    first = "первое"
    second = "второе"
    garnish = "гарнир"

class Dish(Base):

    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[DishCategory] = mapped_column(Enum(DishCategory), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
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

    user = relationship("User", backref="dishes")
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe",
        back_populates="dish",
        cascade="all, delete",
        lazy="selectin"
    )

    @validates('name')
    def validate_name(self, _, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("Название блюда не может быть пустым")
        if len(name) > 100:
            raise ValueError("Название блюда не может быть длиннее 100 символов")
        return name.strip()

class Recipe(Base):

    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint('cook_time > 0', name='check_positive_cook_time'),
        CheckConstraint('servings > 0', name='check_positive_servings'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cook_time: Mapped[int] = mapped_column(Integer, nullable=False)
    cook_method: Mapped[str] = mapped_column(String(200), nullable=False)
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"))
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

    dish: Mapped["Dish"] = relationship("Dish", back_populates="recipes")
    steps: Mapped[List["RecipeStep"]] = relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete",
        order_by="RecipeStep.id",
        lazy="selectin"
    )
    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete",
        lazy="selectin"
    )

    cooking_sessions = relationship(
        "CookingSession",
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=False
    )

    @validates('cook_time', 'servings')
    def validate_positive_numbers(self, _, value: int) -> int:
        if value <= 0:
            raise ValueError("Значение должно быть положительным числом")
        return value

    @validates('cook_method')
    def validate_cook_method(self, _, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Метод приготовления не может быть пустым")
        if len(value) > 200:
            raise ValueError("Метод приготовления не может быть длиннее 200 символов")
        return value.strip()

    @validates('photo_url')
    def validate_photo_url(self, _, value: Optional[str]) -> Optional[str]:
        if value is not None:
            if len(value) > 500:
                raise ValueError("URL фото не может быть длиннее 500 символов")
            if not value.strip():
                return None
            return value.strip()
        return value

class RecipeStep(Base):
    """
    Модель шага рецепта.
    Содержит описание шага и его продолжительность.
    """
    __tablename__ = "recipe_steps"
    __table_args__ = (
        CheckConstraint('duration >= 0', name='check_nonnegative_duration'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
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

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="steps")

    @validates('duration')
    def validate_duration(self, _, value: int) -> int:
        if value < 0:
            raise ValueError("Продолжительность не может быть отрицательной")
        return value

    @validates('description')
    def validate_description(self, _, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Описание шага не может быть пустым")
        return value.strip()

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    amount: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
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

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")

    @validates('amount')
    def validate_amount(self, _, value: float) -> float:
        if value <= 0:
            raise ValueError("Количество ингредиента должно быть положительным числом")
        return value

    @validates('unit')
    def validate_unit(self, _, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Единица измерения не может быть пустой")
        if len(value) > 20:
            raise ValueError("Единица измерения не может быть длиннее 20 символов")
        return value.strip()
