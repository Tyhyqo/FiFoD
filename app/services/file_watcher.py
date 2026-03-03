import logging
from pathlib import PurePosixPath

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
    logger.info("File watcher started: %s", settings.FILE_DIR)
    async for changes in awatch(settings.FILE_DIR):
        logger.info("File changes detected: %s", changes)
        files_cache.invalidate()
        for change_type, path in changes:
            event = _CHANGE_EVENTS.get(change_type, "file_updated")
            name = PurePosixPath(path).name
            await ws_manager.broadcast({"event": event, "name": name})
