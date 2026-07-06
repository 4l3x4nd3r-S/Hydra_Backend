from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.models.usuario import RolUsuario


class LoginRequest(BaseModel):
    codigo_empleado: str
    password: str


class UserInfo(BaseModel):
    id: int
    nombre: str
    rol: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class UserProfile(BaseModel):
    id: int
    codigo_empleado: str
    nombre: str
    rol: str
    activo: bool

    model_config = {"from_attributes": True}
