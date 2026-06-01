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
