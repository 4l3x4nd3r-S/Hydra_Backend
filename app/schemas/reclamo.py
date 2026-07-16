from datetime import datetime
from typing import Optional, Literal
import re

from pydantic import BaseModel, Field, field_validator, model_validator


FORMATO_RECLAMO = Literal["Anexo 6", "Formato 1"]

CANAL_ENTRADA_RECLAMO = Literal[
    "Presencial",
    "Call Center",
    "Llamada Directa",
]

TIPOS_PROBLEMA_ANEXO_6 = {
    "OP-1", "OP-2", "OP-3", "OP-4", "OP-5", "OP-6", "OP-7",
}

TIPOS_PROBLEMA_FORMATO_1 = {
    "B1", "B5", "B8", "B9", "B10", "B11", "B13", "B14",
    "FALTA DE PRESIÓN DE AGUA",
    "REPOSICIÓN DE CAJA DE MEDIDOR",
    "REPOSICIÓN DE MEDIDOR POR HURTO",
    "CAMBIO DE LLAVE DE PASO",
    "REUBICACIÓN DE CONEXION",
    "REPOSICIÓN DE MARCO Y TAPA DE AGUA",
    "NIVELACIÓN DE CAJA DE REGISTRO DE AGUA",
    "B6", "B7", "B12",
    "REPOSICIÓN DE MARCO Y TAPA DE DESAGÜE",
    "NIVELACIÓN DE CAJA DE REGISTRO DE DESAGÜE",
    "REPOSICIÓN DE TUBERIA DE CONCRETO A PVC - DESAGÜE",
    "A1", "TRABAJOS COLATERAS", "OTROS",
}

TIPOS_PROBLEMA_POR_FORMATO = {
    "Anexo 6": TIPOS_PROBLEMA_ANEXO_6,
    "Formato 1": TIPOS_PROBLEMA_FORMATO_1,
}
TODOS_LOS_TIPOS_PROBLEMA = (
    TIPOS_PROBLEMA_ANEXO_6 | TIPOS_PROBLEMA_FORMATO_1
)

ESTADO_RECLAMO = Literal[
    "PENDIENTE", "ASIGNADO", "EN PROCESO", "ATENDIDO",
]


class CrearReclamoRequest(BaseModel):
    formato: FORMATO_RECLAMO
    codigo_solicitud: str = Field(pattern=r"^\d{5}$")
    canal_entrada: CANAL_ENTRADA_RECLAMO
    tipo_problema: str = Field(min_length=1, max_length=120)
    estado: ESTADO_RECLAMO = "PENDIENTE"
    descripcion: str = Field(min_length=1, max_length=500)
    nombre_solicitante: str = Field(min_length=1, max_length=100)
    direccion: str = Field(min_length=1, max_length=255)
    telefono: str = Field(pattern=r"^9[0-9]{8}$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
    numero_medidor: str = Field(pattern=r"^\d{7}$")
    fecha_registro: Optional[datetime] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

    @field_validator("nombre_solicitante")
    @classmethod
    def _solo_letras_y_espacios(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", v):
            raise ValueError("Solo se permiten letras y espacios")
        return v.strip()

    @field_validator("codigo_solicitud")
    @classmethod
    def _codigo_solicitud_no_solo_ceros(cls, v: str) -> str:
        if v == "00000":
            raise ValueError("El código de solicitud no puede ser 00000")
        return v

    @field_validator("numero_medidor")
    @classmethod
    def _numero_medidor_no_solo_ceros(cls, v: str) -> str:
        if v == "0000000":
            raise ValueError("El número de medidor no puede ser 0000000")
        return v

    @model_validator(mode="after")
    def _tipo_corresponde_al_formato(self):
        if self.tipo_problema not in TIPOS_PROBLEMA_POR_FORMATO[self.formato]:
            raise ValueError(
                f"El tipo de problema no corresponde al formato {self.formato}."
            )
        return self


class ActualizarReclamoRequest(BaseModel):
    formato: Optional[FORMATO_RECLAMO] = None
    codigo_solicitud: Optional[str] = Field(default=None, pattern=r"^\d{5}$")
    canal_entrada: Optional[CANAL_ENTRADA_RECLAMO] = None
    tipo_problema: Optional[str] = Field(default=None, max_length=120)
    estado: Optional[ESTADO_RECLAMO] = None
    descripcion: Optional[str] = Field(default=None, max_length=500)
    nombre_solicitante: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=255)
    telefono: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    email: Optional[str] = Field(
        default=None, pattern=r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
    )
    numero_medidor: Optional[str] = Field(default=None, pattern=r"^\d{7}$")
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

    @field_validator("codigo_solicitud")
    @classmethod
    def _codigo_solicitud_no_solo_ceros(cls, v: Optional[str]) -> Optional[str]:
        if v == "00000":
            raise ValueError("El código de solicitud no puede ser 00000")
        return v

    @field_validator("numero_medidor")
    @classmethod
    def _numero_medidor_no_solo_ceros(cls, v: Optional[str]) -> Optional[str]:
        if v == "0000000":
            raise ValueError("El número de medidor no puede ser 0000000")
        return v

    @field_validator("tipo_problema")
    @classmethod
    def _tipo_problema_conocido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TODOS_LOS_TIPOS_PROBLEMA:
            raise ValueError("Tipo de problema no reconocido")
        return v

    @model_validator(mode="after")
    def _tipo_corresponde_al_formato(self):
        if (
            self.formato is not None
            and self.tipo_problema is not None
            and self.tipo_problema not in TIPOS_PROBLEMA_POR_FORMATO[self.formato]
        ):
            raise ValueError(
                f"El tipo de problema no corresponde al formato {self.formato}."
            )
        return self


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
