# GEOR-EMAPAT: Especificaciones Técnicas del Backend y Base de Datos (FastAPI + PostgreSQL)

Este documento contiene las especificaciones, modelos y esquemas SQL para el desarrollo del Backend (FastAPI) y la Base de Datos Relacional Espacial (PostgreSQL + PostGIS) del sistema de detección y ruteo de fugas **GEOR-EMAPAT**.

---

## 1. Stack Tecnológico Backend & Base de Datos
*   **Base de Datos:** PostgreSQL 16 + Extensión Espacial **PostGIS** (Imprescindible para georreferenciación)
*   **Framework API:** FastAPI (Python 3.12)
*   **Asincronía y Concurrencia:** `uvicorn` (ASGI Server) + `asyncio`
*   **Driver Asíncrono de Base de Datos:** `asyncpg`
*   **ORM de Python:** SQLAlchemy 2.0 (Configurado con motor asíncrono `AsyncSession`)
*   **Gestión de Migraciones:** `Alembic`
*   **Validaciones y Serialización:** Pydantic v2 (Validación ultrarrápida de tipos de datos JSON)

---

## 2. Esquema Relacional de Base de Datos (PostgreSQL + PostGIS DDL)

El esquema soporta georreferenciación de activos mediante datos geométricos y espaciales. Debe ser ejecutado directamente en PostgreSQL tras habilitar la extensión espacial:

```sql
-- 1. Habilitar soporte para datos geométricos y consultas espaciales
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Sectores Hidráulicos de la EPS (El Triunfo y Puerto Maldonado)
CREATE TABLE sectores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    geometria GEOMETRY(MultiPolygon, 4326) -- Delimitación espacial poligonal
);

-- 3. Usuarios de la Empresa de Agua (ROF de EMAPAT S.A.)
CREATE TYPE rol_usuario AS ENUM ('GERENTE', 'JEFE_OFICINA', 'ESPECIALISTA', 'TECNICO_CAMPO');
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    rol rol_usuario NOT NULL,
    cuadrilla_nombre VARCHAR(100), -- Identificación de la cuadrilla operativa
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Sensores de Presión (Macromedición en Pozos y Tramos)
CREATE TABLE sensores (
    id VARCHAR(50) PRIMARY KEY, -- Código del sensor (Ej: 'DL-01')
    point_id VARCHAR(50) UNIQUE NOT NULL, -- Código de punto de presión (Ej: 'P-01')
    sector_id INTEGER REFERENCES sectores(id),
    ubicacion GEOMETRY(Point, 4326), -- Ubicación GPS exacta del nodo sensor
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabla de Ingesta de Presiones (Historial 5-Minutos)
CREATE TABLE lecturas_presion (
    id BIGSERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) REFERENCES sensores(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    presion NUMERIC(5,2) NOT NULL, -- en MCA (Metros de Columna de Agua)
    temperatura NUMERIC(4,2), -- en °C (opcional en sensores avanzados)
    UNIQUE(sensor_id, timestamp)
);
-- Índice compuesto de alta velocidad para series temporales
CREATE INDEX idx_lecturas_sensor_time ON lecturas_presion(sensor_id, timestamp DESC);

-- 6. Ingesta de Reclamos Comerciales (Datos provenientes de SYSCO)
CREATE TABLE reclamos (
    id SERIAL PRIMARY KEY,
    nro_reclamo VARCHAR(50) UNIQUE NOT NULL,
    codigo_cliente VARCHAR(50) NOT NULL,
    fecha_reclamo TIMESTAMP NOT NULL,
    tipo_reclamo VARCHAR(150) NOT NULL, -- Ej: 'FUGA EN CALLE' o 'FALTA DE PRESION'
    direccion TEXT NOT NULL,
    urbanizacion VARCHAR(150),
    sector_id INTEGER REFERENCES sectores(id),
    ubicacion GEOMETRY(Point, 4326), -- Geolocalización aproximada de la queja
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Órdenes de Trabajo de Reparación (OT)
CREATE TYPE estado_ot AS ENUM ('PENDIENTE', 'EN_PROCESO', 'RESUELTA', 'FORZADA');
CREATE TYPE prioridad_ot AS ENUM ('MEDIA', 'ALTA', 'CRITICA');
CREATE TABLE ordenes_trabajo (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) REFERENCES sensores(id),
    sector_id INTEGER REFERENCES sectores(id),
    asignado_a INTEGER REFERENCES usuarios(id), -- ID del técnico o cuadrilla
    estado estado_ot DEFAULT 'PENDIENTE',
    prioridad prioridad_ot NOT NULL,
    
    -- Tiempos Operativos (Medición de MTTR de EMAPAT)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    closed_at TIMESTAMP,
    
    -- Reporte de Inspección Real (Carga desde App Móvil)
    tipo_hallazgo_real VARCHAR(50), -- 'ROTURA' / 'FUGA' / 'FALSA ALARMA'
    material_real VARCHAR(50), -- 'ASBESTO CEMENTO' / 'PVC' / 'HDPE'
    diametro_real VARCHAR(20), -- '2"', '3"', '4"', '6"', etc.
    materiales_usados JSONB, -- Array de inventario consumido en la reparación
    foto_antes_url VARCHAR(255),
    foto_despues_url VARCHAR(255),
    ubicacion_reparacion GEOMETRY(Point, 4326), -- Punto GPS de reparación validado
    presion_verificacion_mca NUMERIC(5,2), -- Medición leída durante validación
    justificacion_forzado TEXT, -- Justificación en caso de baja presión persistente
    firma_tecnico_url VARCHAR(255)
);
CREATE INDEX idx_ot_estado_asignado ON ordenes_trabajo(asignado_a, estado);
```

