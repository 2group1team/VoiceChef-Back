from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict
from datetime import datetime, timedelta, UTC
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.analytics import (
    UserActivity, CookingSession, RecipeRecommendation,
    IngredientPreference, ActivityType
)
from app.models.dish import Recipe, Dish, RecipeIngredient
from app.models.ingredient import Ingredient
from app.schemas.analytics import (
    ActivityCreate, ActivityRead, CookingSessionCreate,
    CookingSessionUpdate, CookingSessionRead, RecommendationRead,
    IngredientPreferenceUpdate, IngredientPreferenceRead,
    UserAnalytics, PersonalizedDashboard, TrendingRecipe
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["📊 Аналитика"])

@router.post("/activity",
             response_model=ActivityRead,
             summary="Записать активность",
             description="Трекинг действий пользователя")
async def track_activity(
        activity: ActivityCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Запись активности пользователя"""
    try:
        # Проверяем доступ к рецепту если указан
        if activity.recipe_id:
            recipe = db.query(Recipe).select_from(Recipe).join(
                Dish, Recipe.dish_id == Dish.id
            ).filter(
                Recipe.id == activity.recipe_id,
                Dish.user_id == user.id
            ).first()
            if not recipe:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Рецепт не найден"
                )

        # Создаем запись активности
        user_activity = UserActivity(
            user_id=user.id,
            recipe_id=activity.recipe_id,
            activity_type=activity.activity_type,
            activity_data=activity.activity_data
        )

        db.add(user_activity)
        db.commit()
        db.refresh(user_activity)

        return user_activity

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при записи активности"
        )

@router.post("/cooking-sessions",
             response_model=CookingSessionRead,
             summary="Начать готовку",
             description="Создание новой сессии готовки")
async def start_cooking_session(
        session_data: CookingSessionCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Начало новой сессии готовки"""
    try:
        # Проверяем доступ к рецепту
        recipe = db.query(Recipe).select_from(Recipe).join(
            Dish, Recipe.dish_id == Dish.id
        ).filter(
            Recipe.id == session_data.recipe_id,
            Dish.user_id == user.id
        ).first()
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рецепт не найден"
            )

        # Создаем сессию готовки
        cooking_session = CookingSession(
            user_id=user.id,
            recipe_id=session_data.recipe_id,
            total_steps=session_data.total_steps
        )

        db.add(cooking_session)

        # Записываем активность
        activity = UserActivity(
            user_id=user.id,
            recipe_id=session_data.recipe_id,
            activity_type=ActivityType.START_COOKING,
            activity_data={"session_type": "cooking", "total_steps": session_data.total_steps}
        )
        db.add(activity)

        db.commit()
        db.refresh(cooking_session)

        return cooking_session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting cooking session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании сессии готовки"
        )


@router.put("/cooking-sessions/{session_id}",
            response_model=CookingSessionRead,
            summary="Обновить сессию готовки",
            description="Обновление прогресса готовки")
