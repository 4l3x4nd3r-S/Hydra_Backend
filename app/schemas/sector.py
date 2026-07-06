from typing import Optional

from pydantic import BaseModel


class CrearSectorRequest(BaseModel):
    nombre: str
    reservorio_asociado: Optional[str] = None
    geometria_geojson: Optional[str] = None


class ActualizarSectorRequest(BaseModel):
    nombre: Optional[str] = None
    reservorio_asociado: Optional[str] = None
    geometria_geojson: Optional[str] = None


class SectorResponse(BaseModel):
    id: int
    nombre: str
    reservorio_asociado: Optional[str] = None
    geometria_geojson: Optional[str] = None

    model_config = {"from_attributes": True}
