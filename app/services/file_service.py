import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.infrastructure.cache import files_cache

logger = logging.getLogger(__name__)


class FileService:

    async def list_files(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Получить страницу файлов из рабочей директории (FILE_DIR)."""
        cached = files_cache.get()
        if cached is not None:
            return cached[skip : skip + limit]

        all_files = await asyncio.to_thread(self._list_files_sync)
        files_cache.set(all_files)
        return all_files[skip : skip + limit]

    async def file_exists(self, file_name: str) -> bool:
        """Проверить наличие файла в рабочей директории (с защитой от path traversal)."""
        return await asyncio.to_thread(self._file_exists_sync, file_name)

    @staticmethod
    def _list_files_sync() -> list[dict]:
        file_dir = settings.FILE_DIR
        if not os.path.isdir(file_dir):
            return []

        entries = [
            entry
            for entry in os.scandir(file_dir)
            if entry.is_file(follow_symlinks=False)
        ]
        entries.sort(key=lambda e: e.name)

        result = []
        for entry in entries:
            stat = entry.stat()
            result.append(
                {
                    "name": entry.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ),
                }
            )
        return result

    @staticmethod
    def _file_exists_sync(file_name: str) -> bool:
        file_dir = Path(settings.FILE_DIR).resolve()
        target = (file_dir / file_name).resolve()
        if not target.is_relative_to(file_dir):
            logger.warning("Path traversal attempt blocked: %s", file_name)
            return False
        return target.is_file()
