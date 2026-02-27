from pydantic import BaseModel


class DeviceOut(BaseModel):
    serial: str | None
    model: str | None
    version: str | None
    notes: str | None
