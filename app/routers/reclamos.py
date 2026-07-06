from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.reclamo import Reclamo
from app.schemas.reclamo import CrearReclamoRequest, ActualizarReclamoRequest, ReclamoResponse

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
    if current_user.rol.value != "SUPERVISOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios con rol SUPERVISOR pueden registrar reclamos.",
        )
    data = payload.model_dump()
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
    for key, value in update_data.items():
        setattr(reclamo, key, value)

    await db.commit()
    await db.refresh(reclamo)
    return reclamo
