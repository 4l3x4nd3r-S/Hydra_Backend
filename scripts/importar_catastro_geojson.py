"""Importación reproducible de GeoJSON históricos hacia PostgreSQL."""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.elemento_red import ElementoRed
from app.models.punto_presion import PuntoPresion
from app.models.sector import Sector


def _features(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["features"]


async def importar(source: Path) -> None:
    async with AsyncSessionLocal() as session:
        sectores_existentes = {
            sector.nombre: sector
            for sector in (await session.execute(select(Sector))).scalars().all()
        }
        elementos_existentes = {
            elemento.codigo_plano: elemento
            for elemento in (
                await session.execute(select(ElementoRed))
            ).scalars().all()
            if elemento.codigo_plano
        }
        puntos_existentes = {
            punto.codigo_punto: punto
            for punto in (
                await session.execute(select(PuntoPresion))
            ).scalars().all()
        }
        sectores_por_codigo: dict[str, Sector] = {}
        for feature in _features(source / "sectores_de_agua.geojson"):
            props = feature.get("properties") or {}
            codigo = str(props.get("sector") or "").strip().zfill(2)
            nombre = str(props.get("name") or f"Sector {codigo}").strip()
            sector = sectores_existentes.get(nombre)
            if sector is None:
                sector = Sector(nombre=nombre)
                session.add(sector)
                sectores_existentes[nombre] = sector
            sector.geometria_geojson = json.dumps(
                feature.get("geometry"), ensure_ascii=False
            )
            await session.flush()
            sectores_por_codigo[codigo] = sector

        for archivo, tipo in (
            ("valvulas_de_aire.geojson", "VALVULA_AIRE"),
            ("valvulas_seccionamiento_consolidado.geojson", "VALVULA_SECCIONAMIENTO"),
        ):
            for feature in _features(source / archivo):
                props = feature.get("properties") or {}
                coords = (feature.get("geometry") or {}).get("coordinates") or []
                if len(coords) < 2:
                    continue
                codigo = str(props.get("id") or props.get("name") or "").strip()
                if not codigo:
                    continue
                elemento = elementos_existentes.get(codigo)
                if elemento is None:
                    elemento = ElementoRed(codigo_plano=codigo)
                    session.add(elemento)
                    elementos_existentes[codigo] = elemento
                elemento.tipo = tipo
                elemento.longitud = float(coords[0])
                elemento.latitud = float(coords[1])
                elemento.estado_operativo = "ACTIVO"

        for feature in _features(source / "puntos_presion_puerto_maldonado.geojson"):
            props = feature.get("properties") or {}
            coords = (feature.get("geometry") or {}).get("coordinates") or []
            if len(coords) < 2:
                continue
            codigo = str(props.get("id") or "").strip()
            if not codigo:
                continue
            punto = puntos_existentes.get(codigo)
            if punto is None:
                punto = PuntoPresion(codigo_punto=codigo)
                session.add(punto)
                puntos_existentes[codigo] = punto
            punto.longitud = float(coords[0])
            punto.latitud = float(coords[1])
            sector_codigo = str(props.get("sector") or "").strip().zfill(2)
            sector = sectores_por_codigo.get(sector_codigo)
            punto.sector_id = sector.id if sector is not None else None

        await session.commit()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "import" / "geojson",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"No existe el directorio: {source}")
    await importar(source)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
