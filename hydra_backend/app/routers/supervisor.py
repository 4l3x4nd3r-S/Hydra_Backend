from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, RolUsuario
from app.models.orden_trabajo import OrdenTrabajo, EstadoOT
from app.models.alerta import Alerta, EstadoAlerta
from app.schemas.supervisor import TecnicoResponse, CrearOTRequest, OTSupervisorResponse
from app.schemas.alerta import CrearAlertaRequest, AlertaResponse

router = APIRouter(prefix="/supervisor", tags=["Supervisor"])

ROLES_SUPERVISORES = {RolUsuario.GERENTE, RolUsuario.JEFE_OFICINA, RolUsuario.ESPECIALISTA}


async def require_supervisor(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ROLES_SUPERVISORES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a supervisores y gerentes.",
        )
    return current_user


@router.get("/tecnicos", response_model=list[TecnicoResponse], summary="Listar técnicos de campo")
async def list_tecnicos(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario)
        .where(Usuario.rol == RolUsuario.TECNICO_CAMPO)
        .order_by(Usuario.nombre)
    )
    return result.scalars().all()


@router.get("/alertas", response_model=list[AlertaResponse], summary="Listar alertas del sistema")
async def list_alertas(
    estado: Optional[str] = Query(None, description="Filtrar por estado: PENDIENTE, ATENDIDA, DESCARTADA"),
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Alerta)
        .options(
            selectinload(Alerta.ot).selectinload(OrdenTrabajo.tecnico)
        )
        .order_by(Alerta.created_at.desc())
    )
    if estado:
        query = query.where(Alerta.estado == estado.upper())
    else:
        query = query.where(Alerta.estado == EstadoAlerta.PENDIENTE)

    result = await db.execute(query)
    alertas = result.scalars().all()

    output = []
    for a in alertas:
        tecnico = a.ot.tecnico if a.ot and a.ot.tecnico else None
        output.append(AlertaResponse(
            id=a.id,
            sensor_id=a.sensor_id,
            sector_id=a.sector_id,
            tipo=a.tipo,
            nivel=a.nivel,
            estado=a.estado,
            descripcion=a.descripcion,
            presion_detectada_mca=float(a.presion_detectada_mca) if a.presion_detectada_mca else None,
            ot_id=a.ot_id,
            tecnico_id=tecnico.id if tecnico else None,
            tecnico_nombre=tecnico.nombre if tecnico else None,
            created_at=a.created_at,
            atendida_at=a.atendida_at,
            plazo_atencion_at=a.plazo_atencion_at,
        ))
    return output


@router.post(
    "/alertas",
    response_model=AlertaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear alerta manualmente (o desde modelo ML)",
)
async def crear_alerta(
    payload: CrearAlertaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alerta = Alerta(
        sensor_id=payload.sensor_id,
        sector_id=payload.sector_id,
        tipo=payload.tipo,
        nivel=payload.nivel,
        estado=EstadoAlerta.PENDIENTE,
        descripcion=payload.descripcion,
        presion_detectada_mca=payload.presion_detectada_mca,
    )
    db.add(alerta)
    await db.commit()
    await db.refresh(alerta)
    return alerta


@router.patch(
    "/alertas/{alerta_id}/descartar",
    response_model=AlertaResponse,
    summary="Descartar una alerta",
)
async def descartar_alerta(
    alerta_id: int,
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alerta).where(Alerta.id == alerta_id))
    alerta = result.scalars().first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")
    if alerta.estado != EstadoAlerta.PENDIENTE:
        raise HTTPException(status_code=400, detail=f"La alerta ya fue {alerta.estado.lower()}.")

    alerta.estado = EstadoAlerta.DESCARTADA
    alerta.atendida_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alerta)
    return alerta


@router.post(
    "/ots",
    response_model=OTSupervisorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear y asignar orden de trabajo",
)
async def crear_ot(
    payload: CrearOTRequest,
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    tecnico_result = await db.execute(
        select(Usuario).where(Usuario.id == payload.asignado_a)
    )
    tecnico = tecnico_result.scalars().first()
    if not tecnico or tecnico.rol != RolUsuario.TECNICO_CAMPO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario asignado no existe o no es técnico de campo.",
        )

    # Verificar que el sensor existe; si no, desvincularlo (no causar 500)
    sensor_id_valido = None
    if payload.sensor_id:
        from app.models.sensor import Sensor
        sensor_check = await db.execute(select(Sensor).where(Sensor.id == payload.sensor_id))
        if sensor_check.scalars().first():
            sensor_id_valido = payload.sensor_id

    alerta = None
    if payload.alerta_id:
        alerta_result = await db.execute(select(Alerta).where(Alerta.id == payload.alerta_id))
        alerta = alerta_result.scalars().first()
        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    ot = OrdenTrabajo(
        sensor_id=sensor_id_valido,
        sector_id=payload.sector_id,
        asignado_a=payload.asignado_a,
        prioridad=payload.prioridad,
        estado=EstadoOT.PENDIENTE,
    )
    db.add(ot)
    await db.flush()

    if alerta:
        alerta.estado = EstadoAlerta.ATENDIDA
        alerta.ot_id = ot.id
        alerta.atendida_at = datetime.utcnow()

    # Si viene tipo_alerta, crear una alerta automáticamente vinculada a la OT
    if payload.tipo_alerta:
        nueva_alerta = Alerta(
            sensor_id=sensor_id_valido,
            tipo=payload.tipo_alerta.upper(),
            nivel="ALTA",
            estado=EstadoAlerta.ATENDIDA,
            descripcion=f"Alerta generada al crear OT: {payload.tipo_alerta}",
            ot_id=ot.id,
            atendida_at=datetime.utcnow(),
        )
        db.add(nueva_alerta)

    await db.commit()
    await db.refresh(ot)

    return OTSupervisorResponse(
        id=ot.id,
        sensor_id=ot.sensor_id,
        sector_id=ot.sector_id,
        asignado_a=ot.asignado_a,
        tecnico_nombre=tecnico.nombre,
        estado=ot.estado,
        prioridad=ot.prioridad,
        created_at=ot.created_at,
        started_at=ot.started_at,
        closed_at=ot.closed_at,
    )


@router.get("/ots", response_model=list[OTSupervisorResponse], summary="Listar todas las órdenes de trabajo")
async def list_all_ots(
    estado: Optional[str] = Query(None, description="Filtrar: PENDIENTE, EN_PROCESO, RESUELTA, FORZADA"),
    prioridad: Optional[str] = Query(None, description="Filtrar: MEDIA, ALTA, CRITICA"),
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(OrdenTrabajo)
        .options(selectinload(OrdenTrabajo.tecnico))
        .order_by(OrdenTrabajo.created_at.desc())
    )
    if estado:
        query = query.where(OrdenTrabajo.estado == estado.upper())
    if prioridad:
        query = query.where(OrdenTrabajo.prioridad == prioridad.upper())

    result = await db.execute(query)
    ots = result.scalars().all()

    return [
        OTSupervisorResponse(
            id=ot.id,
            sensor_id=ot.sensor_id,
            sector_id=ot.sector_id,
            asignado_a=ot.asignado_a,
            tecnico_nombre=ot.tecnico.nombre if ot.tecnico else None,
            estado=ot.estado,
            prioridad=ot.prioridad,
            created_at=ot.created_at,
            started_at=ot.started_at,
            closed_at=ot.closed_at,
        )
        for ot in ots
    ]
