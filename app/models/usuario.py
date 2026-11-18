import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship, validates

from app.core.database import Base


class RolUsuario(str, enum.Enum):
    SUPERVISOR = "SUPERVISOR"
    GASFITERO = "GASFITERO"


class CargoUsuario(str, enum.Enum):
    GASFITERO = "GASFITERO"
    GASFITERO_PRINCIPAL = "GASFITERO_PRINCIPAL"
    GASFITERO_APOYO = "GASFITERO_APOYO"
    CHOFER_CAMIONETA = "CHOFER_CAMIONETA"


class AreaUsuario(str, enum.Enum):
    MANTENIMIENTO = "MANTENIMIENTO"


class EstadoPersonal(str, enum.Enum):
    ACTIVO = "ACTIVO"
    AUSENTE = "AUSENTE"
    RETIRADO = "RETIRADO"


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "dni IS NULL OR dni ~ '^[0-9]{8}$'",
            name="ck_usuarios_dni_formato",
        ),
        CheckConstraint(
            "celular IS NULL OR celular ~ '^9[0-9]{8}$'",
            name="ck_usuarios_celular_formato",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo_empleado = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    dni = Column(String(8), unique=True, nullable=True)
    celular = Column(String(9), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    cargo = Column(Enum(CargoUsuario, name="cargo_usuario"), nullable=True)
    area = Column(Enum(AreaUsuario, name="area_usuario"), nullable=True)
    activo = Column(Boolean, default=True)
    estado = Column(
        Enum(EstadoPersonal, name="estado_personal"),
        nullable=False,
        default=EstadoPersonal.ACTIVO,
        server_default=EstadoPersonal.ACTIVO.value,
    )
    motivo_ausencia = Column(String(200), nullable=True)
    fecha_retorno = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())

    @validates("estado")
    def _sincronizar_activo(self, key, value):
        """Mantiene ``activo`` sincronizado con ``estado``.

        ``activo`` se conserva porque las consultas existentes (login, refresh,
        supervisor y app móvil) ya lo usan. Un ausente o retirado queda fuera de
        todas ellas sin necesidad de reescribirlas.
        """
        estado = (
            value
            if isinstance(value, EstadoPersonal)
            else EstadoPersonal(value)
        )
        self.activo = estado == EstadoPersonal.ACTIVO
        return estado

    cuadrillas = relationship("CuadrillaPersonal", back_populates="usuario")
    reclamos = relationship("Reclamo", back_populates="usuario")
    ordenes_supervisadas = relationship(
        "OrdenServicio", back_populates="supervisor", foreign_keys="OrdenServicio.supervisor_id"
    )
