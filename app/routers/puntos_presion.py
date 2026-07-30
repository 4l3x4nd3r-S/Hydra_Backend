from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.punto_presion import PuntoPresion
from app.schemas.punto_presion import (
    CrearPuntoPresionRequest, ActualizarPuntoPresionRequest, PuntoPresionResponse,
    HistorialPuntoResponse, MetricasMes
)

router = APIRouter(prefix="/puntos-presion", tags=["Puntos de Presión"])

@router.get("/{punto_id}/metricas", response_model=HistorialPuntoResponse, summary="Obtener historial de métricas agrupadas por mes")
async def get_metricas_punto(
    punto_id: int,
    limit: int = Query(12, description="Cantidad máxima de meses a devolver"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validar que existe
    result = await db.execute(select(PuntoPresion).where(PuntoPresion.id == punto_id))
    punto = result.scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de presión no encontrado.")

    # Hacer la consulta agregada en BD
    query = text("""
        SELECT 
            CAST(EXTRACT(YEAR FROM fecha_hora) AS INTEGER) as year,
            CAST(EXTRACT(MONTH FROM fecha_hora) AS INTEGER) as month,
            MIN(presion_mca) as p_min,
            MAX(presion_mca) as p_max,
            AVG(presion_mca) as p_mean,
            MIN(temperatura_c) as t_min,
            MAX(temperatura_c) as t_max,
            AVG(temperatura_c) as t_mean
        FROM registros_presion
        WHERE punto_presion_id = :punto_id
        GROUP BY year, month
        ORDER BY year DESC, month DESC
        LIMIT :limit
    """)
    
    rows = await db.execute(query, {"punto_id": punto_id, "limit": limit})
    
    metricas = []
    for r in rows:
        metricas.append(MetricasMes(
            year=r[0],
            month=r[1],
            presion_min=round(float(r[2]), 2) if r[2] is not None else None,
            presion_max=round(float(r[3]), 2) if r[3] is not None else None,
            presion_prom=round(float(r[4]), 2) if r[4] is not None else None,
            temp_min=round(float(r[5]), 2) if r[5] is not None else None,
            temp_max=round(float(r[6]), 2) if r[6] is not None else None,
            temp_prom=round(float(r[7]), 2) if r[7] is not None else None
        ))
        
    return HistorialPuntoResponse(
        codigo_punto=punto.codigo_punto,
        metricas=metricas
    )


@router.get("/cobertura/arbol", summary="Obtener árbol de cobertura de dataloggers")
async def get_cobertura_dataloggers(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve la cobertura real de datos de presión en la BD.
    Formato: { "Puerto Maldonado": { "2024-01": ["P-01", "P-02"...], ... }, "El Triunfo": {...} }
    Ideal para construir un árbol de archivos en el frontend y evitar subir duplicados.
    """
    query = text("""
        SELECT 
            pp.origen,
            TO_CHAR(rp.fecha_hora, 'YYYY-MM') AS mes,
            ARRAY_AGG(DISTINCT pp.codigo_punto) AS puntos
        FROM registros_presion rp
        JOIN puntos_presion pp ON rp.punto_presion_id = pp.id
        GROUP BY pp.origen, TO_CHAR(rp.fecha_hora, 'YYYY-MM')
    """)
    rows = await db.execute(query)
    
    resultado = {}
    for r in rows:
        origen = r[0] or "Desconocido"
        mes = r[1]
        puntos = sorted(r[2]) if r[2] else []
        
        if origen not in resultado:
            resultado[origen] = {}
        resultado[origen][mes] = puntos
        
    return resultado

@router.get("", response_model=list[PuntoPresionResponse], summary="Listar puntos de presión")
async def list_puntos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PuntoPresion).order_by(PuntoPresion.codigo_punto))
    return result.scalars().all()


@router.get("/{punto_id}", response_model=PuntoPresionResponse, summary="Obtener punto de presión")
async def get_punto(
    punto_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PuntoPresion).where(PuntoPresion.id == punto_id))
    punto = result.scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de presión no encontrado.")
    return punto


@router.post(
    "",
    response_model=PuntoPresionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo punto de presión",
)
async def crear_punto(
    payload: CrearPuntoPresionRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(PuntoPresion).where(PuntoPresion.codigo_punto == payload.codigo_punto)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un punto de presión con código '{payload.codigo_punto}'.",
        )

    punto = PuntoPresion(**payload.model_dump())
    db.add(punto)
    await db.commit()
    await db.refresh(punto)
    return punto


@router.patch("/{punto_id}", response_model=PuntoPresionResponse, summary="Actualizar punto de presión")
async def actualizar_punto(
    punto_id: int,
    payload: ActualizarPuntoPresionRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PuntoPresion).where(PuntoPresion.id == punto_id))
    punto = result.scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de presión no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(punto, key, value)

    await db.commit()
    await db.refresh(punto)
    return punto


@router.delete(
    "/{punto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar punto de presión",
)
async def eliminar_punto(
    punto_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PuntoPresion).where(PuntoPresion.id == punto_id))
    punto = result.scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de presión no encontrado.")

    await db.delete(punto)
    await db.commit()
