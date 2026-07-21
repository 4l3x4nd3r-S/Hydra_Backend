import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Enum,
    Sequence,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


cuadrilla_numero_sequence = Sequence(
    "cuadrilla_numero_seq",
    start=1,
    minvalue=1,
    maxvalue=999_999,
    metadata=Base.metadata,
)


def formatear_codigo_cuadrilla(numero: int) -> str:
    return f"Cuadrilla {numero:03d}"


class RolEnCuadrilla(str, enum.Enum):
    LIDER = "LIDER"
    APOYO = "APOYO"
    CHOFER = "CHOFER"


class Cuadrilla(Base):
    __tablename__ = "cuadrillas"
    __table_args__ = (
        UniqueConstraint("codigo_grupo", name="uq_cuadrillas_codigo_grupo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo_grupo = Column(String(50), nullable=False)
    especialidad = Column(String(50), nullable=True)

    personal = relationship("CuadrillaPersonal", back_populates="cuadrilla")
    ordenes = relationship("OrdenServicio", back_populates="cuadrilla")


class CuadrillaPersonal(Base):
    __tablename__ = "cuadrillas_personal"

    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    rol_en_cuadrilla = Column(
        Enum(RolEnCuadrilla, name="rol_cuadrilla"), nullable=False
    )

    cuadrilla = relationship("Cuadrilla", back_populates="personal")
    usuario = relationship("Usuario", back_populates="cuadrillas")
