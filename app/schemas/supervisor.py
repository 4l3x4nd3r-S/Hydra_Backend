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
    cuadrilla_id: Optional[int] = Field(
        None, gt=0, description="ID de la cuadrilla asignada"
    )
    responsable_id: Optional[int] = Field(
        None, gt=0, description="ID del gasfitero asignado (asignacion individual a una persona)"
    )
    supervisor_id: Optional[int] = Field(None, gt=0)
    sector_id: Optional[int] = Field(None, gt=0)
    fecha_programacion: Optional[str] = None

    @model_validator(mode="after")
    def validar_modo_asignacion(self):
        if (self.cuadrilla_id is not None) == (self.responsable_id is not None):
            raise ValueError(
                "Debe asignarse a una cuadrilla o a un responsable individual, pero no a ambos."
            )
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
