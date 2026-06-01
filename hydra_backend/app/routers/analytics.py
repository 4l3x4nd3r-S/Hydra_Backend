from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
