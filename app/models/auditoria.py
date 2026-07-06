from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AuditoriaEvento(Base):
    __tablename__ = "auditoria_eventos"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    usuario_id = Column(Integer, nullable=True)
    usuario_nombre = Column(String(200), nullable=True)
    rol = Column(String(50), nullable=True)
    accion = Column(String(100), nullable=False)
    entidad = Column(String(100), nullable=False)
    entidad_id = Column(Integer, nullable=True)
    detalles = Column(JSONB, nullable=True)
