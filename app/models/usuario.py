import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

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
    created_at = Column(DateTime, default=func.now())

    cuadrillas = relationship("CuadrillaPersonal", back_populates="usuario")
    reclamos = relationship("Reclamo", back_populates="usuario")
    ordenes_supervisadas = relationship(
        "OrdenServicio", back_populates="supervisor", foreign_keys="OrdenServicio.supervisor_id"
    )
    ordenes_asignadas = relationship(
        "OrdenServicio", back_populates="responsable", foreign_keys="OrdenServicio.responsable_id"
    )
