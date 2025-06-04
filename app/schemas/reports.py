from pydantic import BaseModel, ConfigDict
from app.models.dish import DishCategory


class DishStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_dishes: int
    total_recipes: int
    favorite_recipes: int


class CategoryStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: DishCategory
    dishes_count: int
    recipes_count: int


class IngredientUsage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    count: int