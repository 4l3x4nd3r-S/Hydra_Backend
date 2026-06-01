from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Numeric, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class Sensor(Base):
    __tablename__ = "sensores"

    id = Column(String(50), primary_key=True)
    point_id = Column(String(50), unique=True, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    ubicacion = Column(Geometry("POINT", srid=4326), nullable=True)
    created_at = Column(DateTime, default=func.now())

    sector = relationship("Sector", back_populates="sensores")
    lecturas = relationship("LecturaPresion", back_populates="sensor", cascade="all, delete")
    ordenes = relationship("OrdenTrabajo", back_populates="sensor")


class LecturaPresion(Base):
    __tablename__ = "lecturas_presion"

    id = Column(BigInteger, primary_key=True, index=True)
    sensor_id = Column(String(50), ForeignKey("sensores.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    presion = Column(Numeric(5, 2), nullable=False)
    temperatura = Column(Numeric(4, 2), nullable=True)

    __table_args__ = (UniqueConstraint("sensor_id", "timestamp", name="uq_sensor_timestamp"),)

    sensor = relationship("Sensor", back_populates="lecturas")
