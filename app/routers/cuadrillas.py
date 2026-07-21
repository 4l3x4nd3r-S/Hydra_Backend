from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, CargoUsuario, RolUsuario, AreaUsuario
from app.models.cuadrilla import (
    Cuadrilla,
    CuadrillaPersonal,
    RolEnCuadrilla,
    cuadrilla_numero_sequence,
    formatear_codigo_cuadrilla,
)
from app.schemas.cuadrilla import (
    CrearCuadrillaRequest, ActualizarCuadrillaRequest,
    CuadrillaResponse, CuadrillaDetalleResponse, PersonaCuadrilla,
    PersonalRequest,
)
from app.services.catalogo_service import (
    GRUPO_ESPECIALIDAD,
    validar_codigo_catalogo,
    GRUPO_FUNCION_CUADRILLA,
    mapa_etiquetas,
)

router = APIRouter(prefix="/cuadrillas", tags=["Cuadrillas"])


def build_detalle(
    cuadrilla: Cuadrilla,
    funciones: dict[str, str],
) -> CuadrillaDetalleResponse:
    lider = None
    apoyos = []
    chofer = None

    for cp in cuadrilla.personal:
        p = PersonaCuadrilla(
            id=cp.usuario.id,
            codigo_empleado=cp.usuario.codigo_empleado,
            nombre=cp.usuario.nombre,
            rol_en_cuadrilla=cp.rol_en_cuadrilla.value if cp.rol_en_cuadrilla else "",
            funcion_visible=funciones.get(
                cp.rol_en_cuadrilla.value,
                cp.rol_en_cuadrilla.value,
            ),
            es_principal=cp.rol_en_cuadrilla == RolEnCuadrilla.LIDER,
        )
        match cp.rol_en_cuadrilla:
            case RolEnCuadrilla.LIDER:
                lider = p
            case RolEnCuadrilla.APOYO:
                apoyos.append(p)
            case RolEnCuadrilla.CHOFER:
                chofer = p

    return CuadrillaDetalleResponse(
        id=cuadrilla.id,
        codigo_grupo=cuadrilla.codigo_grupo,
        especialidad=cuadrilla.especialidad,
        lider=lider,
        apoyos=apoyos,
        chofer=chofer,
    )


@router.get("", response_model=list[CuadrillaResponse], summary="Listar cuadrillas")
async def list_cuadrillas(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cuadrilla).where(Cuadrilla.activo == True).order_by(Cuadrilla.codigo_grupo))
    return result.scalars().all()


@router.get("/{cuadrilla_id}", response_model=CuadrillaDetalleResponse, summary="Obtener cuadrilla con su personal")
async def get_cuadrilla(
    cuadrilla_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cuadrilla)
        .options(selectinload(Cuadrilla.personal).selectinload(CuadrillaPersonal.usuario))
        .where(Cuadrilla.id == cuadrilla_id)
    )
    cuadrilla = result.scalars().first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada.")

    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    return build_detalle(cuadrilla, funciones)


