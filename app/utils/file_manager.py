from pathlib import Path
import shutil
import time
from typing import Optional
from fastapi import UploadFile, HTTPException
import magic


class FileManager:
    def __init__(
            self,
            base_dir: str = "media",
            max_file_size_mb: int = 2,
            allowed_types: Optional[set] = None
    ):
        self.base_dir = Path(base_dir)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.allowed_types = allowed_types or {"image/jpeg", "image/png"}
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile, subfolder: str) -> str:
        """Сохраняет файл с проверками и возвращает путь"""
        async with file.file as f:
            content = await f.read()

        if len(content) > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {self.max_file_size // 1024 // 1024}MB"
            )

        mime_type = magic.from_buffer(content, mime=True)
        if mime_type not in self.allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {mime_type} not allowed"
            )

        total, used, free = shutil.disk_usage(self.base_dir)
        if len(content) > free * 0.9:
            raise HTTPException(
                status_code=507,
                detail="Insufficient storage space"
            )

        save_dir = self.base_dir / subfolder
        save_dir.mkdir(exist_ok=True)
        file_path = save_dir / f"{time.time_ns()}_{file.filename}"

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path.relative_to(self.base_dir))

    def clean_old_files(self, max_age_days: int = 7):
        """Удаляет старые файлы"""
        current_time = time.time()
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                age = current_time - file_path.stat().st_mtime
                if age > max_age_days * 86400:
                    file_path.unlink()
