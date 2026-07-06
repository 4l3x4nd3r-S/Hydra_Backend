from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrdenServicio(Base):
    __tablename__ = "ordenes_servicio"

    id = Column(Integer, primary_key=True, index=True)
    numero_orden = Column(String(50), nullable=True)
    reclamo_id = Column(Integer, ForeignKey("reclamos.id"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=True)
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

    reclamo = relationship("Reclamo", back_populates="ordenes")
    supervisor = relationship(
        "Usuario", back_populates="ordenes_supervisadas", foreign_keys=[supervisor_id]
    )
    cuadrilla = relationship("Cuadrilla", back_populates="ordenes")
    sector = relationship("Sector", back_populates="ordenes")
