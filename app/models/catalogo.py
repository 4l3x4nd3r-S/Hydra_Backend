from sqlalchemy import Boolean, Column, Integer, String, Text, UniqueConstraint

from app.core.database import Base


class CatalogoOpcion(Base):
    __tablename__ = "catalogo_opciones"
    __table_args__ = (
        UniqueConstraint("grupo", "codigo", name="uq_catalogo_grupo_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String(50), nullable=False, index=True)
    codigo = Column(String(120), nullable=False)
    etiqueta = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    padre_codigo = Column(String(120), nullable=True)
    relacionado_codigo = Column(String(120), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    predeterminado = Column(Boolean, nullable=False, default=False)
