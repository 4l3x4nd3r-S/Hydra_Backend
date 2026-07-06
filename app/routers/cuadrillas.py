from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, CargoUsuario
from app.models.cuadrilla import Cuadrilla, CuadrillaPersonal, RolEnCuadrilla
from app.schemas.cuadrilla import (
    CrearCuadrillaRequest, ActualizarCuadrillaRequest,
    CuadrillaResponse, CuadrillaDetalleResponse, PersonaCuadrilla,
)

router = APIRouter(prefix="/cuadrillas", tags=["Cuadrillas"])


def build_detalle(cuadrilla: Cuadrilla) -> CuadrillaDetalleResponse:
    lider = None
    apoyos = []
    chofer = None
    operador = None

    for cp in cuadrilla.personal:
        p = PersonaCuadrilla(
            id=cp.usuario.id,
            codigo_empleado=cp.usuario.codigo_empleado,
            nombre=cp.usuario.nombre,
            rol_en_cuadrilla=cp.rol_en_cuadrilla.value if cp.rol_en_cuadrilla else "",
        )
        match cp.rol_en_cuadrilla:
            case RolEnCuadrilla.LIDER:
                lider = p
            case RolEnCuadrilla.APOYO:
                apoyos.append(p)
            case RolEnCuadrilla.CHOFER:
                chofer = p
            case RolEnCuadrilla.OPERADOR:
                operador = p

    return CuadrillaDetalleResponse(
        id=cuadrilla.id,
        codigo_grupo=cuadrilla.codigo_grupo,
        especialidad=cuadrilla.especialidad,
        lider=lider,
        apoyos=apoyos,
        chofer=chofer,
        operador=operador,
    )


@router.get("", response_model=list[CuadrillaResponse], summary="Listar cuadrillas")
async def list_cuadrillas(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cuadrilla).order_by(Cuadrilla.codigo_grupo))
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

    return build_detalle(cuadrilla)


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
    cuadrilla = Cuadrilla(
        codigo_grupo=payload.codigo_grupo,
        especialidad=payload.especialidad,
    )
    db.add(cuadrilla)
    await db.flush()

    if payload.personal:
        _agregar_personal_sync(db, cuadrilla.id, payload.personal)

        if payload.personal.chofer_id:
            usuario = await db.get(Usuario, payload.personal.chofer_id)
            if usuario is not None:
                usuario.cargo = CargoUsuario.CHOFER

        if payload.personal.operador_id:
            usuario = await db.get(Usuario, payload.personal.operador_id)
            if usuario is not None:
                usuario.cargo = CargoUsuario.OPERADOR_MAQUINARIA

        if payload.personal.lider_id:
            usuario = await db.get(Usuario, payload.personal.lider_id)
            if usuario is not None:
                usuario.cargo = CargoUsuario.GASFITERO_PRINCIPAL

    await db.commit()

    result = await db.execute(
        select(Cuadrilla)
        .options(selectinload(Cuadrilla.personal).selectinload(CuadrillaPersonal.usuario))
        .where(Cuadrilla.id == cuadrilla.id)
    )
    return build_detalle(result.scalars().first())


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
    if personal.operador_id:
        db.add(CuadrillaPersonal(
            cuadrilla_id=cuadrilla_id,
            usuario_id=personal.operador_id,
            rol_en_cuadrilla=RolEnCuadrilla.OPERADOR,
        ))


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
    for key, value in update_data.items():
        setattr(cuadrilla, key, value)

    await db.commit()
    await db.refresh(cuadrilla)
    return cuadrilla


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

    await db.delete(cuadrilla)
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

    usuario = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    if not usuario.scalars().first():
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

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
