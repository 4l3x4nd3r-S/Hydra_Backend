import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import upload_file
from app.core.security import get_current_user
from app.models.orden_trabajo import OrdenTrabajo, EstadoOT
from app.models.sensor import LecturaPresion, Sensor
from app.models.usuario import Usuario
from app.schemas.ot import (
    OTAsignadaResponse,
    OTIniciadaResponse,
    ControlPresionResponse,
    OTCerradaResponse,
    UbicacionGPS,
)

router = APIRouter(prefix="/ots", tags=["Ordenes de Trabajo"])


@router.get("/assigned", response_model=list[OTAsignadaResponse], summary="Listar OTs asignadas")
async def get_assigned_ots(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenTrabajo)
        .where(
            OrdenTrabajo.asignado_a == current_user.id,
            OrdenTrabajo.estado.in_([EstadoOT.PENDIENTE, EstadoOT.EN_PROCESO]),
        )
        .order_by(OrdenTrabajo.created_at.desc())
    )
    ordenes = result.scalars().all()

    output = []
    for ot in ordenes:
        point_id = None
        ubicacion = None

        if ot.sensor_id:
            sensor_result = await db.execute(
                select(
                    Sensor.point_id,
                    ST_AsGeoJSON(Sensor.ubicacion).label("geojson"),
                ).where(Sensor.id == ot.sensor_id)
            )
            sensor_row = sensor_result.first()
            if sensor_row:
                point_id = sensor_row.point_id
                if sensor_row.geojson:
                    coords = json.loads(sensor_row.geojson)["coordinates"]
                    ubicacion = UbicacionGPS(lat=coords[1], lon=coords[0])

        output.append(
            OTAsignadaResponse(
                id=ot.id,
                sensor_id=ot.sensor_id,
                point_id=point_id,
                prioridad=ot.prioridad,
                estado=ot.estado,
                created_at=ot.created_at,
                ubicacion_estimada=ubicacion,
            )
        )

    return output


@router.post("/{ot_id}/start", response_model=OTIniciadaResponse, summary="Iniciar temporizador de reparación")
async def start_ot(
    ot_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == ot_id,
            OrdenTrabajo.asignado_a == current_user.id,
        )
    )
    ot = result.scalars().first()

    if not ot:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")

    if ot.estado != EstadoOT.PENDIENTE:
        raise HTTPException(
            status_code=400,
            detail=f"La OT ya fue iniciada o cerrada (estado actual: {ot.estado}).",
        )

    ot.estado = EstadoOT.EN_PROCESO
    ot.started_at = datetime.utcnow()
    await db.commit()

    return OTIniciadaResponse(
        message="OT iniciada con éxito. Temporizador de respuesta iniciado.",
        started_at=ot.started_at,
    )


@router.get("/{ot_id}/verify-pressure", response_model=ControlPresionResponse, summary="Verificar presión hidráulica")
async def verify_hydraulic_pressure(
    ot_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ot_result = await db.execute(select(OrdenTrabajo).where(OrdenTrabajo.id == ot_id))
    ot = ot_result.scalars().first()

    if not ot:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")

    if not ot.sensor_id:
        raise HTTPException(
            status_code=400,
            detail="Esta OT no está vinculada a un sensor de presión.",
        )

    lectura_result = await db.execute(
        select(LecturaPresion)
        .where(LecturaPresion.sensor_id == ot.sensor_id)
        .order_by(desc(LecturaPresion.timestamp))
        .limit(1)
    )
    ultima_lectura = lectura_result.scalars().first()

    if not ultima_lectura:
        raise HTTPException(
            status_code=404,
            detail=f"No se registran lecturas históricas para el sensor {ot.sensor_id}.",
        )

    mca_actual = float(ultima_lectura.presion)
    presion_ok = mca_actual >= 15.00
    mensaje = (
        "Presión normalizada. Se autoriza el cierre completo de la orden."
        if presion_ok
        else "Presión de red baja. Verifique fugas adicionales en el sector antes de firmar."
    )

    return ControlPresionResponse(
        ot_id=ot.id,
        sensor_id=ot.sensor_id,
        presion_actual_mca=mca_actual,
        presion_recuperada=presion_ok,
        mensaje=mensaje,
    )




@router.post("/{ot_id}/close", response_model=OTCerradaResponse, summary="Cerrar orden de trabajo")
async def close_ot(
    ot_id: int,
    tipo_hallazgo_real: str = Form(...),
    material_real: str = Form(...),
    diametro_real: str = Form(...),
    materiales_usados: str = Form(...),
    lat_reparacion: float = Form(...),
    lon_reparacion: float = Form(...),
    presion_verificacion_mca: Optional[float] = Form(None),
    justificacion_forzado: Optional[str] = Form(None),
    foto_antes: UploadFile = File(...),
    foto_despues: UploadFile = File(...),
    firma_tecnico: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == ot_id,
            OrdenTrabajo.asignado_a == current_user.id,
        )
    )
    ot = result.scalars().first()

    if not ot:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")

    if ot.estado not in [EstadoOT.EN_PROCESO, EstadoOT.PENDIENTE]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cerrar una OT en estado '{ot.estado}'.",
        )

    try:
        materiales_json = json.loads(materiales_usados)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="materiales_usados debe ser un JSON válido.")

    foto_antes_url = await upload_file(foto_antes, "fotos")
    foto_despues_url = await upload_file(foto_despues, "fotos")
    firma_url = await upload_file(firma_tecnico, "firmas")

    now = datetime.utcnow()
    if presion_verificacion_mca is not None:
        estado_final = EstadoOT.FORZADA if presion_verificacion_mca < 15.0 else EstadoOT.RESUELTA
    else:
        estado_final = EstadoOT.RESUELTA

    ot.estado = estado_final
    ot.closed_at = now
    ot.tipo_hallazgo_real = tipo_hallazgo_real
    ot.material_real = material_real
    ot.diametro_real = diametro_real
    ot.materiales_usados = materiales_json
    ot.foto_antes_url = foto_antes_url
    ot.foto_despues_url = foto_despues_url
    ot.firma_tecnico_url = firma_url
    ot.presion_verificacion_mca = presion_verificacion_mca
    ot.justificacion_forzado = justificacion_forzado
    ot.ubicacion_reparacion = func.ST_SetSRID(
        func.ST_MakePoint(lon_reparacion, lat_reparacion), 4326
    )

    await db.commit()

    return OTCerradaResponse(
        ot_id=ot.id,
        estado=ot.estado,
        closed_at=ot.closed_at,
        message="Orden de trabajo cerrada y georreferenciada en el catastro web de EMAPAT S.A.",
    )
