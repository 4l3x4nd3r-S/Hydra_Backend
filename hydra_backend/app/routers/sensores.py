import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from geoalchemy2 import WKTElement

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_supabase
from app.core.excel_parser import parse_dickson_xlsx
from app.core.ml_predictor import detectar_anomalias
from app.models.sensor import Sensor, LecturaPresion
from app.models.alerta import Alerta, EstadoAlerta
from app.models.usuario import Usuario
from app.schemas.sensor import CrearSensorRequest, SensorResponse

logger = logging.getLogger(__name__)

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
    sensor_id = payload.id or payload.point_id

    existing = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un sensor con id '{sensor_id}'.",
        )

    # Si sector_id no existe en la BD, lo ignoramos (no causa error 500)
    sector_id_valido = None
    if payload.sector_id is not None:
        from app.models.sector import Sector as SectorModel
        sector_check = await db.execute(
            select(SectorModel).where(SectorModel.id == payload.sector_id)
        )
        if sector_check.scalars().first():
            sector_id_valido = payload.sector_id

    ubicacion = None
    if payload.lat is not None and payload.lon is not None:
        ubicacion = WKTElement(f"POINT({payload.lon} {payload.lat})", srid=4326)

    sensor = Sensor(
        id=sensor_id,
        point_id=payload.point_id,
        sector_id=sector_id_valido,
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
    file: UploadFile = File(..., description="Archivo .xlsx exportado del datalogger"),
    point_id: Optional[str] = Form(None, description="Código del punto de medición (ej: P-61). Opcional."),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser .xlsx o .xls.",
        )

    contents = await file.read()
    original_filename = file.filename
    size_kb = round(len(contents) / 1024, 2)

    # Guardar siempre en storage para trazabilidad
    try:
        from datetime import datetime as _dt
        ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "xlsx"
        ts = _dt.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = point_id if point_id else "sin-punto"
        storage_path = f"excel-lecturas/{prefix}_{ts}_{original_filename}"
        supabase = get_supabase()
        supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            path=storage_path,
            file=contents,
            file_options={
                "content-type": file.content_type or "application/octet-stream",
                "upsert": "true",
            },
        )
    except Exception as exc:
        logger.warning("No se pudo guardar en storage: %s", exc)

    # ── Sin point_id: solo confirmar ─────────────────────────────────────────
    if point_id is None:
        return {
            "success": True,
            "message": "Archivo subido exitosamente",
            "data": {
                "filename": original_filename,
                "size": f"{size_kb} KB",
            },
        }
    # ─────────────────────────────────────────────────────────────────────────

    sensor_result = await db.execute(
        select(Sensor).where(Sensor.point_id == point_id)
    )
    sensor = sensor_result.scalars().first()
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún sensor con point_id '{point_id}'. Verifique el código del punto.",
        )

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

    # ── Inferencia ML ────────────────────────────────────────────────────────
    alertas_creadas = 0
    anomalias_detectadas = 0
    if insertadas > 0:
        try:
            hist_result = await db.execute(
                select(
                    LecturaPresion.timestamp,
                    LecturaPresion.presion,
                    LecturaPresion.temperatura,
                )
                .where(LecturaPresion.sensor_id == sensor.id)
                .order_by(desc(LecturaPresion.timestamp))
                .limit(8640 + insertadas)  # 30 días de contexto histórico
            )
            historial = [
                {"timestamp": r.timestamp, "presion": r.presion, "temperatura": r.temperatura}
                for r in reversed(hist_result.all())
            ]

            anomalias = detectar_anomalias(historial, n_nuevas=insertadas)
            anomalias_detectadas = len(anomalias)

            if anomalias:
                peor = max(anomalias, key=lambda x: x["probabilidad"])
                tipo = "PRESION_BAJA" if peor["presion_mca"] < 10 else "ANOMALIA"
                nueva_alerta = Alerta(
                    sensor_id=sensor.id,
                    tipo=tipo,
                    nivel=peor["nivel"],
                    estado=EstadoAlerta.PENDIENTE,
                    descripcion=(
                        f"{len(anomalias)} lectura(s) anómala(s) detectadas en {point_id}. "
                        f"Presión crítica: {peor['presion_mca']} mH2O "
                        f"(confianza: {peor['probabilidad']:.0%})"
                    ),
                    presion_detectada_mca=peor["presion_mca"],
                )
                db.add(nueva_alerta)
                await db.commit()
                alertas_creadas = 1
        except Exception as exc:
            logger.warning("Inferencia ML omitida: %s", exc)
    # ─────────────────────────────────────────────────────────────────────────

    return {
        "sensor_id": sensor.id,
        "point_id": point_id,
        "total_en_archivo": len(rows),
        "insertadas": insertadas,
        "duplicadas_ignoradas": duplicadas,
        "anomalias_detectadas": anomalias_detectadas,
        "alertas_creadas": alertas_creadas,
    }
