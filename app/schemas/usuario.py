from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.usuario import EstadoPersonal, RolUsuario

CARGOS_PROHIBIDOS = {"CHOFER", "CHOFER_CAMIONETA"}


def _rechazar_cargo_chofer(value: Optional[str]) -> Optional[str]:
    """La figura de chofer ya no se usa: no se puede asignar ese cargo."""
    if value is not None and value.strip().upper() in CARGOS_PROHIBIDOS:
        raise ValueError(
            "El cargo de chofer ya no está disponible; usa GASFITERO."
        )
    return value


class CrearUsuarioRequest(BaseModel):
    codigo_empleado: str
    nombre: str
    dni: Optional[str] = Field(default=None, pattern=r"^[0-9]{8}$")
    celular: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    rol: RolUsuario = RolUsuario.GASFITERO
    password: str = Field(min_length=12, max_length=128)
    cargo: Optional[str] = "GASFITERO"
    area: Optional[str] = "MANTENIMIENTO"

    @field_validator("cargo")
    @classmethod
    def _validar_cargo(cls, value):
        return _rechazar_cargo_chofer(value)


class ActualizarUsuarioRequest(BaseModel):
    nombre: Optional[str] = None
    dni: Optional[str] = Field(default=None, pattern=r"^[0-9]{8}$")
    celular: Optional[str] = Field(default=None, pattern=r"^9[0-9]{8}$")
    rol: Optional[RolUsuario] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)
    estado: Optional[EstadoPersonal] = None
    motivo_ausencia: Optional[str] = Field(default=None, max_length=200)
    fecha_retorno: Optional[date] = None
    # Compatibilidad temporal: la web anterior solo enviaba ``activo``.
    # El estado real se deriva en el router únicamente si no llega ``estado``.
    activo: Optional[bool] = None

    @field_validator("cargo")
    @classmethod
    def _validar_cargo(cls, value):
        return _rechazar_cargo_chofer(value)

    @field_validator("fecha_retorno", mode="before")
    @classmethod
    def _normalizar_fecha_retorno(cls, value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            texto = value.strip()
            if len(texto) > 10:
                return texto[:10]
            return texto or None
        return value


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
    estado: Optional[EstadoPersonal] = None
    motivo_ausencia: Optional[str] = None
    fecha_retorno: Optional[date] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