@router.post(
    "",
    response_model=CuadrillaDetalleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva cuadrilla con personal",
)
async def crear_cuadrilla(
    payload: CrearCuadrillaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await validar_codigo_catalogo(db, GRUPO_ESPECIALIDAD, payload.especialidad)
    ids_personal = {
        payload.personal.lider_id,
        *payload.personal.apoyos_ids,
        *([payload.personal.chofer_id] if payload.personal.chofer_id else []),
    }
    await _validar_personal_mantenimiento(db, ids_personal)

    ocupados_result = await db.execute(
        select(CuadrillaPersonal.usuario_id)
        .join(Cuadrilla)
        .where(
            CuadrillaPersonal.usuario_id.in_(ids_personal),
            Cuadrilla.activo == True,
        )
    )
    ocupados = ocupados_result.scalars().all()
    if ocupados:
        raise HTTPException(
            status_code=409,
            detail="Uno o más integrantes ya pertenecen a otra cuadrilla activa.",
        )

    numero_result = await db.execute(select(cuadrilla_numero_sequence.next_value()))
    numero_cuadrilla = numero_result.scalar_one()

    cuadrilla = Cuadrilla(
        codigo_grupo=formatear_codigo_cuadrilla(numero_cuadrilla),
        especialidad=payload.especialidad,
    )
    db.add(cuadrilla)
    await db.flush()

    _agregar_personal_sync(db, cuadrilla.id, payload.personal)

    if payload.personal.chofer_id:
        usuario = await db.get(Usuario, payload.personal.chofer_id)
        if usuario is not None:
            usuario.cargo = CargoUsuario.CHOFER_CAMIONETA

    usuario = await db.get(Usuario, payload.personal.lider_id)
    if usuario is not None:
        usuario.cargo = CargoUsuario.GASFITERO_PRINCIPAL

    await db.commit()

    result = await db.execute(
        select(Cuadrilla)
        .options(selectinload(Cuadrilla.personal).selectinload(CuadrillaPersonal.usuario))
        .where(Cuadrilla.id == cuadrilla.id)
    )
    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    return build_detalle(result.scalars().first(), funciones)


def _agregar_personal_sync(db, cuadrilla_id: int, personal):
    db.add(CuadrillaPersonal(
        cuadrilla_id=cuadrilla_id,
        usuario_id=personal.lider_id,
        rol_en_cuadrilla=RolEnCuadrilla.LIDER,
    ))
    for apoyo_id in personal.apoyos_ids:
        db.add(CuadrillaPersonal(
            cuadrilla_id=cuadrilla_id,
            usuario_id=apoyo_id,
            rol_en_cuadrilla=RolEnCuadrilla.APOYO,
        ))
    if personal.chofer_id:
        db.add(CuadrillaPersonal(
            cuadrilla_id=cuadrilla_id,
            usuario_id=personal.chofer_id,
            rol_en_cuadrilla=RolEnCuadrilla.CHOFER,
        ))


async def _validar_personal_mantenimiento(db: AsyncSession, ids: set[int]) -> None:
    result = await db.execute(select(Usuario).where(Usuario.id.in_(ids)))
    usuarios = result.scalars().all()
    if len(usuarios) != len(ids):
        raise HTTPException(status_code=400, detail="Uno o más integrantes no existen.")
    if any(
        usuario.rol != RolUsuario.GASFITERO
        or usuario.area != AreaUsuario.MANTENIMIENTO
        or not usuario.activo
        for usuario in usuarios
    ):
        raise HTTPException(
            status_code=400,
            detail="Las cuadrillas solo admiten personal activo de Mantenimiento.",
        )


@router.patch("/{cuadrilla_id}", response_model=CuadrillaResponse, summary="Actualizar cuadrilla")
async def actualizar_cuadrilla(
    cuadrilla_id: int,
    payload: ActualizarCuadrillaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id))
    cuadrilla = result.scalars().first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada.")

    update_data = payload.model_dump(exclude_unset=True)
    if payload.especialidad is not None:
        await validar_codigo_catalogo(
            db, GRUPO_ESPECIALIDAD, payload.especialidad
        )
    for key, value in update_data.items():
        setattr(cuadrilla, key, value)

    await db.commit()
    await db.refresh(cuadrilla)
    return cuadrilla


