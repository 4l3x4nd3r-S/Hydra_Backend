import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RolUsuario(str, enum.Enum):
    GERENTE = "GERENTE"
    JEFE_OFICINA = "JEFE_OFICINA"
    ESPECIALISTA = "ESPECIALISTA"
    TECNICO_CAMPO = "TECNICO_CAMPO"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(8), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    rol = Column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    cuadrilla_nombre = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())

    ordenes = relationship("OrdenTrabajo", back_populates="tecnico")
