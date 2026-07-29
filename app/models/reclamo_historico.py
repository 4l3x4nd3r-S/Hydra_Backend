from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from app.core.database import Base


class ReclamoHistorico(Base):
    __tablename__ = "reclamos_historicos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_solicitud = Column(String(50), nullable=True)
    numero_suministro = Column(String(50), nullable=True)
    direccion = Column(String(255), nullable=True)
    fecha_registro = Column(DateTime, nullable=True)
    tipo_problema = Column(String(120), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    estado = Column(String(50), nullable=True, default="HISTORICO")
