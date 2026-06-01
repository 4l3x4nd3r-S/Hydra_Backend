from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CrearSensorRequest(BaseModel):
    point_id: str
    sector_id: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class SensorResponse(BaseModel):
    id: str
    point_id: str
    sector_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
