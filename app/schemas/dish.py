from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from app.models.dish import DishCategory

class StepCreate(BaseModel):
    description: str = Field(..., min_length=10, max_length=1000)
    duration: int = Field(..., ge=1, le=240, description="Время в минутах (от 1 до 240)")


class StepRead(StepCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RecipeCreate(BaseModel):
    cook_time: int = Field(..., ge=1, le=480, description="Общее время приготовления в минутах")
    cook_method: str = Field(..., min_length=3, max_length=100)
    servings: int = Field(..., ge=1, le=50, description="Количество порций")
    steps: List[StepCreate] = Field(..., min_length=1, max_length=20)
    ingredients: List[int] = Field(..., min_length=1, max_length=30)


class RecipeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cook_time: int
    cook_method: str
    servings: int
    photo_url: Optional[str]
    is_favorite: bool
    steps: List[StepRead]


class DishCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Название блюда")
    category: DishCategory


class DishRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: DishCategory


class DishReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: DishCategory
    photo_url: Optional[str]
    recipe_count: int
    avg_cook_time: int


class RecipeReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_name: str
    cook_time: int
    step_count: int
    photo_url: Optional[str]


class IngredientList(BaseModel):
    ingredients: List[str] = Field(..., min_length=1, max_length=20, description="Список ингредиентов для поиска")


class RecipeSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cook_time: int
    cook_method: str
    servings: int
    photo_url: Optional[str]
    is_favorite: bool
    match_percent: float

