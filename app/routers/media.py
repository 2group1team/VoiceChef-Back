from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Recipe, Dish
from app.utils.limits import get_user_limits
from app.utils.media import save_photo, cleanup_old_photo
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes/recipes", tags=["Медиа"])

@router.post("/{recipe_id}/photo",
             summary="Загрузить фото",
             description="Загрузка фотографии для рецепта"
             )
async def upload_photo(
        recipe_id: int,
        photo: UploadFile,
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

        # Проверяем лимиты для не премиум пользователей
        limits = get_user_limits(user.is_premium)
        if not user.is_premium and photo.size > limits["max_photo_size"]:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер фото превышает {limits['max_photo_size']/1024/1024:.1f}MB"
            )

        # Если уже есть фото, удаляем его
        if recipe.photo_url and recipe.photo_url.scalar():
            old_path = recipe.photo_url.scalar().lstrip("/")
            background_tasks.add_task(cleanup_old_photo, old_path)

        # Сохраняем новое фото
        photo_url = await save_photo(photo, recipe_id)
        recipe.photo_url = photo_url
        db.commit()

        return {"photo_url": photo_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке фото"
        )

@router.delete("/{recipe_id}/photo",
               summary="Удалить фото",
               description="Удаление фотографии рецепта"
               )
async def delete_photo(
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

        if recipe.photo_url:
            path = recipe.photo_url.lstrip("/")
            background_tasks.add_task(cleanup_old_photo, path)
            recipe.photo_url = None
            db.commit()

        return {"message": "Фото успешно удалено"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении фото"
        )
