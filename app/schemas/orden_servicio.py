from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class CrearOrdenServicioRequest(BaseModel):
    numero_orden: Optional[str] = None
    reclamo_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    cuadrilla_id: int

    fecha_programacion: Optional[datetime] = None


class ActualizarOrdenServicioRequest(BaseModel):
    numero_orden: Optional[str] = None
    reclamo_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    cuadrilla_id: Optional[int] = None

    fecha_programacion: Optional[datetime] = None
    estado_orden: Optional[str] = None


class FinalizarOrdenRequest(BaseModel):
    insumos_utilizados: Optional[str] = None
    observaciones_gasfitero: Optional[str] = None
    trabajo_ejecutado: Optional[str] = None
    problemas: Optional[str] = None
    soluciones: Optional[str] = None
    comentarios_instrucciones: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    fotos_problema_urls: Optional[List[str]] = None
    fotos_solucion_urls: Optional[List[str]] = None
    fecha_ejecucion_inicio: Optional[datetime] = None
    fecha_ejecucion_fin: Optional[datetime] = None

class ReclamoMinimoResponse(BaseModel):
    id: int
    formato: Optional[str] = None
    codigo_solicitud: Optional[str] = None
    canal_entrada: Optional[str] = None
    tipo_problema: Optional[str] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None
    nombre_solicitante: Optional[str] = None
    direccion: Optional[str] = None
    numero_suministro: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    fecha_registro: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MiembroCuadrillaResponse(BaseModel):
    id: int
    nombre: str
    codigo_empleado: str
    rol_en_cuadrilla: str

    model_config = ConfigDict(from_attributes=True)


class CuadrillaMinimaResponse(BaseModel):
    id: int
    codigo_grupo: str
    especialidad: Optional[str] = None
    lider: Optional[MiembroCuadrillaResponse] = None
    apoyos: List[MiembroCuadrillaResponse] = []
    chofer: Optional[MiembroCuadrillaResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ResponsableMinimoResponse(BaseModel):
    id: int
    nombre: str
    codigo_empleado: str
    cargo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrdenServicioResponse(BaseModel):
    id: int
    numero_orden: Optional[str] = None
    reclamo_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    cuadrilla_id: Optional[int] = None
    responsable_id: Optional[int] = None

    fecha_programacion: Optional[datetime] = None
    fecha_ejecucion_inicio: Optional[datetime] = None
    fecha_ejecucion_fin: Optional[datetime] = None
    estado_orden: Optional[str] = None
    insumos_utilizados: Optional[str] = None
    observaciones_gasfitero: Optional[str] = None
    created_at: Optional[datetime] = None
    trabajo_ejecutado: Optional[str] = None
    problemas: Optional[str] = None
    soluciones: Optional[str] = None
    comentarios_instrucciones: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    fotos_problema_urls: List[str] = []
    fotos_solucion_urls: List[str] = []

    reclamo: Optional[ReclamoMinimoResponse] = None
    cuadrilla: Optional[CuadrillaMinimaResponse] = None

    model_config = ConfigDict(from_attributes=True)
