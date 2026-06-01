import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoAlerta(str, enum.Enum):
    PRESION_BAJA = "PRESION_BAJA"
    FUGA_PROBABLE = "FUGA_PROBABLE"
    ANOMALIA = "ANOMALIA"


class NivelAlerta(str, enum.Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class EstadoAlerta(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    ATENDIDA = "ATENDIDA"
    DESCARTADA = "DESCARTADA"


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(50), ForeignKey("sensores.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    tipo = Column(String(30), nullable=False)
    nivel = Column(String(10), nullable=False)
    estado = Column(String(15), nullable=False, default=EstadoAlerta.PENDIENTE)
    descripcion = Column(Text, nullable=True)
    presion_detectada_mca = Column(Numeric(6, 3), nullable=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    atendida_at = Column(DateTime, nullable=True)

    sensor = relationship("Sensor")
    ot = relationship("OrdenTrabajo")
