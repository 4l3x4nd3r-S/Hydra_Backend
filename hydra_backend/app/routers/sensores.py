from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from geoalchemy2 import WKTElement

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.excel_parser import parse_dickson_xlsx
from app.models.sensor import Sensor, LecturaPresion
from app.models.usuario import Usuario
from app.schemas.sensor import CrearSensorRequest, SensorResponse

router = APIRouter(prefix="/sensores", tags=["Sensores"])


@router.post(
    "",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo punto de medición",
)
async def crear_sensor(
    payload: CrearSensorRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Sensor).where(Sensor.point_id == payload.point_id))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un sensor con point_id '{payload.point_id}'.",
        )

    ubicacion = None
    if payload.lat is not None and payload.lon is not None:
        ubicacion = WKTElement(f"POINT({payload.lon} {payload.lat})", srid=4326)

    sensor = Sensor(
        id=payload.point_id,
        point_id=payload.point_id,
        sector_id=payload.sector_id,
        ubicacion=ubicacion,
    )
    db.add(sensor)
    await db.commit()

    return SensorResponse(
        id=sensor.id,
        point_id=sensor.point_id,
        sector_id=sensor.sector_id,
        created_at=sensor.created_at,
    )


@router.get("", response_model=list[SensorResponse], summary="Listar todos los sensores")
async def list_sensores(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sensor).order_by(Sensor.point_id))
    return result.scalars().all()


@router.post(
    "/upload-lecturas",
    summary="Cargar lecturas desde archivo Excel del datalogger DICKSON",
)
async def upload_lecturas(
    point_id: str = Form(..., description="Código del punto de medición (ej: P-61)"),
    file: UploadFile = File(..., description="Archivo .xlsx exportado del datalogger DICKSON"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser .xlsx o .xls.",
        )

    sensor_result = await db.execute(
        select(Sensor).where(Sensor.point_id == point_id)
    )
    sensor = sensor_result.scalars().first()
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún sensor con point_id '{point_id}'. Verifique el código del punto.",
        )

    contents = await file.read()
    try:
        readings = parse_dickson_xlsx(contents)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al procesar el archivo: {str(e)}",
        )

    if not readings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se encontraron lecturas válidas en el archivo.",
        )

    rows = [
        {
            "sensor_id": sensor.id,
            "timestamp": r["timestamp"],
            "presion": r["presion_mca"],
            "temperatura": r["temperatura_c"],
        }
        for r in readings
    ]

    # ON CONFLICT DO NOTHING ignora duplicados (mismo sensor + mismo timestamp)
    stmt = pg_insert(LecturaPresion).values(rows).on_conflict_do_nothing(
        index_elements=["sensor_id", "timestamp"]
    )
    result = await db.execute(stmt)
    await db.commit()

    insertadas = result.rowcount if result.rowcount >= 0 else len(rows)
    duplicadas = len(rows) - insertadas

    return {
        "sensor_id": sensor.id,
        "point_id": point_id,
        "total_en_archivo": len(rows),
        "insertadas": insertadas,
        "duplicadas_ignoradas": duplicadas,
    }
