from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReclamoHistoricoResponse(BaseModel):
    id: int
    codigo_solicitud: Optional[str] = None
    numero_suministro: Optional[str] = None
    direccion: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    tipo_problema: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    estado: Optional[str] = None

    model_config = {"from_attributes": True}
