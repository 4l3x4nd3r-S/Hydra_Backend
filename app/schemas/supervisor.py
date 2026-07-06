from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TecnicoResponse(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    cargo: Optional[str] = None
    area: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CrearOrdenServicioRequest(BaseModel):
    reclamo_id: int = Field(..., gt=0, description="ID del reclamo origen")
    cuadrilla_id: Optional[int] = Field(
        None, gt=0, description="ID de la cuadrilla asignada"
    )
    supervisor_id: Optional[int] = Field(None, gt=0)
    sector_id: Optional[int] = Field(None, gt=0)
    fecha_programacion: Optional[str] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
