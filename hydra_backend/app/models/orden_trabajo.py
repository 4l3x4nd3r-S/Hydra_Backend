import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class EstadoOT(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    RESUELTA = "RESUELTA"
    FORZADA = "FORZADA"


class PrioridadOT(str, enum.Enum):
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(50), ForeignKey("sensores.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    asignado_a = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    estado = Column(String(20), default=EstadoOT.PENDIENTE, nullable=False)
    prioridad = Column(String(20), nullable=False)

    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    tipo_hallazgo_real = Column(String(50), nullable=True)
    material_real = Column(String(50), nullable=True)
    diametro_real = Column(String(20), nullable=True)
    materiales_usados = Column(JSONB, nullable=True)
    foto_antes_url = Column(String(255), nullable=True)
    foto_despues_url = Column(String(255), nullable=True)
    ubicacion_reparacion = Column(Geometry("POINT", srid=4326), nullable=True)
    presion_verificacion_mca = Column(Numeric(5, 2), nullable=True)
    justificacion_forzado = Column(Text, nullable=True)
    firma_tecnico_url = Column(String(255), nullable=True)

    sensor = relationship("Sensor", back_populates="ordenes")
    sector = relationship("Sector", back_populates="ordenes")
    tecnico = relationship("Usuario", back_populates="ordenes")
