from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Recipe, Dish
from app.schemas.dish import RecipeRead
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes/recipes", tags=["Избранное"])


@router.put("/{recipe_id}/favorite",
            summary="Переключить избранное",
            description="Добавление/удаление рецепта из избранного"
            )
async def toggle_favorite(
        recipe_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        recipe = db.query(Recipe).join(Recipe.dish).filter(
            Recipe.id == recipe_id,
            Dish.user_id == int(user.id)
        ).first()
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рецепт не найден"
            )

        recipe.is_favorite = not recipe.is_favorite
        db.commit()

        return {
            "recipe_id": recipe.id,
            "is_favorite": recipe.is_favorite
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при изменении статуса избранного"
        )

@router.get("/favorites",
            response_model=List[RecipeRead],
            summary="Избранные рецепты",
            description="Получение списка избранных рецептов"
            )
async def get_favorites(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        return db.query(Recipe).join(Recipe.dish).filter(
            Dish.user_id == int(user.id),
            Recipe.is_favorite == True
        ).all()

    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении избранных рецептов"
        )