@router.patch(
    "/{cuadrilla_id}/personal",
    response_model=CuadrillaDetalleResponse,
    summary="Actualizar todo el personal de una cuadrilla",
)
async def actualizar_personal_cuadrilla(
    cuadrilla_id: int,
    payload: PersonalRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cuadrilla)
        .options(selectinload(Cuadrilla.personal))
        .where(Cuadrilla.id == cuadrilla_id)
    )
    cuadrilla = result.scalars().first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada.")

    ids_personal = {
        payload.lider_id,
        *payload.apoyos_ids,
        *([payload.chofer_id] if payload.chofer_id is not None else []),
    }
    await _validar_personal_mantenimiento(db, ids_personal)

    ocupados_result = await db.execute(
        select(CuadrillaPersonal.usuario_id)
        .join(Cuadrilla)
        .where(
            CuadrillaPersonal.usuario_id.in_(ids_personal),
            CuadrillaPersonal.cuadrilla_id != cuadrilla_id,
            Cuadrilla.activo == True,
        )
    )
    ocupados = ocupados_result.scalars().all()
    if ocupados:
        raise HTTPException(
            status_code=409,
            detail="Uno o más integrantes ya pertenecen a otra cuadrilla activa.",
        )

    lider_anterior = next(
        (
            integrante.usuario_id
            for integrante in cuadrilla.personal
            if integrante.rol_en_cuadrilla == RolEnCuadrilla.LIDER
        ),
        None,
    )

    for integrante in list(cuadrilla.personal):
        await db.delete(integrante)
    await db.flush()
    _agregar_personal_sync(db, cuadrilla_id, payload)

    if lider_anterior is not None and lider_anterior != payload.lider_id:
        usuario_anterior = await db.get(Usuario, lider_anterior)
        if (
            usuario_anterior is not None
            and usuario_anterior.cargo == CargoUsuario.GASFITERO_PRINCIPAL
        ):
            usuario_anterior.cargo = CargoUsuario.GASFITERO

    nuevo_lider = await db.get(Usuario, payload.lider_id)
    if nuevo_lider is not None:
        nuevo_lider.cargo = CargoUsuario.GASFITERO_PRINCIPAL

    await db.commit()

    result = await db.execute(
        select(Cuadrilla)
        .options(
            selectinload(Cuadrilla.personal).selectinload(
                CuadrillaPersonal.usuario
            )
        )
        .where(Cuadrilla.id == cuadrilla_id)
        .execution_options(populate_existing=True)
    )
    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    return build_detalle(result.scalars().first(), funciones)


@router.delete(
    "/{cuadrilla_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar cuadrilla",
)
async def eliminar_cuadrilla(
    cuadrilla_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id))
    cuadrilla = result.scalars().first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada.")

    from app.models.orden_servicio import OrdenServicio
    ordenes_activas = await db.execute(
        select(OrdenServicio.id).where(
            OrdenServicio.cuadrilla_id == cuadrilla_id,
            OrdenServicio.estado_orden.in_(["ASIGNADO", "EN_PROCESO"])
        )
    )
    if ordenes_activas.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Esta cuadrilla tiene órdenes de servicio en proceso o asignadas. Finalícelas o reasígnelas antes de eliminarla."
        )

    cuadrilla.activo = False
    await db.commit()


@router.post(
    "/{cuadrilla_id}/personal/{usuario_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Agregar personal a una cuadrilla",
)
async def agregar_personal(
    cuadrilla_id: int,
    usuario_id: int,
    rol: RolEnCuadrilla = RolEnCuadrilla.APOYO,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cuadrilla = await db.execute(select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id))
    if not cuadrilla.scalars().first():
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada.")

    await _validar_personal_mantenimiento(db, {usuario_id})

    existing = await db.execute(
        select(CuadrillaPersonal).where(
            CuadrillaPersonal.cuadrilla_id == cuadrilla_id,
            CuadrillaPersonal.usuario_id == usuario_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="El usuario ya pertenece a esta cuadrilla.")

    cp = CuadrillaPersonal(cuadrilla_id=cuadrilla_id, usuario_id=usuario_id, rol_en_cuadrilla=rol)
    db.add(cp)
    await db.commit()
    return {"ok": True}


@router.delete(
    "/{cuadrilla_id}/personal/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar personal de una cuadrilla",
)
async def quitar_personal(
    cuadrilla_id: int,
    usuario_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CuadrillaPersonal).where(
            CuadrillaPersonal.cuadrilla_id == cuadrilla_id,
            CuadrillaPersonal.usuario_id == usuario_id,
        )
    )
    cp = result.scalars().first()
    if not cp:
        raise HTTPException(status_code=404, detail="El usuario no pertenece a esta cuadrilla.")

    await db.delete(cp)
    await db.commit()
