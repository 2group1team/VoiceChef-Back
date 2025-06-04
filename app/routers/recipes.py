from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Dish, Recipe, RecipeStep, RecipeIngredient
from app.models.ingredient import Ingredient
from app.schemas.dish import RecipeCreate, RecipeRead
from app.utils.limits import get_user_limits
from app.utils.media import cleanup_old_photo
from app.utils.tts import delete_tts_cache_for_recipe
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes", tags=["Рецепты"])

@router.post("/{dish_id}/recipes",
             response_model=RecipeRead,
             status_code=status.HTTP_201_CREATED,
             summary="Добавить рецепт",
             description="Добавление нового рецепта к существующему блюду"
             )
async def add_recipe(
        dish_id: int,
        data: RecipeCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        dish = db.query(Dish).filter(
            Dish.id == dish_id,
            Dish.user_id == int(user.id)
        ).first()
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Блюдо не найдено"
            )

        limits = get_user_limits(user.is_premium)
        count = db.query(Recipe).filter(Recipe.dish_id == dish.id).count()
        if count >= limits["max_recipes_per_dish"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Превышен лимит рецептов для блюда ({limits['max_recipes_per_dish']})"
            )

        recipe = Recipe(
            cook_time=data.cook_time,
            cook_method=data.cook_method,
            servings=data.servings,
            dish_id=dish.id
        )
        db.add(recipe)
        db.flush()

        # Добавляем шаги рецепта
        for step in data.steps:
            db.add(RecipeStep(
                description=step.description.strip(),
                duration=step.duration,
                recipe_id=recipe.id
            ))

        # Добавляем ингредиенты
        for ing_id in data.ingredients:
            ingredient = db.query(Ingredient).filter_by(id=ing_id).first()
            if ingredient:
                db.add(RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    amount=1.0,
                    unit="шт"
                ))

        db.commit()
        db.refresh(recipe)
        return recipe

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding recipe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при добавлении рецепта"
        )

@router.get("/{dish_id}/recipes",
            response_model=List[RecipeRead],
            summary="Получить рецепты блюда",
            description="Получение списка всех рецептов для указанного блюда"
            )
async def get_recipes(
        dish_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        recipes = db.query(Recipe).join(Recipe.dish).filter(
            Dish.id == dish_id,
            Dish.user_id == int(user.id)
        ).all()
        return recipes

    except Exception as e:
        logger.error(f"Error getting recipes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении рецептов"
        )

@router.delete("/recipes/{recipe_id}",
               status_code=status.HTTP_200_OK,
               summary="Удалить рецепт",
               description="Удаление рецепта и связанных с ним данных (фото, озвучка)"
               )
async def delete_recipe(
        recipe_id: int,
        background_tasks: BackgroundTasks,
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

        # Удаляем фото, если есть
        if recipe.photo_url and recipe.photo_url.scalar():
            path = recipe.photo_url.scalar().lstrip("/")
            background_tasks.add_task(cleanup_old_photo, path)

        # Удаляем озвучку
        delete_tts_cache_for_recipe(recipe_id)

        db.delete(recipe)
        db.commit()
        return {"message": "Рецепт успешно удалён"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recipe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении рецепта"
        )
