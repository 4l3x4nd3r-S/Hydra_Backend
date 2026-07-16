from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, RolUsuario
from app.models.cuadrilla import Cuadrilla, CuadrillaPersonal
from app.models.orden_servicio import OrdenServicio
from app.services.orden_servicio_snapshot import (
    ESTADOS_OS_ARCHIVADA,
    construir_snapshot_cuadrilla,
    cuadrilla_para_respuesta,
)
from app.schemas.orden_servicio import (
    CrearOrdenServicioRequest, ActualizarOrdenServicioRequest,
    FinalizarOrdenRequest, OrdenServicioResponse,
)

router = APIRouter(prefix="/ordenes-servicio", tags=["Órdenes de Servicio"])


def _build_os_response(o: OrdenServicio) -> dict:
    cuadrilla_data = cuadrilla_para_respuesta(o)
        
    reclamo_data = None
    if getattr(o, "reclamo", None):
        reclamo_data = {
            "id": o.reclamo.id,
            "formato": o.reclamo.formato,
            "codigo_solicitud": o.reclamo.codigo_solicitud,
            "canal_entrada": o.reclamo.canal_entrada,
            "tipo_problema": o.reclamo.tipo_problema,
            "estado": o.reclamo.estado,
            "descripcion": o.reclamo.descripcion,
            "nombre_solicitante": o.reclamo.nombre_solicitante,
            "direccion": o.reclamo.direccion,
            "numero_medidor": o.reclamo.numero_medidor,
            "telefono": o.reclamo.telefono,
            "email": o.reclamo.email,
            "fecha_registro": o.reclamo.fecha_registro,
        }

    responsable_data = None
    if getattr(o, "responsable", None):
        responsable_data = {
            "id": o.responsable.id,
            "nombre": o.responsable.nombre,
            "codigo_empleado": o.responsable.codigo_empleado,
            "cargo": o.responsable.cargo.value if o.responsable.cargo else None,
        }
        
    return {
        "id": o.id,
        "numero_orden": o.numero_orden,
        "reclamo_id": o.reclamo_id,
        "supervisor_id": o.supervisor_id,
        "cuadrilla_id": o.cuadrilla_id,
        "responsable_id": o.responsable_id,
        "sector_id": o.sector_id,
        "fecha_programacion": o.fecha_programacion,
        "fecha_ejecucion_inicio": o.fecha_ejecucion_inicio,
        "fecha_ejecucion_fin": o.fecha_ejecucion_fin,
        "estado_orden": o.estado_orden,
        "insumos_utilizados": o.insumos_utilizados,
        "observaciones_gasfitero": o.observaciones_gasfitero,
        "ruta_carpeta_evidencias": o.ruta_carpeta_evidencias,
        "created_at": o.created_at,
        "trabajo_ejecutado": getattr(o, "trabajo_ejecutado", None),
        "problemas": getattr(o, "problemas", None),
        "soluciones": getattr(o, "soluciones", None),
        "comentarios_instrucciones": getattr(o, "comentarios_instrucciones", None),
        "latitud": getattr(o, "latitud", None),
        "longitud": getattr(o, "longitud", None),
        "fotos_problema_urls": getattr(o, "fotos_problema_urls", None) or [],
        "fotos_solucion_urls": getattr(o, "fotos_solucion_urls", None) or [],
        "reclamo": reclamo_data,
        "cuadrilla": cuadrilla_data,
        "responsable": responsable_data,
    }


@router.get("", response_model=list[OrdenServicioResponse], summary="Listar órdenes de servicio")
async def list_ordenes(
    estado: Optional[str] = Query(None),
    cuadrilla_id: Optional[int] = Query(None),
    supervisor_id: Optional[int] = Query(None),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(OrdenServicio).options(
        selectinload(OrdenServicio.supervisor),
        selectinload(OrdenServicio.cuadrilla)
            .selectinload(Cuadrilla.personal)
            .selectinload(CuadrillaPersonal.usuario),
        selectinload(OrdenServicio.responsable),
        selectinload(OrdenServicio.reclamo),
    ).order_by(OrdenServicio.created_at.desc())

    if current_user.rol == RolUsuario.GASFITERO:
        user_cuadrillas_result = await db.execute(
            select(CuadrillaPersonal.cuadrilla_id)
            .where(CuadrillaPersonal.usuario_id == current_user.id)
        )
        user_cuadrilla_ids = user_cuadrillas_result.scalars().all()

        from sqlalchemy import or_
        conditions = []
        if user_cuadrilla_ids:
            conditions.append(OrdenServicio.cuadrilla_id.in_(user_cuadrilla_ids))
        conditions.append(OrdenServicio.responsable_id == current_user.id)
        query = query.where(or_(*conditions))

    if estado:
        query = query.where(OrdenServicio.estado_orden == estado)
    if cuadrilla_id:
        query = query.where(OrdenServicio.cuadrilla_id == cuadrilla_id)
    if supervisor_id:
        query = query.where(OrdenServicio.supervisor_id == supervisor_id)
        
    result = await db.execute(query)
    ordenes = result.scalars().all()
    return [_build_os_response(o) for o in ordenes]


@router.get("/{orden_id}", response_model=OrdenServicioResponse, summary="Obtener orden de servicio")
async def get_orden(
    orden_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(OrdenServicio).options(
        selectinload(OrdenServicio.supervisor),
        selectinload(OrdenServicio.cuadrilla)
            .selectinload(Cuadrilla.personal)
            .selectinload(CuadrillaPersonal.usuario),
        selectinload(OrdenServicio.responsable),
        selectinload(OrdenServicio.reclamo),
    ).where(OrdenServicio.id == orden_id)
    result = await db.execute(query)
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    if current_user.rol == RolUsuario.GASFITERO:
        user_cuadrillas_result = await db.execute(
            select(CuadrillaPersonal.cuadrilla_id)
            .where(CuadrillaPersonal.usuario_id == current_user.id)
        )
        user_cuadrilla_ids = user_cuadrillas_result.scalars().all()

        is_in_cuadrilla = orden.cuadrilla_id in user_cuadrilla_ids
        is_responsable = orden.responsable_id == current_user.id

        if not (is_in_cuadrilla or is_responsable):
            raise HTTPException(status_code=403, detail="No tienes acceso a esta orden de servicio.")

    return _build_os_response(orden)


@router.patch("/{orden_id}", response_model=OrdenServicioResponse, summary="Actualizar orden de servicio")
async def actualizar_orden(
    orden_id: int,
    payload: ActualizarOrdenServicioRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.reclamo),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
        )
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    update_data = payload.model_dump(exclude_unset=True)
    estado_actual = (orden.estado_orden or "").upper()
    if estado_actual in ESTADOS_OS_ARCHIVADA and {
        "cuadrilla_id",
        "responsable_id",
    }.intersection(update_data):
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar la asignación de una O.S. archivada.",
        )

    estado_nuevo = str(update_data.get("estado_orden", "")).upper()
    if estado_nuevo in ESTADOS_OS_ARCHIVADA and orden.cuadrilla_snapshot is None:
        orden.cuadrilla_snapshot = construir_snapshot_cuadrilla(orden.cuadrilla)

    for key, value in update_data.items():
        setattr(orden, key, value)

    await db.commit()
    await db.refresh(orden)
    
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.supervisor),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
            selectinload(OrdenServicio.reclamo),
        )
        .where(OrdenServicio.id == orden.id)
    )
    return _build_os_response(result.scalars().first())


