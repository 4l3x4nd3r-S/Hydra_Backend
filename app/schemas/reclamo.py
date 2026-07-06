from datetime import datetime
from typing import Optional, Literal
import re

from pydantic import BaseModel, Field, field_validator


FORMATO_RECLAMO = Literal["Anexo 6", "Formato 1"]

CANAL_ENTRADA_RECLAMO = Literal[
    "Presencial",
    "Call Center",
    "Llamada Directa",
]

TIPO_PROBLEMA_RECLAMO = Literal[
    "OP-1", "OP-2", "OP-3", "OP-4", "OP-5", "OP-6", "OP-7",
]

ESTADO_RECLAMO = Literal[
    "PENDIENTE", "ASIGNADO", "EN PROCESO", "ATENDIDO",
]


class CrearReclamoRequest(BaseModel):
    formato: FORMATO_RECLAMO
    codigo_solicitud: str = Field(min_length=1, max_length=50)
    canal_entrada: CANAL_ENTRADA_RECLAMO
    tipo_problema: TIPO_PROBLEMA_RECLAMO
    estado: ESTADO_RECLAMO = "PENDIENTE"
    descripcion: str = Field(min_length=1, max_length=500)
    nombre_solicitante: str = Field(min_length=1, max_length=100)
    direccion: str = Field(min_length=1, max_length=255)
    telefono: str = Field(pattern=r"^\d{9}$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
    numero_medidor: str = Field(pattern=r"^\d{1,8}$")
    fecha_registro: Optional[datetime] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

    @field_validator("nombre_solicitante")
    @classmethod
    def _solo_letras_y_espacios(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", v):
            raise ValueError("Solo se permiten letras y espacios")
        return v.strip()


class ActualizarReclamoRequest(BaseModel):
    formato: Optional[FORMATO_RECLAMO] = None
    codigo_solicitud: Optional[str] = Field(default=None, max_length=50)
    canal_entrada: Optional[CANAL_ENTRADA_RECLAMO] = None
    tipo_problema: Optional[TIPO_PROBLEMA_RECLAMO] = None
    estado: Optional[ESTADO_RECLAMO] = None
    descripcion: Optional[str] = Field(default=None, max_length=500)
    nombre_solicitante: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=255)
    telefono: Optional[str] = Field(default=None, pattern=r"^\d{9}$")
    email: Optional[str] = Field(
        default=None, pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
    )
    numero_medidor: Optional[str] = Field(default=None, pattern=r"^\d{1,8}$")
    latitud: Optional[float] = None
    longitud: Optional[float] = None

    @field_validator("nombre_solicitante")
    @classmethod
    def _solo_letras_y_espacios(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", v):
            raise ValueError("Solo se permiten letras y espacios")
        return v.strip()


class ReclamoResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    canal_entrada: Optional[str] = None
    tipo_problema: Optional[str] = None
    formato: Optional[str] = None
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    estado: Optional[str] = None
    fecha_registro: datetime
    nombre_solicitante: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    numero_medidor: Optional[str] = None
    codigo_solicitud: Optional[str] = None

    model_config = {"from_attributes": True}
