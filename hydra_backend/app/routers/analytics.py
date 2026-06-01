import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.functions import ST_AsGeoJSON

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.orden_trabajo import OrdenTrabajo, EstadoOT
from app.models.usuario import Usuario

router = APIRouter(prefix="/analytics", tags=["Analítica"])


@router.get("/kpis", summary="Indicadores de gestión (KPIs)")
async def get_kpis(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(select(func.count(OrdenTrabajo.id)))
    total = total_result.scalar()

    resueltas_result = await db.execute(
        select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.estado == EstadoOT.RESUELTA)
    )
    resueltas = resueltas_result.scalar()

    pendientes_result = await db.execute(
        select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.estado == EstadoOT.PENDIENTE)
    )
    pendientes = pendientes_result.scalar()

    forzadas_result = await db.execute(
        select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.estado == EstadoOT.FORZADA)
    )
    forzadas = forzadas_result.scalar()

    mttr_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", OrdenTrabajo.closed_at - OrdenTrabajo.started_at) / 60
            )
        ).where(
            OrdenTrabajo.closed_at.isnot(None),
            OrdenTrabajo.started_at.isnot(None),
        )
    )
    mttr_minutos = mttr_result.scalar()

    return {
        "total_ots": total,
        "resueltas": resueltas,
        "pendientes": pendientes,
        "forzadas": forzadas,
        "mttr_promedio_minutos": round(float(mttr_minutos), 2) if mttr_minutos else None,
    }


@router.get("/catastro", summary="Catastro de reparaciones georeferenciadas (GeoJSON)")
async def get_catastro(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            OrdenTrabajo.id,
            OrdenTrabajo.estado,
            OrdenTrabajo.prioridad,
            OrdenTrabajo.sensor_id,
            OrdenTrabajo.closed_at,
            OrdenTrabajo.tipo_hallazgo_real,
            OrdenTrabajo.material_real,
            OrdenTrabajo.diametro_real,
            OrdenTrabajo.presion_verificacion_mca,
            ST_AsGeoJSON(OrdenTrabajo.ubicacion_reparacion).label("geojson"),
        ).where(
            OrdenTrabajo.ubicacion_reparacion.isnot(None)
        )
    )
    rows = result.all()

    features = []
    for row in rows:
        if not row.geojson:
            continue
        features.append({
            "type": "Feature",
            "geometry": json.loads(row.geojson),
            "properties": {
                "ot_id": row.id,
                "estado": row.estado,
                "prioridad": row.prioridad,
                "sensor_id": row.sensor_id,
                "closed_at": row.closed_at.isoformat() if row.closed_at else None,
                "tipo_hallazgo": row.tipo_hallazgo_real,
                "material": row.material_real,
                "diametro": row.diametro_real,
                "presion_verificacion_mca": float(row.presion_verificacion_mca) if row.presion_verificacion_mca else None,
            },
        })

    return {
        "type": "FeatureCollection",
        "total": len(features),
        "features": features,
    }
