from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Dish, DishCategory
from app.schemas.dish import DishCreate, DishRead
from app.utils.limits import get_user_limits
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes", tags=["Блюда"])

@router.post("/",
             response_model=DishRead,
             status_code=status.HTTP_201_CREATED,
             summary="Создать блюдо",
             description="Создание нового блюда с указанным названием и категорией"
             )
async def create_dish(
        data: DishCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        limits = get_user_limits(user.is_premium)
        count = db.query(Dish).filter(Dish.user_id == int(user.id)).count()
        if count >= limits["max_dishes"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Превышен лимит блюд ({limits['max_dishes']})"
            )

        dish = Dish(
            name=data.name.strip(),
            category=data.category,
            user_id=int(user.id)
        )
        db.add(dish)
        db.commit()
        db.refresh(dish)
        return dish

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dish: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании блюда"
        )

@router.get("/",
            response_model=List[DishRead],
            summary="Получить список блюд",
            description="Получение списка блюд с возможностью фильтрации по категории и поиска по названию"
            )
async def get_dishes(
        category: Optional[DishCategory] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    try:
        query = db.query(Dish).filter(Dish.user_id == int(user.id))

        if category:
            query = query.filter(Dish.category == category)
        if search:
            search = search.strip()
            query = query.filter(Dish.name.ilike(f"%{search}%"))

        return query.all()

    except Exception as e:
        logger.error(f"Error getting dishes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка блюд"
        )
