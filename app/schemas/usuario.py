from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.usuario import RolUsuario


class CrearUsuarioRequest(BaseModel):
    codigo_empleado: str
    nombre: str
    dni: Optional[str] = Field(default=None, pattern=r"^[0-9]{8}$")
    celular: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    rol: RolUsuario
    password: str = Field(min_length=12, max_length=128)
    cargo: Optional[str] = None
    area: Optional[str] = None


class ActualizarUsuarioRequest(BaseModel):
    nombre: Optional[str] = None
    dni: Optional[str] = Field(default=None, pattern=r"^[0-9]{8}$")
    celular: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    rol: Optional[RolUsuario] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)


class UsuarioResponse(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    dni: Optional[str] = None
    celular: Optional[str] = None
    rol: str
    cargo: Optional[str] = None
    area: Optional[str] = None
    activo: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
