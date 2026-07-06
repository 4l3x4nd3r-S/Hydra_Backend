from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PuntoPresion(Base):
    __tablename__ = "puntos_presion"

    id = Column(Integer, primary_key=True, index=True)
    codigo_punto = Column(String(50), unique=True, nullable=False)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    sector = relationship("Sector", back_populates="puntos_presion")
    registros = relationship("RegistroPresion", back_populates="punto_presion", cascade="all, delete")
