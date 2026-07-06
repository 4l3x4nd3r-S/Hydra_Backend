from typing import Optional, List, Literal
from pydantic import BaseModel


ESPECIALIDAD_CUADRILLA = Literal["Agua", "Desagüe"]


class PersonalRequest(BaseModel):
    lider_id: int
    apoyos_ids: List[int] = []
    chofer_id: Optional[int] = None
    operador_id: Optional[int] = None


class CrearCuadrillaRequest(BaseModel):
    codigo_grupo: str
    especialidad: Optional[ESPECIALIDAD_CUADRILLA] = None
    personal: Optional[PersonalRequest] = None


class ActualizarCuadrillaRequest(BaseModel):
    codigo_grupo: Optional[str] = None
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
