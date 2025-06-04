from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Dish, Recipe, RecipeIngredient
from typing import List, Dict, Any
from app.schemas.reports import DishStats, CategoryStats
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Отчеты"])

@router.get("/stats",
            response_model=DishStats,
            summary="Общая статистика",
            description="Получение общей статистики по блюдам и рецептам"
            )
async def get_statistics(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        dishes_count = db.query(Dish).filter(
            Dish.user_id == int(user.id)
        ).count()

        recipes_count = db.query(Recipe).join(Recipe.dish).filter(
            Dish.user_id == int(user.id)
        ).count()

        favorites_count = db.query(Recipe).join(Recipe.dish).filter(
            Dish.user_id == int(user.id),
            Recipe.is_favorite == True
        ).count()

        return {
            "total_dishes": dishes_count,
            "total_recipes": recipes_count,
            "favorite_recipes": favorites_count
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )

@router.get("/categories",
            response_model=List[CategoryStats],
            summary="Статистика по категориям",
            description="Получение статистики по категориям блюд"
            )
async def get_category_stats(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        stats = []
        categories = db.query(Dish.category).filter(
            Dish.user_id == int(user.id)
        ).distinct().all()

        for (category,) in categories:
            dishes = db.query(Dish).filter(
                Dish.user_id == int(user.id),
                Dish.category == category
            )
            dishes_count = dishes.count()

            recipes_count = db.query(Recipe).join(Recipe.dish).filter(
                Dish.user_id == int(user.id),
                Dish.category == category
            ).count()

            stats.append({
                "category": category,
                "dishes_count": dishes_count,
                "recipes_count": recipes_count
            })

        return sorted(stats, key=lambda x: -x["dishes_count"])

    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики по категориям"
        )

@router.get("/popular_ingredients",
            response_model=List[Dict[str, Any]],
            summary="Популярные ингредиенты",
            description="Список наиболее часто используемых ингредиентов"
            )
async def get_popular_ingredients(
        limit: int = 10,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        ingredients = db.query(
            RecipeIngredient.ingredient_id,
            func.count(RecipeIngredient.ingredient_id).label('count')
        ).join(Recipe).join(Dish).filter(
            Dish.user_id == int(user.id)
        ).group_by(RecipeIngredient.ingredient_id).order_by(
            text('count DESC')
        ).limit(limit).all()

        return [
            {
                "ingredient_id": ing.ingredient_id,
                "count": ing.count
            } for ing in ingredients
        ]

    except Exception as e:
        logger.error(f"Error getting popular ingredients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении популярных ингредиентов"
        )
