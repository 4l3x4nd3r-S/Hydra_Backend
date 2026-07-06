from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CrearRegistroPresionRequest(BaseModel):
    punto_presion_id: int
    fecha_hora: datetime
    presion_mca: float
    temperatura_c: Optional[float] = None
    dispositivo_serie: Optional[str] = None


class RegistroPresionResponse(BaseModel):
    id: int
    punto_presion_id: int
    fecha_hora: datetime
    presion_mca: float
    temperatura_c: Optional[float] = None
    dispositivo_serie: Optional[str] = None

    model_config = {"from_attributes": True}


class BulkRegistrosResponse(BaseModel):
    insertados: int
    duplicados_ignorados: int
    total_enviados: int
