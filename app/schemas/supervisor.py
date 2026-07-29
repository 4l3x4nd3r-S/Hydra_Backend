from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TecnicoResponse(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    dni: Optional[str] = None
    celular: Optional[str] = None
    cargo: Optional[str] = None
    cargo_visible: Optional[str] = None
    area: Optional[str] = None
    area_visible: Optional[str] = None
    rol_en_cuadrilla: Optional[str] = None
    funcion_visible: str
    es_principal: bool
    puede_ser_gasfitero: bool
    puede_ser_chofer: bool
    cuadrilla_id: Optional[int] = None
    codigo_cuadrilla: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CrearOrdenServicioRequest(BaseModel):
    reclamo_id: int = Field(..., gt=0, description="ID del reclamo origen")
    cuadrilla_id: int = Field(
        ..., gt=0, description="ID de la cuadrilla asignada"
    )
    supervisor_id: Optional[int] = Field(None, gt=0)

    fecha_programacion: Optional[str] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
