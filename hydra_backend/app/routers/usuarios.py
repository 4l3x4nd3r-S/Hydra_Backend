from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.usuario import Usuario, RolUsuario
from app.schemas.usuario import CrearUsuarioRequest, ActualizarUsuarioRequest, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

# Ubicaciones en tiempo real de los técnicos (en memoria)
_ubicaciones: dict[int, dict] = {}


class UbicacionPayload(BaseModel):
    lat: float
    lon: float

ROLES_ADMIN = {RolUsuario.GERENTE, RolUsuario.JEFE_OFICINA}


async def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ROLES_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a gerentes y jefes de oficina.",
        )
    return current_user


@router.patch("/me/locacion", summary="Actualizar ubicación GPS del técnico en campo")
async def actualizar_mi_locacion(
    payload: UbicacionPayload,
    current_user: Usuario = Depends(get_current_user),
):
    _ubicaciones[current_user.id] = {
        "usuario_id": current_user.id,
        "nombre": current_user.nombre,
        "lat": payload.lat,
        "lon": payload.lon,
        "actualizado_en": datetime.utcnow().isoformat(),
    }
    return {"ok": True}


@router.get("/locaciones", summary="Ver ubicaciones en tiempo real de técnicos en campo")
async def get_locaciones(current_user: Usuario = Depends(get_current_user)):
    return list(_ubicaciones.values())


@router.get("", response_model=list[UsuarioResponse], summary="Listar usuarios")
async def list_usuarios(
    rol: Optional[str] = Query(None, description="Filtrar por rol: GERENTE, JEFE_OFICINA, ESPECIALISTA, TECNICO_CAMPO"),
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
    existing = await db.execute(select(Usuario).where(Usuario.dni == payload.dni))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con DNI '{payload.dni}'.",
        )

    usuario = Usuario(
        dni=payload.dni,
        nombre=payload.nombre,
        rol=payload.rol,
        cuadrilla_nombre=payload.cuadrilla_nombre,
        hashed_password=hash_password(payload.password),
    )
    db.add(usuario)
    await db.commit()
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

    if payload.nombre is not None:
        usuario.nombre = payload.nombre
    if payload.rol is not None:
        usuario.rol = payload.rol
    if payload.cuadrilla_nombre is not None:
        usuario.cuadrilla_nombre = payload.cuadrilla_nombre
    if payload.password is not None:
        usuario.hashed_password = hash_password(payload.password)

    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario (solo si no tiene OTs asignadas)",
)
async def eliminar_usuario(
    usuario_id: int,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.orden_trabajo import OrdenTrabajo

    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario.")

    ots = await db.execute(
        select(OrdenTrabajo).where(OrdenTrabajo.asignado_a == usuario_id).limit(1)
    )
    if ots.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el usuario porque tiene órdenes de trabajo asignadas.",
        )

    await db.delete(usuario)
    await db.commit()
