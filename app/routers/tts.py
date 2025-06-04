from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.dish import Recipe, Dish, RecipeStep
from app.utils.tts import generate_tts_for_step, get_tts_cache_path, delete_tts_cache_for_recipe
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["🔊 Озвучка"])


@router.get("/{recipe_id}/tts/step/{step_number}",
            summary="Получить MP3 файл шага",
            description="Возврат MP3 файла для воспроизведения шага рецепта")
async def get_step_audio(
        recipe_id: int,
        step_number: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Получение MP3 файла для конкретного шага рецепта"""
    try:
        # Проверяем доступ к рецепту
        recipe = db.query(Recipe).join(Recipe.dish).filter(
            Recipe.id == recipe_id,
            Dish.user_id == int(user.id)
        ).first()

        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рецепт не найден"
            )

        # Получаем конкретный шаг по порядковому номеру
        step = db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.id).offset(step_number - 1).first()

        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Шаг {step_number} не найден"
            )

        # Генерируем или получаем кешированный файл
        voice_id = f"recipe_{recipe_id}_step_{step_number}"
        cache_path = get_tts_cache_path(step.description, voice_id)

        # Если файл не существует, генерируем его
        if not cache_path.exists():
            logger.info(f"Generating TTS for recipe {recipe_id}, step {step_number}")
            cache_path = await generate_tts_for_step(step.description, voice_id)

        # Проверяем что файл создался
        if not cache_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка генерации аудио файла"
            )

        logger.info(f"Serving TTS file: {cache_path}")

        return FileResponse(
            path=str(cache_path),
            media_type="audio/mpeg",
            filename=f"recipe_{recipe_id}_step_{step_number}.mp3",
            headers={
                "Cache-Control": "public, max-age=3600",  # Кеш на 1 час
                "Accept-Ranges": "bytes"  # Поддержка частичной загрузки
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving TTS file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении аудио файла"
        )


@router.post("/{recipe_id}/tts/generate",
             summary="Генерировать TTS для всех шагов",
             description="Предварительная генерация TTS для всех шагов рецепта")
async def generate_recipe_tts(
        recipe_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Генерация TTS для всех шагов рецепта"""
    try:
        # Проверяем доступ к рецепту
        recipe = db.query(Recipe).join(Recipe.dish).filter(
            Recipe.id == recipe_id,
            Dish.user_id == int(user.id)
        ).first()

        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рецепт не найден"
            )

        # Получаем все шаги рецепта
        steps = db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.id).all()

        if not steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У рецепта нет шагов"
            )

        # Запускаем генерацию в фоне для каждого шага
        generated_count = 0
        for i, step in enumerate(steps, 1):
            voice_id = f"recipe_{recipe_id}_step_{i}"
            cache_path = get_tts_cache_path(step.description, voice_id)

            # Генерируем только если файл не существует
            if not cache_path.exists():
                background_tasks.add_task(
                    generate_tts_for_step,
                    step.description,
                    voice_id
                )
                generated_count += 1

        return {
            "message": "Генерация TTS запущена",
            "recipe_id": recipe_id,
            "total_steps": len(steps),
            "generating_steps": generated_count,
            "cached_steps": len(steps) - generated_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating TTS generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при запуске генерации TTS"
        )


@router.get("/{recipe_id}/tts/status",
            summary="Статус TTS файлов",
            description="Проверка готовности TTS файлов для рецепта")
async def get_tts_status(
        recipe_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Проверка статуса TTS файлов для рецепта"""
    try:
        # Проверяем доступ к рецепту
        recipe = db.query(Recipe).join(Recipe.dish).filter(
            Recipe.id == recipe_id,
            Dish.user_id == int(user.id)
        ).first()

        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рецепт не найден"
            )

        # Получаем все шаги
        steps = db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.id).all()

        # Проверяем статус каждого шага
        steps_status = []
        ready_count = 0

        for i, step in enumerate(steps, 1):
            voice_id = f"recipe_{recipe_id}_step_{i}"
            cache_path = get_tts_cache_path(step.description, voice_id)
            is_ready = cache_path.exists()

            if is_ready:
                ready_count += 1
                file_size = cache_path.stat().st_size if cache_path.exists() else 0
            else:
                file_size = 0

            steps_status.append({
                "step_number": i,
                "description": step.description[:50] + "..." if len(step.description) > 50 else step.description,
                "is_ready": is_ready,
                "file_size": file_size,
                "url": f"/recipes/{recipe_id}/tts/step/{i}" if is_ready else None
            })

        return {
            "recipe_id": recipe_id,
            "total_steps": len(steps),
            "ready_steps": ready_count,
            "completion_percentage": round((ready_count / len(steps)) * 100, 1) if steps else 0,
            "steps": steps_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking TTS status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке статуса TTS"
        )


@router.delete("/{recipe_id}/tts",
               summary="Удалить озвучку",
               description="Удаление всех файлов озвучки для рецепта")
async def delete_recipe_tts(
        recipe_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Удаление всех TTS файлов для рецепта"""
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

        deleted_count = delete_tts_cache_for_recipe(recipe_id)
        return {
            "message": "Озвучка успешно удалена",
            "recipe_id": recipe_id,
            "deleted_files": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting TTS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении озвучки"
        )