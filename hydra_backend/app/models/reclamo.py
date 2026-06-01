from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class Reclamo(Base):
    __tablename__ = "reclamos"

    id = Column(Integer, primary_key=True, index=True)
    nro_reclamo = Column(String(50), unique=True, nullable=False)
    codigo_cliente = Column(String(50), nullable=False)
    fecha_reclamo = Column(DateTime, nullable=False)
    tipo_reclamo = Column(String(150), nullable=False)
    direccion = Column(Text, nullable=False)
    urbanizacion = Column(String(150), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    ubicacion = Column(Geometry("POINT", srid=4326), nullable=True)
    created_at = Column(DateTime, default=func.now())

    sector = relationship("Sector", back_populates="reclamos")
