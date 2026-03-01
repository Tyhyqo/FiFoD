from fastapi import APIRouter, Depends, Query

from app.dependencies import get_attachment_service
from app.schemas.attachment import AttachmentCreateIn, AttachmentOut
from app.services.attachment_service import AttachmentService

router = APIRouter()


@router.post("/attachments", response_model=AttachmentOut, status_code=201)
async def create_attachment(
    body: AttachmentCreateIn,
    svc: AttachmentService = Depends(get_attachment_service),
):
    """Создать привязку файлов к устройству."""
    return await svc.create(body.deviceId, body.fileNames)


@router.get("/attachments", response_model=list[AttachmentOut])
async def list_attachments(
    skip: int = Query(0, ge=0, description="Пропустить первые N привязок"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное число привязок в ответе"),
    svc: AttachmentService = Depends(get_attachment_service),
):
    """Получить список всех привязок."""
    return await svc.get_all(skip=skip, limit=limit)
