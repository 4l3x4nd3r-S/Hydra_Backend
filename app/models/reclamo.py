from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Reclamo(Base):
    __tablename__ = "reclamos"
    __table_args__ = (
        CheckConstraint(
            "codigo_solicitud IS NULL OR "
            "(codigo_solicitud ~ '^[0-9]{5}$' AND codigo_solicitud <> '00000')",
            name="ck_reclamos_codigo_solicitud_5_digitos",
        ),
        CheckConstraint(
            "numero_medidor IS NULL OR "
            "(numero_medidor ~ '^[0-9]{7}$' AND numero_medidor <> '0000000')",
            name="ck_reclamos_numero_medidor_7_digitos",
        ),
        CheckConstraint(
            "telefono IS NULL OR telefono ~ '^9[0-9]{8}$'",
            name="ck_reclamos_telefono_peru",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    canal_entrada = Column(String(50), nullable=True)
    tipo_problema = Column(String(120), nullable=True)
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
    numero_medidor = Column(String(7), nullable=True)
    codigo_solicitud = Column(String(5), nullable=True)

    usuario = relationship("Usuario", back_populates="reclamos")
    ordenes = relationship("OrdenServicio", back_populates="reclamo")
