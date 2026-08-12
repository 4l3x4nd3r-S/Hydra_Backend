from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.reclamo_historico import ReclamoHistorico

router = APIRouter(prefix="/reclamos-historicos", tags=["Reclamos Historicos"])

@router.get("/cobertura/arbol", summary="Cobertura de reclamos históricos agrupados por mes")
async def get_cobertura_arbol(db: AsyncSession = Depends(get_db)):
    query = select(
        func.to_char(ReclamoHistorico.fecha_registro, 'YYYY-MM').label('mes'),
        func.count(ReclamoHistorico.id).label('conteo')
    ).where(
        ReclamoHistorico.fecha_registro.isnot(None)
    ).group_by(
        'mes'
    ).order_by(
        'mes'
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return {row.mes: row.conteo for row in rows}
