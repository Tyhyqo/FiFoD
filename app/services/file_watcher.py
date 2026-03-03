import logging
from pathlib import Path, PurePosixPath

from watchfiles import Change, awatch

from app.config import settings
from app.infrastructure.cache import files_cache
from app.infrastructure.ws_manager import ws_manager

logger = logging.getLogger(__name__)

_CHANGE_EVENTS = {
    Change.added: "file_added",
    Change.modified: "file_modified",
    Change.deleted: "file_deleted",
}


async def watch_files() -> None:
    """Наблюдать за FILE_DIR и уведомлять клиентов при изменениях."""
    watch_dir = str(Path(settings.FILE_DIR).resolve())
    logger.info("File watcher started: %s", watch_dir)
    async for changes in awatch(watch_dir):
        logger.info("File changes detected: %s", changes)
        files_cache.invalidate()
        for change_type, path in changes:
            if str(path) == watch_dir:
                continue
            event = _CHANGE_EVENTS.get(change_type, "file_updated")
            name = PurePosixPath(path).name
            await ws_manager.broadcast({"event": event, "name": name})
