from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, RolUsuario
from app.models.reclamo import Reclamo
from app.schemas.reclamo import CrearReclamoRequest, ActualizarReclamoRequest, ReclamoResponse
from app.services.catalogo_service import (
    GRUPO_ESTADO_RECLAMO,
    codigo_predeterminado,
    validar_reclamo_catalogo,
)

router = APIRouter(prefix="/reclamos", tags=["Reclamos"])


@router.get("", response_model=list[ReclamoResponse], summary="Listar reclamos")
async def list_reclamos(
    estado: Optional[str] = Query(None),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Reclamo).order_by(Reclamo.fecha_registro.desc())
    if estado:
        query = query.where(Reclamo.estado == estado)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{reclamo_id}", response_model=ReclamoResponse, summary="Obtener reclamo")
async def get_reclamo(
    reclamo_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Reclamo).where(Reclamo.id == reclamo_id))
    reclamo = result.scalars().first()
    if not reclamo:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado.")
    return reclamo


@router.post(
    "",
    response_model=ReclamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo reclamo",
)
async def crear_reclamo(
    payload: CrearReclamoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.rol != RolUsuario.SUPERVISOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios con rol SUPERVISOR pueden registrar reclamos.",
        )
    data = payload.model_dump(exclude_unset=True)
    estado = data.get("estado") or await codigo_predeterminado(
        db, GRUPO_ESTADO_RECLAMO
    )
    await validar_reclamo_catalogo(
        db,
        formato=data["formato"],
        canal=data["canal_entrada"],
        tipo_problema=data["tipo_problema"],
        estado=estado,
    )
    data["estado"] = estado
    data["usuario_id"] = current_user.id
    reclamo = Reclamo(**data)
    db.add(reclamo)
    await db.commit()
    await db.refresh(reclamo)
    return reclamo


@router.patch("/{reclamo_id}", response_model=ReclamoResponse, summary="Actualizar reclamo")
async def actualizar_reclamo(
    reclamo_id: int,
    payload: ActualizarReclamoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Reclamo).where(Reclamo.id == reclamo_id))
    reclamo = result.scalars().first()
    if not reclamo:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    await validar_reclamo_catalogo(
        db,
        formato=update_data.get("formato") or reclamo.formato,
        canal=update_data.get("canal_entrada") or reclamo.canal_entrada,
        tipo_problema=update_data.get("tipo_problema") or reclamo.tipo_problema,
        estado=update_data.get("estado") or reclamo.estado,
    )
    for key, value in update_data.items():
        setattr(reclamo, key, value)

    await db.commit()
    await db.refresh(reclamo)
    return reclamo
