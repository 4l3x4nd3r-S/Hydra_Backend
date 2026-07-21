from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.schemas.catalogo import CatalogoOpcionResponse
from app.services.catalogo_service import listar_catalogo


router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


@router.get(
    "/operacion",
    response_model=list[CatalogoOpcionResponse],
    summary="Listar catálogos operativos activos",
)
async def catalogos_operacion(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await listar_catalogo(db)
