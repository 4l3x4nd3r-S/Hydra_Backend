from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class ElementoRed(Base):
    __tablename__ = "elementos_red"

    id = Column(Integer, primary_key=True, index=True)
    codigo_plano = Column(String(50), nullable=True)
    tipo = Column(String(50), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    estado_operativo = Column(String(50), nullable=True)
    estado_valvula = Column(String(50), nullable=True)
    fecha_modificacion = Column(DateTime, nullable=True)

    sector = relationship("Sector", back_populates="elementos_red")