@router.post("/{orden_id}/iniciar", response_model=OrdenServicioResponse, summary="Iniciar ejecución de la orden")
async def iniciar_orden(
    orden_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.reclamo),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
        )
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    if orden.estado_orden not in {"ASIGNADO", "EN_PROCESO", "COMPLETADO"}:
        raise HTTPException(
            status_code=400,
            detail=f"La orden no puede iniciarse porque su estado actual es '{orden.estado_orden}'.",
        )

    # El inicio debe ser idempotente para la sincronización offline. Si el
    # dispositivo perdió la respuesta después del commit, puede reintentarlo
    # sin bloquear posteriormente el envío del reporte final.
    if orden.estado_orden == "ASIGNADO":
        orden.estado_orden = "EN_PROCESO"
        orden.fecha_ejecucion_inicio = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        await db.refresh(orden)
    
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.supervisor),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
            selectinload(OrdenServicio.reclamo),
        )
        .where(OrdenServicio.id == orden.id)
    )
    return _build_os_response(result.scalars().first())


@router.post("/{orden_id}/finalizar", response_model=OrdenServicioResponse, summary="Finalizar orden de servicio")
async def finalizar_orden(
    orden_id: int,
    payload: FinalizarOrdenRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.reclamo),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
        )
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    # Una sincronización offline puede perder la respuesta después de que el
    # commit ya se realizó. En ese caso, el siguiente reintento debe confirmar
    # el resultado existente para que el dispositivo limpie su cola local.
    if orden.estado_orden == "COMPLETADO":
        return _build_os_response(orden)

    if orden.estado_orden != "EN_PROCESO":
        raise HTTPException(
            status_code=400,
            detail=f"La orden no puede finalizarse porque su estado actual es '{orden.estado_orden}'.",
        )

    orden.cuadrilla_snapshot = construir_snapshot_cuadrilla(orden.cuadrilla)
    orden.estado_orden = "COMPLETADO"
    if payload.fecha_ejecucion_fin:
        orden.fecha_ejecucion_fin = payload.fecha_ejecucion_fin.replace(tzinfo=None)
    else:
        orden.fecha_ejecucion_fin = datetime.now(timezone.utc).replace(tzinfo=None)
        
    if payload.fecha_ejecucion_inicio:
        orden.fecha_ejecucion_inicio = payload.fecha_ejecucion_inicio.replace(tzinfo=None)
    orden.insumos_utilizados = payload.insumos_utilizados
    orden.observaciones_gasfitero = payload.observaciones_gasfitero
    orden.ruta_carpeta_evidencias = payload.ruta_carpeta_evidencias
    orden.trabajo_ejecutado = payload.trabajo_ejecutado
    orden.problemas = payload.problemas
    orden.soluciones = payload.soluciones
    orden.comentarios_instrucciones = payload.comentarios_instrucciones
    orden.latitud = payload.latitud
    orden.longitud = payload.longitud
    if payload.fotos_problema_urls is not None:
        orden.fotos_problema_urls = payload.fotos_problema_urls
    if payload.fotos_solucion_urls is not None:
        orden.fotos_solucion_urls = payload.fotos_solucion_urls

    if orden.reclamo:
        orden.reclamo.estado = "CERRADO"

    await db.commit()
    await db.refresh(orden)
    
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.supervisor),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
            selectinload(OrdenServicio.reclamo),
        )
        .where(OrdenServicio.id == orden.id)
    )
    return _build_os_response(result.scalars().first())