---

## 3. Arquitectura del Proyecto FastAPI (Clean Architecture)

Estructura modular basada en controladores, esquemas y modelos ORM asíncronos:

```
backend_geor_emapat/
├── alembic/                  # Migraciones y versionamiento de DB
├── app/
│   ├── __init__.py
│   ├── main.py               # Instancia central y middlewares ASGI
│   ├── core/
│   │   ├── config.py         # Carga y validación de variables de entorno (.env)
│   │   ├── security.py       # Algoritmos JWT y Hashing (Passlib / bcrypt)
│   │   └── database.py       # Configuración del motor asíncrono asyncpg
│   ├── models/               # Modelos ORM SQLAlchemy
│   │   ├── usuario.py
│   │   ├── sensor.py
│   │   └── orden_trabajo.py
│   ├── schemas/              # Validación JSON de entrada/salida (Pydantic)
│   │   ├── auth.py
│   │   └── ot.py
│   └── routers/              # Rutas divididas por controladores
│       ├── auth.py           # Login e identidades
│       ├── ot.py             # Flujos de la App Móvil de campo
│       └── analytics.py      # Mapas de calor y KPIs de catastro web
├── requirements.txt
└── .env
```

---

## 4. Contratos de la API REST (Especificaciones de Rutas)

### A. Login de Servidores Públicos
*   **Ruta:** `POST /api/v1/auth/login`
*   **Headers:** `Content-Type: application/json`
*   **Payload (JSON):**
    ```json
    {
      "dni": "45217896",
      "password": "mi_password_seguro"
    }
    ```
*   **Respuesta (200 OK):**
    ```json
    {
      "access_token": "ey...",
      "token_type": "bearer",
      "user": {
        "id": 12,
        "nombre": "Cuadrilla El Triunfo 02",
        "rol": "TECNICO_CAMPO"
      }
    }
    ```

### B. Listar OTs Asignadas en Campo
*   **Ruta:** `GET /api/v1/ots/assigned`
*   **Headers:** `Authorization: Bearer <JWT_TOKEN>`
*   **Respuesta (200 OK):**
    ```json
    [
      {
        "id": 104,
        "sensor_id": "DL-02",
        "point_id": "TRIUNFO_P-02",
        "prioridad": "CRITICA",
        "estado": "PENDIENTE",
        "created_at": "2026-06-01T04:22:00Z",
        "ubicacion_estimada": {
          "lat": -12.5934,
          "lon": -69.1923
        }
      }
    ]
    ```

### C. Iniciar Temporizador de Reparación (MTTR)
*   **Ruta:** `POST /api/v1/ots/{ot_id}/start`
*   **Respuesta (200 OK):**
    ```json
    {
      "message": "OT iniciada con éxito. Temporizador de respuesta iniciado.",
      "started_at": "2026-06-01T05:48:10Z"
    }
    ```

