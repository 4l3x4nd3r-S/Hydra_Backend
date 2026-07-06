from sqlalchemy import Column, BigInteger, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class RegistroPresion(Base):
    __tablename__ = "registros_presion"

    id = Column(BigInteger, primary_key=True, index=True)
    punto_presion_id = Column(Integer, ForeignKey("puntos_presion.id", ondelete="CASCADE"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    presion_mca = Column(Float, nullable=False)
    temperatura_c = Column(Float, nullable=True)
    dispositivo_serie = Column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("punto_presion_id", "fecha_hora", name="uq_punto_timestamp"),)

    punto_presion = relationship("PuntoPresion", back_populates="registros")
