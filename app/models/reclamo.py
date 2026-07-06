from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Reclamo(Base):
    __tablename__ = "reclamos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    canal_entrada = Column(String(50), nullable=True)
    tipo_problema = Column(String(50), nullable=True)
    formato = Column(String(50), nullable=True)
    descripcion = Column(Text, nullable=True)
    direccion = Column(String(255), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    estado = Column(String(50), nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=func.now())
    nombre_solicitante = Column(String(200), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    numero_medidor = Column(String(50), nullable=True)
    codigo_solicitud = Column(String(50), nullable=True)

    usuario = relationship("Usuario", back_populates="reclamos")
    ordenes = relationship("OrdenServicio", back_populates="reclamo")
