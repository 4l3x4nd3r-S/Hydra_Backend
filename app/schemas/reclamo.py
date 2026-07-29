import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
class _ValidacionesReclamo:
    @field_validator("nombre_solicitante", check_fields=False)
    @classmethod
    def _solo_letras_y_espacios(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return valor
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", valor):
            raise ValueError("Solo se permiten letras y espacios")
        return valor.strip()
    @field_validator("codigo_solicitud", check_fields=False)
    @classmethod
    def _codigo_no_solo_ceros(cls, valor: Optional[str]) -> Optional[str]:
        if valor == "00000":
            raise ValueError("El código de solicitud no puede ser 00000")
        return valor
    @field_validator("numero_suministro", check_fields=False)
    @classmethod
    def _suministro_no_solo_ceros(cls, valor: Optional[str]) -> Optional[str]:
        if valor == "0000000":
            raise ValueError("El número de suministro no puede ser 0000000")
        return valor
class CrearReclamoRequest(_ValidacionesReclamo, BaseModel):
    formato: str = Field(min_length=1, max_length=120)
    codigo_solicitud: str = Field(pattern=r"^\d{5}$")
    canal_entrada: str = Field(min_length=1, max_length=120)
    tipo_problema: str = Field(min_length=1, max_length=120)
    estado: Optional[str] = Field(default=None, max_length=50)
    descripcion: str = Field(min_length=1, max_length=500)
    nombre_solicitante: str = Field(min_length=1, max_length=100)
    direccion: str = Field(min_length=1, max_length=255)
    telefono: str = Field(pattern=r"^9[0-9]{8}$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
    numero_suministro: str = Field(pattern=r"^\d{7}$")
    fecha_registro: Optional[datetime] = None
class ActualizarReclamoRequest(_ValidacionesReclamo, BaseModel):
    formato: Optional[str] = Field(default=None, max_length=120)
    codigo_solicitud: Optional[str] = Field(default=None, pattern=r"^\d{5}$")
    canal_entrada: Optional[str] = Field(default=None, max_length=120)
    tipo_problema: Optional[str] = Field(default=None, max_length=120)
    estado: Optional[str] = Field(default=None, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    nombre_solicitante: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=255)
    telefono: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    email: Optional[str] = Field(
        default=None, pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
    )
    numero_suministro: Optional[str] = Field(default=None, pattern=r"^\d{7}$")
class ReclamoResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    canal_entrada: Optional[str] = None
    tipo_problema: Optional[str] = None
    formato: Optional[str] = None
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    estado: Optional[str] = None
    fecha_registro: datetime
    nombre_solicitante: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    numero_suministro: Optional[str] = None
    codigo_solicitud: Optional[str] = None
    model_config = {"from_attributes": True}
