from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.elemento_red import ElementoRed
from app.schemas.elemento_red import CrearElementoRedRequest, ActualizarElementoRedRequest, ElementoRedResponse

router = APIRouter(prefix="/elementos-red", tags=["Elementos de Red"])


@router.get("", response_model=list[ElementoRedResponse], summary="Listar elementos de red")
async def list_elementos(
    sector_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ElementoRed).order_by(ElementoRed.codigo_plano)
    if sector_id:
        query = query.where(ElementoRed.sector_id == sector_id)
    if tipo:
        query = query.where(ElementoRed.tipo == tipo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{elemento_id}", response_model=ElementoRedResponse, summary="Obtener elemento de red")
async def get_elemento(
    elemento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ElementoRed).where(ElementoRed.id == elemento_id))
    elemento = result.scalars().first()
    if not elemento:
        raise HTTPException(status_code=404, detail="Elemento de red no encontrado.")
    return elemento


@router.post(
    "",
    response_model=ElementoRedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo elemento de red",
)
async def crear_elemento(
    payload: CrearElementoRedRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    elemento = ElementoRed(**payload.model_dump())
    db.add(elemento)
    await db.commit()
    await db.refresh(elemento)
    return elemento


@router.patch("/{elemento_id}", response_model=ElementoRedResponse, summary="Actualizar elemento de red")
async def actualizar_elemento(
    elemento_id: int,
    payload: ActualizarElementoRedRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ElementoRed).where(ElementoRed.id == elemento_id))
    elemento = result.scalars().first()
    if not elemento:
        raise HTTPException(status_code=404, detail="Elemento de red no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(elemento, key, value)

    await db.commit()
    await db.refresh(elemento)
    return elemento


@router.delete(
    "/{elemento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar elemento de red",
)
async def eliminar_elemento(
    elemento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ElementoRed).where(ElementoRed.id == elemento_id))
    elemento = result.scalars().first()
    if not elemento:
        raise HTTPException(status_code=404, detail="Elemento de red no encontrado.")

    await db.delete(elemento)
    await db.commit()
