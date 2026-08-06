from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator


class PersonalRequest(BaseModel):
    lider_id: int
    apoyos_ids: List[int] = []
    chofer_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validar_integrantes(self):
        integrantes_lista = [
            self.lider_id,
            *self.apoyos_ids,
            *([self.chofer_id] if self.chofer_id is not None else []),
        ]
        integrantes = set(integrantes_lista)
        if len(integrantes) < 2:
            raise ValueError("La cuadrilla debe tener al menos 2 integrantes distintos.")
        if len(integrantes) != len(integrantes_lista):
            raise ValueError("Una persona no puede ocupar más de un rol en la cuadrilla.")
        return self


class CrearCuadrillaRequest(BaseModel):
    especialidad: str
    personal: PersonalRequest



class ActualizarCuadrillaRequest(BaseModel):
    especialidad: Optional[str] = None
    miembros: Optional[List[dict]] = None


class CuadrillaResponse(BaseModel):
    id: int
    codigo_grupo: str
    especialidad: Optional[str] = None

    model_config = {"from_attributes": True}


class PersonaCuadrilla(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    rol_en_cuadrilla: str
    funcion_visible: str
    es_principal: bool


class CuadrillaDetalleResponse(BaseModel):
    id: int
    codigo_grupo: str
    especialidad: Optional[str] = None
    lider: Optional[PersonaCuadrilla] = None
    apoyos: List[PersonaCuadrilla] = []
    chofer: Optional[PersonaCuadrilla] = None

    model_config = {"from_attributes": True}
