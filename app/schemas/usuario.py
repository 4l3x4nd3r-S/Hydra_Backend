from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.usuario import RolUsuario


class CrearUsuarioRequest(BaseModel):
    codigo_empleado: str
    nombre: str
    rol: RolUsuario
    password: str
    cargo: Optional[str] = None
    area: Optional[str] = None


class ActualizarUsuarioRequest(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolUsuario] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = None


class UsuarioResponse(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    rol: str
    cargo: Optional[str] = None
    area: Optional[str] = None
    activo: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
