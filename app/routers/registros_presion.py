import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.excel_parser import parse_dickson_xlsx
from app.models.usuario import Usuario
from app.models.punto_presion import PuntoPresion
from app.models.registro_presion import RegistroPresion
from app.schemas.registro_presion import (
    CrearRegistroPresionRequest, RegistroPresionResponse, BulkRegistrosResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registros-presion", tags=["Registros de Presión"])


@router.get(
    "/punto/{punto_id}",
    response_model=list[RegistroPresionResponse],
    summary="Listar registros de un punto de presión",
)
async def list_registros(
    punto_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RegistroPresion)
        .where(RegistroPresion.punto_presion_id == punto_id)
        .order_by(desc(RegistroPresion.fecha_hora))
        .limit(2000)
    )
    return result.scalars().all()


@router.get(
    "/punto/{punto_id}/ultimo",
    response_model=RegistroPresionResponse,
    summary="Último registro de un punto de presión",
)
async def ultimo_registro(
    punto_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RegistroPresion)
        .where(RegistroPresion.punto_presion_id == punto_id)
        .order_by(desc(RegistroPresion.fecha_hora))
        .limit(1)
    )
    registro = result.scalars().first()
    if not registro:
        raise HTTPException(status_code=404, detail="No hay registros para este punto.")
    return registro


@router.post(
    "",
    response_model=RegistroPresionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una lectura de presión",
)
async def crear_registro(
    payload: CrearRegistroPresionRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    punto = await db.execute(
        select(PuntoPresion).where(PuntoPresion.id == payload.punto_presion_id)
    )
    if not punto.scalars().first():
        raise HTTPException(status_code=404, detail="Punto de presión no encontrado.")

    registro = RegistroPresion(**payload.model_dump())
    db.add(registro)
    await db.commit()
    await db.refresh(registro)
    return registro


@router.post("/bulk", response_model=BulkRegistrosResponse, summary="Registrar múltiples lecturas")
async def crear_registros_bulk(
    payload: list[CrearRegistroPresionRequest],
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload:
        raise HTTPException(status_code=400, detail="Lista de registros vacía.")

    rows = [
        {
            "punto_presion_id": r.punto_presion_id,
            "fecha_hora": r.fecha_hora,
            "presion_mca": r.presion_mca,
            "temperatura_c": r.temperatura_c,

        }
        for r in payload
    ]

    stmt = pg_insert(RegistroPresion).values(rows).on_conflict_do_nothing(
        index_elements=["punto_presion_id", "fecha_hora"]
    )
    result = await db.execute(stmt)
    await db.commit()

    insertados = result.rowcount if result.rowcount >= 0 else len(rows)
    duplicados = len(rows) - insertados

    return BulkRegistrosResponse(
        insertados=insertados,
        duplicados_ignorados=duplicados,
        total_enviados=len(rows),
    )


@router.post(
    "/upload-excel",
    summary="Cargar registros desde archivo Excel del datalogger DICKSON",
)
async def upload_excel(
    file: UploadFile = File(..., description="Archivo .xlsx exportado del datalogger"),
    codigo_punto: Optional[str] = Form(None, description="Código del punto de presión (ej: TRIUNFO_P-02)"),
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

    if codigo_punto is None:
        return {
            "success": True,
            "message": "Archivo subido exitosamente",
            "data": {
                "filename": original_filename,
                "size": f"{size_kb} KB",
            },
        }

    punto_result = await db.execute(
        select(PuntoPresion).where(PuntoPresion.codigo_punto == codigo_punto)
    )
    punto = punto_result.scalars().first()
    if not punto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún punto de presión con código '{codigo_punto}'.",
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
            "punto_presion_id": punto.id,
            "fecha_hora": r["timestamp"],
            "presion_mca": r["presion_mca"],
            "temperatura_c": r["temperatura_c"],
        }
        for r in readings
    ]

    stmt = pg_insert(RegistroPresion).values(rows).on_conflict_do_nothing(
        index_elements=["punto_presion_id", "fecha_hora"]
    )
    result = await db.execute(stmt)
    await db.commit()

    insertadas = result.rowcount if result.rowcount >= 0 else len(rows)
    duplicadas = len(rows) - insertadas

    return {
        "punto_id": punto.id,
        "codigo_punto": codigo_punto,
        "total_en_archivo": len(rows),
        "insertadas": insertadas,
        "duplicadas_ignoradas": duplicadas,
    }


@router.post(
    "/upload-excel-bulk",
    summary="Cargar masivamente registros desde múltiples archivos Excel",
)
async def upload_excel_bulk(
    files: list[UploadFile] = File(..., description="Archivos .xlsx exportados de dataloggers"),
    prefix: Optional[str] = Form(None, description="Prefijo opcional (ej: TRIUNFO_) para evitar conflictos si se repite P-01"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import re
    resultados = []
    
    for file in files:
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            resultados.append({"file": file.filename, "status": "Error: Extensión inválida"})
            continue
            
        # Extraer el código P-XX con regex
        match = re.search(r'(P-\d+)', file.filename, re.IGNORECASE)
        if not match:
            resultados.append({"file": file.filename, "status": "Error: No se encontró P-XX en el nombre"})
            continue
            
        codigo_extraido = match.group(1).upper()
        if prefix:
            # Si el usuario olvida el guión bajo (ej. escribe TRIUNFO en vez de TRIUNFO_), se lo agregamos automáticamente
            prefijo_limpio = prefix if prefix.endswith('_') else f"{prefix}_"
            codigo_extraido = f"{prefijo_limpio}{codigo_extraido}"
            
        # Buscar el punto en la DB (usando endswith por si el prefijo falta)
        punto_result = await db.execute(
            select(PuntoPresion).where(PuntoPresion.codigo_punto.endswith(codigo_extraido))
        )
        puntos = punto_result.scalars().all()
        
        if not puntos:
            resultados.append({"file": file.filename, "status": f"Error: Punto {codigo_extraido} no encontrado"})
            continue
        if len(puntos) > 1:
            resultados.append({"file": file.filename, "status": f"Error: Múltiples puntos coinciden con {codigo_extraido}. Usa el parámetro prefix (ej. PM_ o TRIUNFO_)."})
            continue
            
        punto = puntos[0]
        
        contents = await file.read()
        try:
            readings = parse_dickson_xlsx(contents)
            if not readings:
                resultados.append({"file": file.filename, "status": "Error: Sin lecturas válidas"})
                continue
                
            rows = [
                {
                    "punto_presion_id": punto.id,
                    "fecha_hora": r["timestamp"],
                    "presion_mca": r["presion_mca"],
                    "temperatura_c": r["temperatura_c"],
                }
                for r in readings
            ]
            
            stmt = pg_insert(RegistroPresion).values(rows).on_conflict_do_nothing(
                index_elements=["punto_presion_id", "fecha_hora"]
            )
            result = await db.execute(stmt)
            await db.commit()
            
            insertadas = result.rowcount if result.rowcount >= 0 else len(rows)
            duplicadas = len(rows) - insertadas
            
            resultados.append({
                "file": file.filename,
                "status": "OK",
                "insertadas": insertadas,
                "duplicadas_ignoradas": duplicadas,
                "codigo_punto_detectado": punto.codigo_punto
            })
            
        except Exception as e:
            resultados.append({"file": file.filename, "status": f"Error: {str(e)}"})
            
    return {"resultados": resultados}

