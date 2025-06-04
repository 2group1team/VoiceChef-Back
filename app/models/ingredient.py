from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy import String, Integer, Enum, DateTime
from app.database.session import Base
import enum
from datetime import datetime, UTC

class IngredientType(str, enum.Enum):
    meat = "мясо"
    fish = "рыба"
    vegetable = "овощ"
    fruit = "фрукт"
    dairy = "молочное"
    other = "другое"

class Ingredient(Base):

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[IngredientType] = mapped_column(Enum(IngredientType), nullable=False)
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

    @validates('name')
    def validate_name(self, _, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("Название ингредиента не может быть пустым")
        if len(name) > 100:
            raise ValueError("Название ингредиента не может быть длиннее 100 символов")
        return name.strip()
