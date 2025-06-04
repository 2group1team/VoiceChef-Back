from pathlib import Path
import time
import threading
import logging
import aiofiles

logger = logging.getLogger(__name__)


class TTSCacheManager:
    def __init__(
            self,
            cache_dir: str = "tts_cache",
            max_size_mb: int = 100,
            max_age_days: int = 7
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size_mb * 1024 * 1024
        self.max_age = max_age_days * 86400
        self.lock = threading.Lock()
        self._total_size = None
        self._last_size_check = 0
        self.SIZE_CHECK_INTERVAL = 300  # 5 минут

    def get_cache_path(self, recipe_id: int, step_number: int) -> Path:
        return self.cache_dir / f"recipe_{recipe_id}_step_{step_number}.mp3"

    def is_cached(self, recipe_id: int, step_number: int) -> bool:
        return self.get_cache_path(recipe_id, step_number).exists()

    def cleanup(self) -> None:
        with self.lock:
            try:
                current_time = time.time()
                total_size = 0

                for file_path in self.cache_dir.glob("*.mp3"):
                    try:
                        stat = file_path.stat()
                        age = current_time - stat.st_mtime

                        if age > self.max_age:
                            file_path.unlink()
                            logger.info(f"Removed old cached file: {file_path}")
                        else:
                            total_size += stat.st_size
                            if total_size > self.max_size:
                                file_path.unlink()
                                total_size -= stat.st_size
                                logger.info(f"Removed cached file due to size limit: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to process cache file: {e}")

                self._total_size = total_size
                self._last_size_check = current_time

            except Exception as e:
                logger.error(f"Cache cleanup failed: {e}")

    def should_cleanup(self) -> bool:
        current_time = time.time()
        if current_time - self._last_size_check > self.SIZE_CHECK_INTERVAL:
            with self.lock:
                self._total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.mp3"))
                self._last_size_check = current_time
        return self._total_size and self._total_size > self.max_size * 0.9

    def store(self, recipe_id: int, step_number: int, audio_data: bytes) -> None:
        try:
            if self.should_cleanup():
                self.cleanup()

            cache_path = self.get_cache_path(recipe_id, step_number)
            with open(cache_path, "wb") as f:
                f.write(audio_data)

        except Exception as e:
            logger.error(f"Failed to store audio in cache: {e}")
            raise

    async def store_async(self, recipe_id: int, step_number: int, audio_data: bytes) -> None:
        try:
            if self.should_cleanup():
                self.cleanup()

            cache_path = self.get_cache_path(recipe_id, step_number)
            async with aiofiles.open(cache_path, "wb") as f:
                await f.write(audio_data)

        except Exception as e:
            logger.error(f"Failed to store audio in cache: {e}")
            raise
