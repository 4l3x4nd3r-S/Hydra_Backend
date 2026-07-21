from typing import Optional

from pydantic import BaseModel, ConfigDict


class CatalogoOpcionResponse(BaseModel):
    grupo: str
    codigo: str
    etiqueta: str
    descripcion: Optional[str] = None
    padre_codigo: Optional[str] = None
    relacionado_codigo: Optional[str] = None
    orden: int
    predeterminado: bool

    model_config = ConfigDict(from_attributes=True)
