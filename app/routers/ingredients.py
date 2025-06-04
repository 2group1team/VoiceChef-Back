from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.user import User
from app.models.ingredient import Ingredient
from app.schemas.ingredient import IngredientCreate, IngredientRead
from app.dependencies.auth import get_current_user
from app.database.session import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ingredients",
    tags=["Ингредиенты"]
)


@router.post("/",
             response_model=IngredientRead,
             summary="Добавить ингредиент",
             description="Создание нового ингредиента в базе данных"
             )
async def create_ingredient(
        data: IngredientCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        existing = db.query(Ingredient).filter(Ingredient.name.ilike(data.name)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Такой ингредиент уже есть"
            )

        ing = Ingredient(name=data.name.strip(), type=data.type)
        db.add(ing)
        db.commit()
        db.refresh(ing)
        return ing

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ingredient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании ингредиента"
        )


@router.get("/",
            response_model=List[IngredientRead],
            summary="Список всех ингредиентов",
            description="Получение списка всех доступных ингредиентов"
            )
async def get_all_ingredients(
        db: Session = Depends(get_db),
        _: User = Depends(get_current_user)
):
    try:
        return db.query(Ingredient).order_by(Ingredient.name).all()
    except Exception as e:
        logger.error(f"Error getting ingredients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка ингредиентов"
        )
