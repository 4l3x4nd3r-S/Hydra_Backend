from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

numero_orden_sequence = Sequence(
    "orden_servicio_numero_seq",
    start=1,
    minvalue=1,
    maxvalue=9_999_999,
    metadata=Base.metadata,
)


class OrdenServicio(Base):
    __tablename__ = "ordenes_servicio"
    __table_args__ = (
        UniqueConstraint(
            "numero_orden", name="uq_ordenes_servicio_numero_orden"
        ),
        CheckConstraint(
            "numero_orden IS NULL OR numero_orden ~ '^[0-9]{7}$'",
            name="ck_ordenes_servicio_numero_orden_7_digitos",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    numero_orden = Column(String(7), nullable=True)
    reclamo_id = Column(Integer, ForeignKey("reclamos.id"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=True)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    fecha_programacion = Column(DateTime, nullable=True)
    fecha_ejecucion_inicio = Column(DateTime, nullable=True)
    fecha_ejecucion_fin = Column(DateTime, nullable=True)
    estado_orden = Column(String(50), nullable=True)
    insumos_utilizados = Column(Text, nullable=True)
    observaciones_gasfitero = Column(Text, nullable=True)
    ruta_carpeta_evidencias = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    trabajo_ejecutado = Column(Text, nullable=True)
    problemas = Column(Text, nullable=True)
    soluciones = Column(Text, nullable=True)
    comentarios_instrucciones = Column(Text, nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    fotos_problema_urls = Column(JSON, nullable=True)
    fotos_solucion_urls = Column(JSON, nullable=True)
    cuadrilla_snapshot = Column(JSON, nullable=True)

    reclamo = relationship("Reclamo", back_populates="ordenes")
    supervisor = relationship(
        "Usuario", back_populates="ordenes_supervisadas", foreign_keys=[supervisor_id]
    )
    cuadrilla = relationship("Cuadrilla", back_populates="ordenes")
    responsable = relationship("Usuario", back_populates="ordenes_asignadas", foreign_keys=[responsable_id])
    sector = relationship("Sector", back_populates="ordenes")
