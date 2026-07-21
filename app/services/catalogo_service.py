from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import CatalogoOpcion


GRUPO_FORMATO_RECLAMO = "FORMATO_RECLAMO"
GRUPO_CANAL_RECLAMO = "CANAL_RECLAMO"
GRUPO_TIPO_PROBLEMA = "TIPO_PROBLEMA"
GRUPO_ESPECIALIDAD = "ESPECIALIDAD_CUADRILLA"
GRUPO_ESTADO_RECLAMO = "ESTADO_RECLAMO"
GRUPO_ESTADO_ORDEN = "ESTADO_ORDEN"
GRUPO_FUNCION_CUADRILLA = "FUNCION_CUADRILLA"
GRUPO_AREA_USUARIO = "AREA_USUARIO"
GRUPO_CARGO_USUARIO = "CARGO_USUARIO"


async def listar_catalogo(
    db: AsyncSession,
    *,
    grupos: set[str] | None = None,
) -> list[CatalogoOpcion]:
    query = select(CatalogoOpcion).where(CatalogoOpcion.activo.is_(True))
    if grupos:
        query = query.where(CatalogoOpcion.grupo.in_(grupos))
    query = query.order_by(
        CatalogoOpcion.grupo,
        CatalogoOpcion.orden,
        CatalogoOpcion.etiqueta,
    )
    return list((await db.execute(query)).scalars().all())


async def mapa_etiquetas(
    db: AsyncSession,
    grupo: str,
) -> dict[str, str]:
    opciones = await listar_catalogo(db, grupos={grupo})
    return {opcion.codigo: opcion.etiqueta for opcion in opciones}


async def validar_codigo_catalogo(
    db: AsyncSession,
    grupo: str,
    codigo: str,
) -> None:
    result = await db.execute(
        select(CatalogoOpcion.id).where(
            CatalogoOpcion.grupo == grupo,
            CatalogoOpcion.codigo == codigo,
            CatalogoOpcion.activo.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Opción no válida para el catálogo {grupo}.")


async def codigo_predeterminado(db: AsyncSession, grupo: str) -> str:
    result = await db.execute(
        select(CatalogoOpcion.codigo)
        .where(
            CatalogoOpcion.grupo == grupo,
            CatalogoOpcion.activo.is_(True),
            CatalogoOpcion.predeterminado.is_(True),
        )
        .order_by(CatalogoOpcion.orden)
        .limit(1)
    )
    codigo = result.scalar_one_or_none()
    if codigo is None:
        raise ValueError(f"El catálogo {grupo} no tiene una opción predeterminada.")
    return codigo


async def validar_reclamo_catalogo(
    db: AsyncSession,
    *,
    formato: str,
    canal: str,
    tipo_problema: str,
    estado: str,
) -> None:
    opciones = await listar_catalogo(
        db,
        grupos={
            GRUPO_FORMATO_RECLAMO,
            GRUPO_CANAL_RECLAMO,
            GRUPO_TIPO_PROBLEMA,
            GRUPO_ESTADO_RECLAMO,
        },
    )
    por_grupo = {
        grupo: {opcion.codigo: opcion for opcion in opciones if opcion.grupo == grupo}
        for grupo in {
            GRUPO_FORMATO_RECLAMO,
            GRUPO_CANAL_RECLAMO,
            GRUPO_TIPO_PROBLEMA,
            GRUPO_ESTADO_RECLAMO,
        }
    }
    if formato not in por_grupo[GRUPO_FORMATO_RECLAMO]:
        raise ValueError("Formato de reclamo no reconocido.")
    if canal not in por_grupo[GRUPO_CANAL_RECLAMO]:
        raise ValueError("Canal de entrada no reconocido.")
    tipo = por_grupo[GRUPO_TIPO_PROBLEMA].get(tipo_problema)
    if tipo is None:
        raise ValueError("Tipo de problema no reconocido.")
    if tipo.padre_codigo != formato:
        raise ValueError(f"El tipo de problema no corresponde al formato {formato}.")
    if estado not in por_grupo[GRUPO_ESTADO_RECLAMO]:
        raise ValueError("Estado de reclamo no reconocido.")


async def especialidad_para_formato(
    db: AsyncSession,
    formato: str | None,
) -> str | None:
    if not formato:
        return None
    result = await db.execute(
        select(CatalogoOpcion.relacionado_codigo).where(
            CatalogoOpcion.grupo == GRUPO_FORMATO_RECLAMO,
            CatalogoOpcion.codigo == formato,
            CatalogoOpcion.activo.is_(True),
        )
    )
    return result.scalar_one_or_none()
