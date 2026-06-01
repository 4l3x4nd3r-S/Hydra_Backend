from sqlalchemy import Column, Integer, String, Text
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship

from app.core.database import Base


class Sector(Base):
    __tablename__ = "sectores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)

    sensores = relationship("Sensor", back_populates="sector")
    reclamos = relationship("Reclamo", back_populates="sector")
    ordenes = relationship("OrdenTrabajo", back_populates="sector")