async def update_cooking_session(
        session_id: int,
        session_update: CookingSessionUpdate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Обновление сессии готовки"""
    try:
        cooking_session = db.query(CookingSession).filter(
            CookingSession.id == session_id,
            CookingSession.user_id == user.id
        ).first()

        if not cooking_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия готовки не найдена"
            )

        # Обновляем поля
        if session_update.current_step is not None:
            cooking_session.current_step = session_update.current_step

            # Записываем активность завершения шага
            activity = UserActivity(
                user_id=user.id,
                recipe_id=cooking_session.recipe_id,
                activity_type=ActivityType.STEP_COMPLETED,
                activity_data={"step": session_update.current_step, "session_id": session_id}
            )
            db.add(activity)

        if session_update.is_completed is not None:
            cooking_session.is_completed = session_update.is_completed
            if session_update.is_completed:
                cooking_session.completed_at = datetime.now(UTC)

                # Записываем активность завершения готовки
                activity = UserActivity(
                    user_id=user.id,
                    recipe_id=cooking_session.recipe_id,
                    activity_type=ActivityType.COMPLETE_COOKING,
                    activity_data={"session_id": session_id, "total_steps": cooking_session.total_steps}
                )
                db.add(activity)

        if session_update.notes is not None:
            cooking_session.notes = session_update.notes

        if session_update.rating is not None:
            cooking_session.rating = session_update.rating

        db.commit()
        db.refresh(cooking_session)

        return cooking_session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cooking session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении сессии готовки"
        )


@router.get("/cooking-sessions",
            response_model=List[CookingSessionRead],
            summary="История готовки",
            description="Получение истории сессий готовки")
async def get_cooking_history(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        completed_only: bool = Query(False),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Получение истории готовки пользователя"""
    try:
        query = db.query(CookingSession).filter(
            CookingSession.user_id == user.id
        )

        if completed_only:
            query = query.filter(CookingSession.is_completed == True)

        cooking_sessions = query.order_by(
            desc(CookingSession.started_at)
        ).offset(offset).limit(limit).all()

        return cooking_sessions

    except Exception as e:
        logger.error(f"Error getting cooking history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении истории готовки"
        )

@router.get("/recommendations",
            response_model=List[RecommendationRead],
            summary="Персональные рекомендации",
            description="Получение персонализированных рекомендаций на основе ингредиентов")
async def get_recommendations(
        limit: int = Query(10, ge=1, le=20),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Получение персональных рекомендаций на основе анализа ингредиентов"""
    try:
        recommendations = []

        # Анализируем любимые ингредиенты пользователя
        favorite_ingredients = await _get_user_favorite_ingredients(db, user.id)

        # Анализируем любимые категории блюд
        favorite_categories = await _get_user_favorite_categories(db, user.id)

        # Рекомендации на основе ингредиентов
        ingredient_based_recs = await _get_ingredient_based_recommendations(
            db, user.id, favorite_ingredients, limit // 2
        )
        recommendations.extend(ingredient_based_recs)

        # Рекомендации на основе категорий
        if len(recommendations) < limit:
            category_based_recs = await _get_category_based_recommendations(
                db, user.id, favorite_categories, limit - len(recommendations)
            )
            recommendations.extend(category_based_recs)

        # Дополняем общими рекомендациями если нужно
        if len(recommendations) < limit:
            general_recs = await _get_general_recommendations(
                db, user.id, limit - len(recommendations)
            )
            recommendations.extend(general_recs)

        # Сортируем по score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return recommendations[:limit]

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []


async def _get_user_favorite_ingredients(db: Session, user_id: int) -> List[Dict]:
    """Анализ любимых ингредиентов пользователя"""
    try:
        # Ингредиенты из рецептов которые пользователь часто готовит
        cooking_ingredients = db.query(
            Ingredient.id,
            Ingredient.name,
            func.count(CookingSession.id).label('cooking_count')
        ).select_from(CookingSession).join(
            Recipe, CookingSession.recipe_id == Recipe.id
        ).join(
            RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
        ).join(
            Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).filter(
            CookingSession.user_id == user_id,
            CookingSession.is_completed == True
        ).group_by(
            Ingredient.id, Ingredient.name
        ).order_by(desc('cooking_count')).limit(10).all()

        # Ингредиенты из рецептов пользователя (создание рецептов)
        recipe_ingredients = db.query(
            Ingredient.id,
            Ingredient.name,
            func.count(Recipe.id).label('recipe_count')
        ).select_from(Recipe).join(
            Dish, Recipe.dish_id == Dish.id
        ).join(
            RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
        ).join(
            Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).filter(
            Dish.user_id == user_id
        ).group_by(
            Ingredient.id, Ingredient.name
        ).order_by(desc('recipe_count')).limit(10).all()

        # Объединяем и ранжируем ингредиенты
        ingredient_scores = defaultdict(float)

        for ing_id, name, cooking_count in cooking_ingredients:
            ingredient_scores[ing_id] += cooking_count * 2.0  # Готовка важнее

        for ing_id, name, recipe_count in recipe_ingredients:
            ingredient_scores[ing_id] += recipe_count * 1.0  # Создание рецептов

        # Формируем список любимых ингредиентов
        favorite_ingredients = []
        for ing_id, score in sorted(ingredient_scores.items(), key=lambda x: x[1], reverse=True)[:10]:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
            if ingredient:
                favorite_ingredients.append({
                    "id": ing_id,
                    "name": ingredient.name,
                    "score": score,
                    "preference_strength": min(1.0, score / 5.0)  # Нормализуем от 0 до 1
                })

        return favorite_ingredients

    except Exception as e:
        logger.warning(f"Could not analyze favorite ingredients: {e}")
        return []


async def _get_user_favorite_categories(db: Session, user_id: int) -> List[Dict]:
    """Анализ любимых категорий блюд пользователя"""
    try:
        # Категории из истории готовки
        cooking_categories = db.query(
            Dish.category,
            func.count(CookingSession.id).label('cooking_count')
        ).select_from(CookingSession).join(
            Recipe, CookingSession.recipe_id == Recipe.id
        ).join(
            Dish, Recipe.dish_id == Dish.id
        ).filter(
            CookingSession.user_id == user_id,
            CookingSession.is_completed == True
        ).group_by(Dish.category).order_by(desc('cooking_count')).all()

        # Категории из рецептов пользователя
        recipe_categories = db.query(
            Dish.category,
            func.count(Recipe.id).label('recipe_count')
        ).select_from(Recipe).join(
            Dish, Recipe.dish_id == Dish.id
        ).filter(
            Dish.user_id == user_id
        ).group_by(Dish.category).order_by(desc('recipe_count')).all()

        # Объединяем данные
        category_scores = defaultdict(float)

        for category, cooking_count in cooking_categories:
            category_scores[category] += cooking_count * 2.0

        for category, recipe_count in recipe_categories:
            category_scores[category] += recipe_count * 1.0

        # Формируем список любимых категорий
        favorite_categories = []
        for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
            favorite_categories.append({
                "category": category,
                "score": score,
                "preference_strength": min(1.0, score / 5.0)
            })

        return favorite_categories

    except Exception as e:
        logger.warning(f"Could not analyze favorite categories: {e}")
        return []


async def _get_ingredient_based_recommendations(
        db: Session, user_id: int, favorite_ingredients: List[Dict], limit: int
) -> List[Dict]:
    """Рекомендации на основе любимых ингредиентов"""
    recommendations = []

    if not favorite_ingredients:
        return recommendations

    try:
        # Для каждого любимого ингредиента ищем рецепты
        for ingredient_data in favorite_ingredients[:5]:  # Топ-5 ингредиентов
            ingredient_id = ingredient_data["id"]
            ingredient_name = ingredient_data["name"]
            preference_strength = ingredient_data["preference_strength"]

            # Ищем рецепты с этим ингредиентом (включая других пользователей)
            recipes_with_ingredient = db.query(Recipe).join(
                RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
            ).join(
                Dish, Recipe.dish_id == Dish.id
            ).filter(
                RecipeIngredient.ingredient_id == ingredient_id,
                Dish.user_id == user_id  # Пока только свои рецепты
            ).limit(3).all()

            for recipe in recipes_with_ingredient:
                # Проверяем что не дублируем
                if any(r["recipe_id"] == recipe.id for r in recommendations):
                    continue

                # Считаем совпадение ингредиентов
                recipe_ingredients = db.query(RecipeIngredient).filter(
                    RecipeIngredient.recipe_id == recipe.id
                ).all()

                total_ingredients = len(recipe_ingredients)
                matching_ingredients = 0

                for recipe_ing in recipe_ingredients:
                    if any(fav["id"] == recipe_ing.ingredient_id for fav in favorite_ingredients):
                        matching_ingredients += 1

                # Рассчитываем score
                ingredient_match_ratio = matching_ingredients / total_ingredients if total_ingredients > 0 else 0
                base_score = 0.6 + (preference_strength * 0.3) + (ingredient_match_ratio * 0.1)

                recommendations.append({
                    "id": len(recommendations) + 1,
                    "recipe_id": recipe.id,
                    "score": round(base_score, 2),
                    "reason": f"Содержит {ingredient_name} ({matching_ingredients}/{total_ingredients} совпадений ингредиентов)",
                    "created_at": datetime.now(UTC),
                    "recipe_name": recipe.dish.name,
                    "recipe_category": recipe.dish.category.value if hasattr(recipe.dish.category, 'value') else str(
                        recipe.dish.category),
                    "cook_time": recipe.cook_time,
                    "match_details": {
                        "primary_ingredient": ingredient_name,
                        "ingredient_match_ratio": round(ingredient_match_ratio, 2),
                        "matching_ingredients": matching_ingredients,
                        "total_ingredients": total_ingredients
                    }
                })

                if len(recommendations) >= limit:
                    break

            if len(recommendations) >= limit:
                break

        return recommendations

    except Exception as e:
        logger.warning(f"Could not get ingredient-based recommendations: {e}")
        return []


async def _get_category_based_recommendations(
        db: Session, user_id: int, favorite_categories: List[Dict], limit: int
) -> List[Dict]:
    """Рекомендации на основе любимых категорий"""
    recommendations = []

    if not favorite_categories:
        return recommendations

    try:
        for category_data in favorite_categories[:3]:  # Топ-3 категории
            category = category_data["category"]
            preference_strength = category_data["preference_strength"]

            # Ищем рецепты в этой категории
            recipes_in_category = db.query(Recipe).join(
                Dish, Recipe.dish_id == Dish.id
            ).filter(
                Dish.category == category,
                Dish.user_id == user_id
            ).order_by(desc(Recipe.created_at)).limit(2).all()

            for recipe in recipes_in_category:
                # Проверяем дубликаты
                if any(r["recipe_id"] == recipe.id for r in recommendations):
                    continue

                base_score = 0.5 + (preference_strength * 0.3)

                recommendations.append({
                    "id": len(recommendations) + 1,
                    "recipe_id": recipe.id,
                    "score": round(base_score, 2),
                    "reason": f"Вы часто готовите {category}",
                    "created_at": datetime.now(UTC),
                    "recipe_name": recipe.dish.name,
                    "recipe_category": recipe.dish.category.value if hasattr(recipe.dish.category, 'value') else str(
                        recipe.dish.category),
                    "cook_time": recipe.cook_time
                })

                if len(recommendations) >= limit:
                    break

            if len(recommendations) >= limit:
                break

        return recommendations

    except Exception as e:
        logger.warning(f"Could not get category-based recommendations: {e}")
        return []


async def _get_general_recommendations(db: Session, user_id: int, limit: int) -> List[Dict]:
    """Общие рекомендации (fallback)"""
    try:
        # Просто недавние рецепты пользователя
        recent_recipes = db.query(Recipe).join(
            Dish, Recipe.dish_id == Dish.id
        ).filter(
            Dish.user_id == user_id
        ).order_by(desc(Recipe.created_at)).limit(limit).all()

        recommendations = []
        for recipe in recent_recipes:
            recommendations.append({
                "id": len(recommendations) + 1,
                "recipe_id": recipe.id,
                "score": 0.4,
                "reason": "Ваш недавний рецепт",
                "created_at": datetime.now(UTC),
                "recipe_name": recipe.dish.name,
                "recipe_category": recipe.dish.category.value if hasattr(recipe.dish.category, 'value') else str(
                    recipe.dish.category),
                "cook_time": recipe.cook_time
            })

        return recommendations

    except Exception as e:
        logger.warning(f"Could not get general recommendations: {e}")
        return []

@router.get("/ingredient-preferences",
            response_model=List[IngredientPreferenceRead],
            summary="Предпочтения по ингредиентам",
            description="Анализ предпочтений пользователя по ингредиентам")
async def get_ingredient_preferences(
        limit: int = Query(20, ge=1, le=50),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Получение анализа предпочтений по ингредиентам"""
    try:
        favorite_ingredients = await _get_user_favorite_ingredients(db, user.id)

        preferences = []
        for ing_data in favorite_ingredients[:limit]:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ing_data["id"]).first()
            if ingredient:
                preferences.append({
                    "ingredient_id": ingredient.id,
                    "ingredient_name": ingredient.name,
                    "preference_score": min(1.0, ing_data["preference_strength"]),
                    "usage_count": int(ing_data["score"]),
                    "updated_at": datetime.now(UTC)
                })

        return preferences

    except Exception as e:
        logger.error(f"Error getting ingredient preferences: {e}")
        return []

@router.get("/dashboard",
            response_model=PersonalizedDashboard,
            summary="Персональная панель",
            description="Панель с улучшенными рекомендациями и аналитикой")
async def get_personalized_dashboard(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Персонализированная панель с улучшенной аналитикой"""
    try:
        # Получаем улучшенные рекомендации
        recommendations = await get_recommendations(limit=5, db=db, user=user)

        # Недавние сессии готовки
        recent_cooking_sessions = db.query(CookingSession).filter(
            CookingSession.user_id == user.id
        ).order_by(desc(CookingSession.started_at)).limit(5).all()

        # Анализ любимых ингредиентов для достижений
        favorite_ingredients = await _get_user_favorite_ingredients(db, user.id)
        favorite_categories = await _get_user_favorite_categories(db, user.id)

        # Простой подсчет серии готовки
        today = datetime.now(UTC).date()
        cooking_streak = 0

        for days_back in range(7):
            check_date = today - timedelta(days=days_back)
            sessions_count = db.query(CookingSession).filter(
                CookingSession.user_id == user.id,
                func.date(CookingSession.started_at) == check_date,
                CookingSession.is_completed == True
            ).count()

            if sessions_count > 0:
                if days_back == cooking_streak:
                    cooking_streak += 1
                else:
                    break
            else:
                if days_back == 0:
                    break
                elif days_back == cooking_streak:
                    break

        # Статистика за неделю
        week_ago = datetime.now(UTC) - timedelta(days=7)
        weekly_stats = {
            "recipes_cooked": db.query(CookingSession).filter(
                CookingSession.user_id == user.id,
                CookingSession.started_at >= week_ago,
                CookingSession.is_completed == True
            ).count(),
            "favorite_ingredients_count": len(favorite_ingredients),
            "new_recipes": db.query(Recipe).join(Dish).filter(
                Dish.user_id == user.id,
                Recipe.created_at >= week_ago
            ).count()
        }

        # Улучшенные достижения
        achievements = []
        if len(favorite_ingredients) >= 5:
            achievements.append({
                "type": "ingredient_explorer",
                "title": "Исследователь ингредиентов",
                "description": f"Активно использует {len(favorite_ingredients)} разных ингредиентов"
            })

        if cooking_streak >= 3:
            achievements.append({
                "type": "cooking_streak",
                "title": "Серия готовки",
                "description": f"Готовит {cooking_streak} дней подряд!"
            })

        if favorite_categories:
            top_category = favorite_categories[0]["category"]
            achievements.append({
                "type": "category_master",
                "title": f"Мастер категории {top_category}",
                "description": f"Специализируется на приготовлении блюд типа '{top_category}'"
            })

        return PersonalizedDashboard(
            recommended_recipes=recommendations,
            recent_cooking_sessions=recent_cooking_sessions,
            cooking_streak=cooking_streak,
            achievements=achievements,
            weekly_stats=weekly_stats
        )

    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении панели"
        )