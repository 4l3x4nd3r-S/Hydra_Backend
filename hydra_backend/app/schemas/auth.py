from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    dni: str
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
    dni: str
    nombre: str
    rol: str
    cuadrilla_nombre: Optional[str] = None

    model_config = {"from_attributes": True}
