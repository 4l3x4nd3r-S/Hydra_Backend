from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from shapely.geometry import shape, Point

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.sector import Sector
from app.models.reclamo_historico import ReclamoHistorico
from app.schemas.sector import CrearSectorRequest, ActualizarSectorRequest, SectorResponse
from app.schemas.reclamo_historico import ReclamoHistoricoResponse

router = APIRouter(prefix="/sectores", tags=["Sectores"])

@router.get("/{sector_id}/reclamos-historicos", response_model=list[ReclamoHistoricoResponse], summary="Obtener últimos reclamos históricos del sector")
async def get_reclamos_historicos_by_sector(
    sector_id: int,
    limit: int = Query(50, description="Cantidad máxima de reclamos recientes a devolver"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalars().first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")
        
    if not sector.geometria_geojson:
        return []
        
    try:
        geom_dict = json.loads(sector.geometria_geojson)
        if "geometry" in geom_dict:
            poly = shape(geom_dict["geometry"])
        else:
            poly = shape(geom_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parseando polígono del sector: {str(e)}")
        
    # Traer los reclamos ordenados por fecha (limitamos a los últimos 500 para no hacer point-in-polygon a toda la DB)
    reclamos_result = await db.execute(
        select(ReclamoHistorico)
        .where(ReclamoHistorico.latitud.is_not(None))
        .order_by(ReclamoHistorico.fecha_registro.desc())
        .limit(1000)
    )
    reclamos = reclamos_result.scalars().all()
    
    reclamos_filtrados = []
    for r in reclamos:
        pt = Point(r.longitud, r.latitud)
        if poly.contains(pt):
            reclamos_filtrados.append(r)
            if len(reclamos_filtrados) >= limit:
                break
                
    return reclamos_filtrados



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
