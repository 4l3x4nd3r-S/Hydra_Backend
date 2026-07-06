from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.usuario import Usuario, RolUsuario
from app.schemas.usuario import CrearUsuarioRequest, ActualizarUsuarioRequest, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

ROLES_ADMIN = {RolUsuario.SUPERVISOR}


async def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ROLES_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a supervisores.",
        )
    return current_user


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

    usuario = Usuario(
        codigo_empleado=payload.codigo_empleado,
        nombre=payload.nombre,
        rol=payload.rol,
        password_hash=hash_password(payload.password),
        cargo=payload.cargo,
        area=payload.area,
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
    if payload.activo is not None:
        usuario.activo = payload.activo
    if payload.password is not None:
        usuario.password_hash = hash_password(payload.password)

    await db.commit()
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
