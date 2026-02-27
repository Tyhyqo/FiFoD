from fastapi import APIRouter, Depends

from app.dependencies import get_device_service
from app.schemas.device import DeviceOut
from app.services.device_service import DeviceService

router = APIRouter()


@router.get("/devices", response_model=list[DeviceOut])
async def get_devices(svc: DeviceService = Depends(get_device_service)):
    """Получить список свободных устройств из внешнего API."""
    return await svc.get_free_devices()
