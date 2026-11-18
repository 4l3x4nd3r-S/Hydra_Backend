# Hydra — Backend API

Sistema de detección y ruteo de fugas de agua para **EMAPAT S.A.** (Puerto Maldonado y El Triunfo). Permite a técnicos de campo gestionar órdenes de trabajo, verificar presión hidráulica en tiempo real y registrar reparaciones georreferenciadas.

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Framework API | FastAPI (Python 3.12) |
| Base de Datos | PostgreSQL 18 + PostGIS 3.6 |
| ORM | SQLAlchemy 2.0 (async) |
| Driver BD | asyncpg |
| Migraciones | Alembic |
| Validación | Pydantic v2 |
| Autenticación | JWT (python-jose + bcrypt) |
| Servidor | Uvicorn (ASGI) |

---

## Estructura del Proyecto

```
hydra_backend/
├── alembic/                  # Migraciones de base de datos
│   └── versions/
├── app/
│   ├── core/
│   │   ├── config.py         # Variables de entorno
│   │   ├── database.py       # Motor asíncrono AsyncSession
│   │   └── security.py       # JWT y bcrypt
│   ├── models/               # Modelos ORM SQLAlchemy
│   │   ├── sector.py
│   │   ├── usuario.py
│   │   ├── sensor.py
│   │   ├── reclamo.py
│   │   └── orden_trabajo.py
│   ├── schemas/              # Esquemas Pydantic v2
│   │   ├── auth.py
│   │   └── ot.py
│   ├── routers/              # Controladores de rutas
│   │   ├── auth.py
│   │   ├── ot.py
│   │   └── analytics.py
│   └── main.py               # Instancia FastAPI y middlewares
├── .env                      # Variables de entorno (no subir a git)
├── alembic.ini
├── Procfile                  # Para despliegue en Railway
└── requirements.txt
```

---

## Instalación Local

### Requisitos previos
- Python 3.12
- PostgreSQL 18 + extensión PostGIS

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd hydra_backend

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
# Editar .env con tus credenciales de PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/hydra
SECRET_KEY=tu_clave_secreta_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# 5. Crear la base de datos en PostgreSQL
# (ejecutar en psql o DBeaver)
# CREATE DATABASE hydra;
# \c hydra
# CREATE EXTENSION IF NOT EXISTS postgis;

# 6. Aplicar migraciones
alembic upgrade head

# 7. Levantar el servidor
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`
Documentación interactiva en `http://localhost:8000/docs`

---

## Endpoints de la API

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/login` | Iniciar sesión con DNI y contraseña |

### Órdenes de Trabajo
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/ots/assigned` | Listar OTs asignadas al técnico autenticado |
| POST | `/api/v1/ots/{ot_id}/start` | Iniciar temporizador de reparación (MTTR) |
| GET | `/api/v1/ots/{ot_id}/verify-pressure` | Verificar presión hidráulica del sensor (umbral: 15 MCA) |
| POST | `/api/v1/ots/{ot_id}/close` | Cerrar OT con fotos, firma y geolocalización |

### Analítica
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/analytics/kpis` | KPIs operativos: total OTs, MTTR promedio, estado |

---

## Roles de Usuario

| Rol | Descripción |
|---|---|
| `GERENTE` | Acceso total al sistema |
| `JEFE_OFICINA` | Gestión de OTs y reportes |
| `ESPECIALISTA` | Análisis y catastro |
| `TECNICO_CAMPO` | App móvil: gestión de reparaciones en campo |

---

## Estados del Personal

El personal ya no se crea y borra en cada rotación: la cuenta permanece y
cambia de estado.

| Estado | Inicia sesión | Asignable a cuadrillas | Visible en Personal |
|---|---|---|---|
| `ACTIVO` | Sí | Sí | Sí |
| `AUSENTE` (viaje, vacaciones, rotación) | No | No | Sí, con motivo y fecha de regreso |
| `RETIRADO` (ya no trabaja) | No | No | Sí, en la pestaña Retirados |

> `activo` se conserva por compatibilidad y se mantiene sincronizado:
> `activo = (estado == ACTIVO)`.

### Cambiar el estado

```http
PATCH /api/v1/usuarios/{id}
{ "estado": "AUSENTE", "motivo_ausencia": "Vacaciones", "fecha_retorno": "2026-12-01" }
{ "estado": "ACTIVO" }
{ "estado": "RETIRADO" }
```

Reglas:

- Pasar a `AUSENTE` o `RETIRADO` con la persona en una cuadrilla activa
  devuelve **409** (`Primero retíralo de la cuadrilla ...`).
- Pasar a `ACTIVO` limpia `motivo_ausencia` y `fecha_retorno`.
- Una `fecha_retorno` anterior a hoy devuelve **422**.
- Un supervisor no puede cambiar su propio estado.
- Login con contraseña correcta pero estado no `ACTIVO` devuelve **403**
  con un mensaje claro; con contraseña incorrecta se mantiene el 401 genérico.
- Los tokens vigentes de una persona que pasa a `AUSENTE`/`RETIRADO` dejan de
  funcionar de inmediato.

El cargo de chofer ya no se usa: `POST`/`PATCH /usuarios` rechazan
`CHOFER`/`CHOFER_CAMIONETA` con **422**.

---

## Despliegue en Railway

1. Conectar el repositorio de GitHub a Railway
2. Establecer **Root Directory** como `hydra_backend`
3. Agregar un servicio **PostgreSQL** en Railway
4. Configurar las variables de entorno en Railway:
   - `SECRET_KEY`
   - `ALGORITHM`
   - `ACCESS_TOKEN_EXPIRE_MINUTES`
5. Railway asigna `DATABASE_URL` automáticamente

---

## Variables de Entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | Clave para firmar tokens JWT | Mínimo 32 caracteres aleatorios |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del token en minutos | `480` (8 horas) |
# Importación inicial del catastro

Los GeoJSON históricos son fuentes de importación del backend; la aplicación
móvil nunca los empaqueta. Para cargar o actualizar el catastro de forma
idempotente:

```powershell
.\venv\Scripts\python.exe scripts\importar_catastro_geojson.py
```
