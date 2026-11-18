from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.cuadrilla import Cuadrilla, CuadrillaPersonal
from app.models.usuario import Usuario, RolUsuario, EstadoPersonal
from app.schemas.usuario import CrearUsuarioRequest, ActualizarUsuarioRequest, UsuarioResponse
from app.services.catalogo_service import (
    GRUPO_AREA_USUARIO,
    GRUPO_CARGO_USUARIO,
    validar_codigo_catalogo,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

ROLES_ADMIN = {RolUsuario.SUPERVISOR}


async def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ROLES_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a supervisores.",
        )
    return current_user


async def _validar_documentos_unicos(
    db: AsyncSession,
    *,
    dni: Optional[str] = None,
    celular: Optional[str] = None,
    excluir_id: Optional[int] = None,
) -> None:
    """Comprueba DNI y celular antes del commit para dar un 409 claro."""
    if dni is not None:
        query = select(Usuario.id).where(Usuario.dni == dni)
        if excluir_id is not None:
            query = query.where(Usuario.id != excluir_id)
        if (await db.execute(query)).scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El DNI {dni} ya está registrado.",
            )
    if celular is not None:
        query = select(Usuario.id).where(Usuario.celular == celular)
        if excluir_id is not None:
            query = query.where(Usuario.id != excluir_id)
        if (await db.execute(query)).scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El celular {celular} ya está registrado.",
            )


def _conflicto_integridad(exc: IntegrityError) -> HTTPException:
    """Traduce una violación de unicidad en un 409 legible."""
    detalle = str(getattr(exc, "orig", exc))
    if "uq_usuarios_dni" in detalle:
        mensaje = "El DNI ya está registrado."
    elif "uq_usuarios_celular" in detalle:
        mensaje = "El celular ya está registrado."
    elif "codigo_empleado" in detalle:
        mensaje = "Ya existe un usuario con ese código de empleado."
    else:
        mensaje = "Los datos del usuario ya están registrados."
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensaje)


async def _cuadrilla_activa_de(db: AsyncSession, usuario_id: int) -> Optional[str]:
    result = await db.execute(
        select(Cuadrilla.codigo_grupo)
        .join(CuadrillaPersonal, CuadrillaPersonal.cuadrilla_id == Cuadrilla.id)
        .where(
            CuadrillaPersonal.usuario_id == usuario_id,
            Cuadrilla.activo.is_(True),
        )
        .limit(1)
    )
    return result.scalars().first()


@router.get("", response_model=list[UsuarioResponse], summary="Listar usuarios")
async def list_usuarios(
    rol: Optional[str] = Query(None, description="Filtrar por rol: SUPERVISOR, GASFITERO"),
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Usuario).order_by(Usuario.nombre)
    if rol:
        query = query.where(Usuario.rol == rol.upper())
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
)
async def crear_usuario(
    payload: CrearUsuarioRequest,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Usuario).where(Usuario.codigo_empleado == payload.codigo_empleado)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con código de empleado '{payload.codigo_empleado}'.",
        )

    await _validar_documentos_unicos(
        db, dni=payload.dni, celular=payload.celular
    )

    if payload.cargo is not None:
        await validar_codigo_catalogo(db, GRUPO_CARGO_USUARIO, payload.cargo)
    if payload.area is not None:
        await validar_codigo_catalogo(db, GRUPO_AREA_USUARIO, payload.area)

    usuario = Usuario(
        codigo_empleado=payload.codigo_empleado,
        nombre=payload.nombre,
        dni=payload.dni,
        celular=payload.celular,
        rol=payload.rol,
        password_hash=hash_password(payload.password),
        cargo=payload.cargo,
        area=payload.area,
        estado=EstadoPersonal.ACTIVO,
    )
    db.add(usuario)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflicto_integridad(exc)
    await db.refresh(usuario)
    return usuario


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioResponse,
    summary="Actualizar datos de un usuario",
)
async def actualizar_usuario(
    usuario_id: int,
    payload: ActualizarUsuarioRequest,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # ``model_fields_set`` distingue "no enviado" de "enviado como null".
    campos = payload.model_fields_set

    if "fecha_retorno" in campos and payload.fecha_retorno is not None:
        if payload.fecha_retorno < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de retorno no puede ser anterior a hoy.",
            )

    if "nombre" in campos and payload.nombre is not None:
        usuario.nombre = payload.nombre
    if "dni" in campos:
        if payload.dni != usuario.dni:
            await _validar_documentos_unicos(
                db, dni=payload.dni, excluir_id=usuario.id
            )
        usuario.dni = payload.dni
    if "celular" in campos:
        if payload.celular != usuario.celular:
            await _validar_documentos_unicos(
                db, celular=payload.celular, excluir_id=usuario.id
            )
        usuario.celular = payload.celular
    if payload.rol is not None:
        usuario.rol = payload.rol
    if payload.cargo is not None:
        await validar_codigo_catalogo(db, GRUPO_CARGO_USUARIO, payload.cargo)
        usuario.cargo = payload.cargo
    if payload.area is not None:
        await validar_codigo_catalogo(db, GRUPO_AREA_USUARIO, payload.area)
        usuario.area = payload.area

    # ``activo`` ya no se acepta como fuente de verdad: solo se usa como
    # compatibilidad cuando el cliente anterior no envía ``estado``.
    estado_solicitado = payload.estado
    if (
        estado_solicitado is None
        and "activo" in campos
        and payload.activo is not None
    ):
        estado_solicitado = (
            EstadoPersonal.ACTIVO
            if payload.activo
            else EstadoPersonal.RETIRADO
        )

    if estado_solicitado is not None:
        cambia_estado = estado_solicitado != usuario.estado

        if cambia_estado:
            if usuario.id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes cambiar tu propio estado.",
                )

            if estado_solicitado in (
                EstadoPersonal.AUSENTE,
                EstadoPersonal.RETIRADO,
            ):
                codigo_cuadrilla = await _cuadrilla_activa_de(db, usuario.id)
                if codigo_cuadrilla:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Primero retíralo de la cuadrilla "
                            f"{codigo_cuadrilla}."
                        ),
                    )

        if estado_solicitado == EstadoPersonal.AUSENTE:
            # Permite ampliar una ausencia ya registrada sin cambiar de estado.
            if "motivo_ausencia" in campos:
                usuario.motivo_ausencia = payload.motivo_ausencia
            if "fecha_retorno" in campos:
                usuario.fecha_retorno = payload.fecha_retorno
        else:
            # Al reincorporar o retirar no debe quedar rastro de una ausencia.
            usuario.motivo_ausencia = None
            usuario.fecha_retorno = None

        if cambia_estado:
            # El validador del modelo sincroniza ``activo`` automáticamente.
            usuario.estado = estado_solicitado

    if payload.password is not None:
        usuario.password_hash = hash_password(payload.password)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflicto_integridad(exc)
    await db.refresh(usuario)
    return usuario


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
)
async def eliminar_usuario(
    usuario_id: int,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario.")

    await db.delete(usuario)
    await db.commit()
