from pathlib import Path
import aiofiles
from fastapi import UploadFile
import logging
from uuid import uuid4
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Настройки для медиафайлов
UPLOAD_DIR = Path("uploads/photos")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILENAME_LENGTH = 100
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def save_photo(photo: UploadFile, recipe_id: int) -> str:
    try:
        # Создаем директорию, если её нет
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Проверяем расширение файла
        file_ext = Path(photo.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Неподдерживаемый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")

        # Проверяем размер файла
        content = await photo.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // 1024 // 1024}MB")

        # Генерируем уникальное имя файла
        filename = f"{recipe_id}_{uuid4().hex[:8]}{file_ext}"
        file_path = UPLOAD_DIR / filename

        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)

        # Возвращаем относительный путь для URL
        return urljoin("/", str(file_path))

    except Exception as e:
        logger.error(f"Error saving photo: {e}")
        raise


async def cleanup_old_photo(file_path: str) -> None:
    """
    Удаляет старое фото рецепта.
    """
    try:
        if file_path.startswith('/'):
            file_path = file_path[1:]

        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted old photo: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting old photo {file_path}: {e}")