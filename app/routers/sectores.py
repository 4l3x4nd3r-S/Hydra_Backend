from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.sector import Sector
from app.schemas.sector import CrearSectorRequest, ActualizarSectorRequest, SectorResponse

router = APIRouter(prefix="/sectores", tags=["Sectores"])


@router.get("", response_model=list[SectorResponse], summary="Listar sectores")
async def list_sectores(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sector).order_by(Sector.nombre))
    return result.scalars().all()


@router.get("/{sector_id}", response_model=SectorResponse, summary="Obtener sector por ID")
async def get_sector(
    sector_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalars().first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")
    return sector


@router.post(
    "",
    response_model=SectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo sector",
)
async def crear_sector(
    payload: CrearSectorRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sector = Sector(**payload.model_dump())
    db.add(sector)
    await db.commit()
    await db.refresh(sector)
    return sector


@router.patch("/{sector_id}", response_model=SectorResponse, summary="Actualizar sector")
async def actualizar_sector(
    sector_id: int,
    payload: ActualizarSectorRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalars().first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sector, key, value)

    await db.commit()
    await db.refresh(sector)
    return sector


@router.delete(
    "/{sector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar sector",
)
async def eliminar_sector(
    sector_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalars().first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")

    await db.delete(sector)
    await db.commit()
