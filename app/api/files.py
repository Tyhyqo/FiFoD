from fastapi import APIRouter, Depends, Query

from app.db.models import User
from app.dependencies import get_current_user, get_file_service
from app.schemas.file import FileOut
from app.services.file_service import FileService

router = APIRouter()


@router.get("/files", response_model=list[FileOut])
async def get_files(
    _user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Пропустить первые N файлов"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное число файлов в ответе"),
    svc: FileService = Depends(get_file_service),
):
    """Получить список файлов в рабочей директории."""
    return await svc.list_files(skip=skip, limit=limit)
