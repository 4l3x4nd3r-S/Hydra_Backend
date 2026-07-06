import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RolUsuario(str, enum.Enum):
    SUPERVISOR = "SUPERVISOR"
    GASFITERO = "GASFITERO"


class CargoUsuario(str, enum.Enum):
    GASFITERO_PRINCIPAL = "GASFITERO_PRINCIPAL"
    GASFITERO_APOYO = "GASFITERO_APOYO"
    CHOFER = "CHOFER"
    OPERADOR_MAQUINARIA = "OPERADOR_MAQUINARIA"
    GASFITERO = "GASFITERO"
    CHOFER_CAMIONETA = "CHOFER_CAMIONETA"
    OPERADOR_RETROEXCAVADORA = "OPERADOR_RETROEXCAVADORA"


class AreaUsuario(str, enum.Enum):
    DISTRIBUCION = "DISTRIBUCION"
    MANTENIMIENTO = "MANTENIMIENTO"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    codigo_empleado = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
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
