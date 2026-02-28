from datetime import datetime

from pydantic import BaseModel


class FileOut(BaseModel):
    name: str
    size: int
    modified_at: datetime
