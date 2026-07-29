from typing import Optional

from pydantic import BaseModel


class CrearSectorRequest(BaseModel):
    nombre: str

    geometria_geojson: Optional[str] = None


class ActualizarSectorRequest(BaseModel):
    nombre: Optional[str] = None

    geometria_geojson: Optional[str] = None


class SectorResponse(BaseModel):
    id: int
    nombre: str

    geometria_geojson: Optional[str] = None

    model_config = {"from_attributes": True}
