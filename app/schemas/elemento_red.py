from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CrearElementoRedRequest(BaseModel):
    codigo_plano: Optional[str] = None
    tipo: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None
    estado_operativo: Optional[str] = None
    estado_valvula: Optional[str] = None
    fecha_modificacion: Optional[datetime] = None


class ActualizarElementoRedRequest(BaseModel):
    codigo_plano: Optional[str] = None
    tipo: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None
    estado_operativo: Optional[str] = None
    estado_valvula: Optional[str] = None
    fecha_modificacion: Optional[datetime] = None


class ElementoRedResponse(BaseModel):
    id: int
    codigo_plano: Optional[str] = None
    tipo: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None
    estado_operativo: Optional[str] = None
    estado_valvula: Optional[str] = None
    fecha_modificacion: Optional[datetime] = None

    model_config = {"from_attributes": True}