### D. Ping de Validación Hidráulica
*   **Ruta:** `GET /api/v1/ots/{ot_id}/verify-pressure`
*   **Descripción:** Consulta la última lectura en tiempo real del sensor asignado al sector de la OT y determina si la presión es superior a 15 mca (lo que verifica que la tubería fue sellada con éxito).
*   **Respuesta (200 OK):**
    ```json
    {
      "ot_id": 104,
      "sensor_id": "DL-02",
      "presion_actual_mca": 16.45,
      "presion_recuperada": true,
      "mensaje": "Presión normalizada. Se autoriza el cierre completo de la orden."
    }
    ```

### E. Cierre Completo de la Orden de Trabajo
*   **Ruta:** `POST /api/v1/ots/{ot_id}/close`
*   **Headers:** `Content-Type: multipart/form-data` (Requerido para el envío binario de firmas e imágenes de inspección)
*   **Carga útil (Form Fields):**
    *   `tipo_hallazgo_real` (Texto): 'ROTURA' o 'FUGA'
    *   `material_real` (Texto): 'ASBESTO CEMENTO', 'PVC', 'HDPE' o 'HIERRO FUNDIDO'
    *   `diametro_real` (Texto): '4"' o '6"'
    *   `materiales_usados` (Texto JSON): `{"abrazaderas": 1, "niples": 2}`
    *   `lat_reparacion` (Decimal): -12.5935
    *   `lon_reparacion` (Decimal): -69.1924
    *   `presion_verificacion_mca` (Decimal): 16.45
    *   `justificacion_forzado` (Texto, Opcional): "..."
    *   `foto_antes` (Archivo Binario)
    *   `foto_despues` (Archivo Binario)
    *   `firma_tecnico` (Archivo Binario)
*   **Respuesta (200 OK):**
    ```json
    {
      "ot_id": 104,
      "estado": "RESUELTA",
      "closed_at": "2026-06-01T06:12:00Z",
      "message": "Orden de trabajo cerrada y georreferenciada en el catastro web de EMAPAT S.A."
    }
    ```

---

## 5. Ejemplo de Ruta Asíncrona en FastAPI (Python)

El siguiente fragmento de código representa el controlador FastAPI para la verificación hidráulica automática mediante sensores de presión:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.orden_trabajo import OrdenTrabajo
from app.models.sensor import LecturaPresion
from app.schemas.ot import ControlPresionResponse

router = APIRouter(prefix="/ots", tags=["Ordenes de Trabajo"])

@router.get("/{ot_id}/verify-pressure", response_model=ControlPresionResponse)
async def verify_hydraulic_pressure(ot_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Obtener la Orden de Trabajo
    ot_query = await db.execute(select(OrdenTrabajo).where(OrdenTrabajo.id == ot_id))
    ot = ot_query.scalars().first()
    if not ot:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")

    if not ot.sensor_id:
        raise HTTPException(status_code=400, detail="Esta OT no está vinculada a un sensor de presión.")

    # 2. Consultar la última lectura del sensor de presión en lecturas_presion
    lectura_query = await db.execute(
        select(LecturaPresion)
        .where(LecturaPresion.sensor_id == ot.sensor_id)
        .order_by(desc(LecturaPresion.timestamp))
        .limit(1)
    )
    ultima_lectura = lectura_query.scalars().first()
    
    if not ultima_lectura:
        raise HTTPException(
            status_code=404, 
            detail=f"No se registran lecturas históricas para el sensor {ot.sensor_id}."
        )

    # 3. Validar el umbral mínimo operativo de restablecimiento (15 MCA)
    mca_actual = float(ultima_lectura.presion)
    mca_umbral_minimo = 15.00
    presion_ok = mca_actual >= mca_umbral_minimo

    mensaje = (
        "Presión normalizada. Se autoriza el cierre completo de la orden."
        if presion_ok
        else "Presión de red baja. Verifique fugas adicionales en el sector antes de firmar."
    )

    return ControlPresionResponse(
        ot_id=ot.id,
        sensor_id=ot.sensor_id,
        presion_actual_mca=mca_actual,
        presion_recuperada=presion_ok,
        mensaje=mensaje
    )
```
