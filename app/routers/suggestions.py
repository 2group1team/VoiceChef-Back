from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Recipe, Dish, RecipeIngredient
from app.schemas.dish import RecipeSuggestion, IngredientList, RecipeRead
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes/recipes", tags=["Подбор рецептов"])

@router.post("/suggest",
             response_model=List[RecipeSuggestion],
             summary="Подбор по ингредиентам",
             description="Поиск рецептов по списку имеющихся ингредиентов"
             )
async def suggest_recipes(
        data: IngredientList,
        min_match: float = Query(0.3, ge=0.0, le=1.0, description="Минимальный процент совпадения"),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        if not data.ingredients:
            return []

        input_names = {i.strip().lower() for i in data.ingredients}
        recipes = db.query(Recipe).join(Dish).filter(
            Dish.user_id == int(user.id)
        ).all()

        results = []
        for recipe in recipes:
            # Получаем ингредиенты рецепта с join для оптимизации
            recipe_ingredients = db.query(RecipeIngredient).join(
                RecipeIngredient.ingredient
            ).filter(
                RecipeIngredient.recipe_id == recipe.id
            ).all()

            ingredient_names = {ri.ingredient.name.lower() for ri in recipe_ingredients}

            if not ingredient_names:
                continue

            score = len(ingredient_names & input_names) / len(ingredient_names)
            if score >= min_match:
                results.append({
                    "id": recipe.id,
                    "cook_time": recipe.cook_time,
                    "cook_method": recipe.cook_method,
                    "servings": recipe.servings,
                    "photo_url": recipe.photo_url,
                    "is_favorite": recipe.is_favorite,
                    "match_percent": round(score, 2)
                })

        return sorted(results, key=lambda x: -x["match_percent"])

    except Exception as e:
        logger.error(f"Error suggesting recipes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при подборе рецептов"
        )

@router.get("/filter",
            response_model=List[RecipeRead],
            summary="Фильтр по ингредиентам",
            description="Поиск рецептов, содержащих все указанные ингредиенты"
            )
async def filter_recipes_by_ingredients(
        ingredients: List[str] = Query(..., description="Список ингредиентов"),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        input_set = {i.strip().lower() for i in ingredients}

        recipes = db.query(Recipe).join(Dish).filter(
            Dish.user_id == user.id
        ).all()

        result = []
        for recipe in recipes:
            # Более эффективный запрос ингредиентов
            recipe_ingredients = db.query(RecipeIngredient).join(
                RecipeIngredient.ingredient
            ).filter(
                RecipeIngredient.recipe_id == recipe.id  # ИСПРАВЛЕНО
            ).all()

            ingredient_names = {ri.ingredient.name.lower() for ri in recipe_ingredients}

            if input_set.issubset(ingredient_names):
                result.append(recipe)

        return result

    except Exception as e:
        logger.error(f"Error filtering recipes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при фильтрации рецептов"
        )
