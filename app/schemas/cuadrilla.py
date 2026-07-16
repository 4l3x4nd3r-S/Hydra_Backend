from typing import Optional, List, Literal
from pydantic import BaseModel, model_validator


ESPECIALIDAD_CUADRILLA = Literal["Agua", "Desagüe"]


class PersonalRequest(BaseModel):
    lider_id: int
    apoyos_ids: List[int] = []
    chofer_id: Optional[int] = None
    operador_id: Optional[int] = None

    @model_validator(mode="after")
    def validar_integrantes(self):
        integrantes_lista = [
            self.lider_id,
            *self.apoyos_ids,
            *([self.chofer_id] if self.chofer_id is not None else []),
            *([self.operador_id] if self.operador_id is not None else []),
        ]
        integrantes = set(integrantes_lista)
        if len(integrantes) != len(integrantes_lista):
            raise ValueError("Una persona no puede ocupar más de un rol en la cuadrilla.")
        if len(integrantes) < 2:
            raise ValueError("La cuadrilla debe tener al menos 2 integrantes distintos.")
        return self


class CrearCuadrillaRequest(BaseModel):
    especialidad: ESPECIALIDAD_CUADRILLA
    personal: PersonalRequest

    @model_validator(mode="after")
    def validar_roles_por_especialidad(self):
        if self.especialidad == "Agua" and self.personal.chofer_id is not None:
            raise ValueError("Las cuadrillas de Agua no admiten el rol Chofer.")
        if self.especialidad == "Desagüe" and self.personal.operador_id is not None:
            raise ValueError("Las cuadrillas de Desagüe no admiten el rol Operador.")
        return self


class ActualizarCuadrillaRequest(BaseModel):
    especialidad: Optional[ESPECIALIDAD_CUADRILLA] = None


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


class CuadrillaDetalleResponse(BaseModel):
    id: int
    codigo_grupo: str
    especialidad: Optional[str] = None
    lider: Optional[PersonaCuadrilla] = None
    apoyos: List[PersonaCuadrilla] = []
    chofer: Optional[PersonaCuadrilla] = None
    operador: Optional[PersonaCuadrilla] = None

    model_config = {"from_attributes": True}
