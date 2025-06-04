import hashlib
import asyncio
import logging
from fastapi import HTTPException, status
from gtts import gTTS
import pyttsx3
from pathlib import Path
import socket

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache/tts")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def internet_available(host="8.8.8.8", port=53, timeout=1) -> bool:
    """Проверка доступности интернета"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


def get_tts_cache_path(text: str, voice: str) -> Path:
    # Создаем хэш из текста и голоса для уникального имени файла
    content_hash = hashlib.md5(f"{text}_{voice}".encode()).hexdigest()
    return CACHE_DIR / f"{content_hash}.mp3"


async def generate_tts_for_step(text: str, voice: str = "default") -> Path:
    # Получаем путь к кэшированному файлу
    cache_path = get_tts_cache_path(text, voice)

    # Если файл уже существует в кэше, возвращаем его
    if cache_path.exists():
        logger.info(f"TTS file found in cache: {cache_path}")
        return cache_path

    try:
        logger.info(f"Generating TTS for text: {text[:50]}...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _generate_tts_sync, text, cache_path)

        if cache_path.exists():
            logger.info(f"TTS generated successfully: {cache_path}")
            return cache_path
        else:
            raise Exception("TTS file was not created")

    except Exception as e:
        logger.error(f"Error generating TTS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка генерации TTS: {str(e)}"
        )


def _generate_tts_sync(text: str, cache_path: Path) -> None:
    """Синхронная генерация TTS (для выполнения в executor)"""
    try:
        if internet_available():
            # Пробуем gTTS (требует интернет)
            logger.info("Using gTTS (online)")
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(str(cache_path))
        else:
            # Fallback на pyttsx3 (оффлайн)
            logger.info("Using pyttsx3 (offline)")
            engine = pyttsx3.init()

            # Настройки голоса
            voices = engine.getProperty('voices')
            if voices:
                # Ищем русский голос
                for voice in voices:
                    if 'ru' in voice.id.lower() or 'russian' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break

            engine.setProperty('rate', 150)  # Скорость речи
            engine.setProperty('volume', 0.9)  # Громкость

            engine.save_to_file(text, str(cache_path))
            engine.runAndWait()

    except Exception as e:
        logger.error(f"Error in sync TTS generation: {e}")
        raise


def delete_tts_cache_for_recipe(recipe_id: int) -> int:
    deleted_count = 0
    pattern = f"recipe_{recipe_id}_step_"

    try:
        for file_path in CACHE_DIR.glob("*.mp3"):
            # Проверяем содержимое файла по хешу
            if pattern in file_path.stem:
                file_path.unlink()
                deleted_count += 1
                logger.info(f"Deleted TTS file: {file_path}")

    except Exception as e:
        logger.error(f"Error deleting TTS cache for recipe {recipe_id}: {e}")

    return deleted_count


def cleanup_old_tts_cache(max_age_days: int = 7) -> int:
    import time

    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60

    try:
        for file_path in CACHE_DIR.glob("*.mp3"):
            if current_time - file_path.stat().st_mtime > max_age_seconds:
                file_path.unlink()
                deleted_count += 1
                logger.info(f"Deleted old TTS file: {file_path}")

    except Exception as e:
        logger.error(f"Error cleaning up old TTS cache: {e}")

    return deleted_count