from pydantic import BaseModel, Field, ConfigDict
from app.models.ingredient import IngredientType

class IngredientCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Название ингредиента"
    )
    type: IngredientType


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: IngredientType

