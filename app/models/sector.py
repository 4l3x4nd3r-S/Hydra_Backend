from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Sector(Base):
    __tablename__ = "sectores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    reservorio_asociado = Column(String(100), nullable=True)
    geometria_geojson = Column(Text, nullable=True)

    puntos_presion = relationship("PuntoPresion", back_populates="sector")
    elementos_red = relationship("ElementoRed", back_populates="sector")
    ordenes = relationship("OrdenServicio", back_populates="sector")
