from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.usuario import RolUsuario


class CrearUsuarioRequest(BaseModel):
    dni: str
    nombre: str
    rol: RolUsuario
    cuadrilla_nombre: Optional[str] = None
    password: str

    @field_validator("dni")
    @classmethod
    def dni_debe_tener_8_digitos(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 8:
            raise ValueError("El DNI debe tener exactamente 8 dígitos numéricos.")
        return v


class ActualizarUsuarioRequest(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolUsuario] = None
    cuadrilla_nombre: Optional[str] = None
    password: Optional[str] = None


class UsuarioResponse(BaseModel):
    id: int
    dni: str
    nombre: str
    rol: str
    cuadrilla_nombre: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
