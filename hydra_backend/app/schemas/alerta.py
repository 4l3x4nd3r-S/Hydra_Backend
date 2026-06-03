from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.alerta import TipoAlerta, NivelAlerta, EstadoAlerta


class CrearAlertaRequest(BaseModel):
    sensor_id: Optional[str] = None
    sector_id: Optional[int] = None
    tipo: TipoAlerta
    nivel: NivelAlerta
    descripcion: Optional[str] = None
    presion_detectada_mca: Optional[float] = None


class AlertaResponse(BaseModel):
    id: int
    sensor_id: Optional[str] = None
    sector_id: Optional[int] = None
    tipo: str
    nivel: str
    estado: str
    descripcion: Optional[str] = None
    presion_detectada_mca: Optional[float] = None
    ot_id: Optional[int] = None
    created_at: datetime
    atendida_at: Optional[datetime] = None
    plazo_atencion_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
