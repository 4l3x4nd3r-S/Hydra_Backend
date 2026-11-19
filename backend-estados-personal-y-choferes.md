# Backend — Estados del personal y eliminación de choferes

**Para:** Alex (backend `Hydra_Backend`)
**Fecha:** 18/11/2026
**Estado:** pendiente de implementar. La web (`Catastro_Web`) ya tiene la pantalla de Personal preparada para este contrato.

---

## Contexto y decisiones

1. **El personal rota, viaja o sale de vacaciones.** No queremos crear y borrar cuentas en cada rotación: se perdería la trazabilidad de quién hizo cada OS y habría que repartir contraseñas nuevas. La cuenta dura lo que dura la persona en la empresa; lo que cambia es su **estado**.
2. **Estados del personal:**
   | Estado | Puede iniciar sesión | Aparece para asignar a cuadrillas | Se ve en la web (Personal) |
   |---|---|---|---|
   | `ACTIVO` | Sí | Sí | Sí |
   | `AUSENTE` (viaje, vacaciones, rotación) | **No** | No | Sí, con motivo y fecha de regreso |
   | `RETIRADO` (ya no trabaja) | No | No | Sí, en la pestaña Retirados |
3. **Agregar personal = crear una cuenta** (código de empleado + contraseña inicial). Los gasfiteros necesitan la cuenta para usar la app móvil.
4. **La figura de "chofer" ya no se usa.** Nadie debe quedar con cargo ni rol de chofer. Las OS archivadas que tengan un chofer en su `cuadrilla_snapshot` se conservan como histórico.
5. **No se borra personal** (`DELETE /usuarios/{id}`): se pasa a `RETIRADO`, para no romper la relación con reclamos y OS.

---

## Parte A — Lo que ya está hecho (rama `fix/sin-choferes`, sin commit)

| Archivo | Cambio |
|---|---|
| `alembic/versions/6c91240d80e1_sin_choferes.py` (nuevo, `down_revision = 39940296b568`) | Migración de datos: `usuarios.cargo` `CHOFER_CAMIONETA` → `GASFITERO` (incluye a Teodoro Condori, MAN001). En las cuadrillas **activas**, la pertenencia con rol chofer pasa a apoyo. Busca el valor real de apoyo en `pg_enum` (ver A.1). No toca las cuadrillas inactivas, los snapshots de OS ni los tipos enum. |
| `app/schemas/usuario.py` | `field_validator("cargo")` en `CrearUsuarioRequest` y `ActualizarUsuarioRequest`: rechaza `CHOFER_CAMIONETA`/`CHOFER` con un 422. |

**Pendiente:** ejecutar el diagnóstico de solo lectura contra la base de datos real antes de `alembic upgrade head`. No se pudo hacer porque no había `DATABASE_URL`.

### A.1 ⚠️ Desajuste a revisar: `rol_cuadrilla`
- Según las migraciones (`b5c6d7e8f9a0`), el tipo postgres `rol_cuadrilla` tiene los valores `('LIDER','APOYO','CHOFER')`.
- El modelo Python (`app/models/cuadrilla.py`, desde el commit `476b27d`, 29/07/2026) usa `GASFITERO_PRINCIPAL / GASFITERO_APOYO / CHOFER_CAMIONETA`, y **ninguna migración renombra esos valores**.
- Hay que verificar en la base real: `SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='rol_cuadrilla';`. Si aparecen los valores antiguos, falta una migración de renombrado (o la base se cambió a mano y las migraciones están desfasadas).
- Algunos tests todavía insertan `'LIDER'`.

---

## Parte B — Fase 1: estados del personal (por implementar)

### B1. Migración `estado` del personal
- Enum nuevo `estado_personal`: `ACTIVO`, `AUSENTE`, `RETIRADO`.
- Columnas nuevas en `usuarios`:
  - `estado estado_personal NOT NULL DEFAULT 'ACTIVO'`
  - `motivo_ausencia varchar(200) NULL`
  - `fecha_retorno date NULL`
- Relleno de datos: `activo = true` → `ACTIVO` y `activo = false` → `RETIRADO`.
- `downgrade`: borrar las columnas y el enum.
- **Por qué:** `activo` solo distingue "está / no está"; las rotaciones necesitan un estado temporal que no se confunda con un retiro.

### B2. Modelo `app/models/usuario.py`
- Añadir el enum `EstadoPersonal` y las 3 columnas.
- **Mantener `activo` sincronizado** (`activo = (estado == ACTIVO)`).
- **Por qué:** `activo` ya se usa en `/auth/login`, `/auth/refresh`, `/supervisor/tecnicos`, `/supervisor/tecnicos-disponibles` y la app móvil. Si se mantiene sincronizado, un ausente o retirado queda fuera de todo sin reescribir esas consultas.

### B3. Schemas `app/schemas/usuario.py`
- `UsuarioResponse`: añadir `estado`, `motivo_ausencia` y `fecha_retorno`.
- `ActualizarUsuarioRequest`: añadir `estado`, `motivo_ausencia` y `fecha_retorno`. **`activo` deja de aceptarse desde fuera** (solo se cambia vía `estado`), para que no queden contradictorios.
- `CrearUsuarioRequest`: valores por defecto `rol=GASFITERO`, `area=MANTENIMIENTO`, `cargo=GASFITERO` (hoy `rol` es obligatorio).

### B4. Router `app/routers/usuarios.py` — `PATCH /usuarios/{id}`
- Paso a `AUSENTE` o `RETIRADO` con la persona en una **cuadrilla activa** → **409** `"Primero retíralo de la cuadrilla <codigo_grupo>."`.
  *Por qué:* la cuadrilla quedaría con un integrante que no puede iniciar sesión ni ejecutar OS, posiblemente sin su Gasfitero Principal.
- Paso a `ACTIVO` → limpiar `motivo_ausencia` y `fecha_retorno`.
- `fecha_retorno` anterior a hoy → 422.
- Un supervisor no puede cambiar su propio estado.
- `GET /usuarios?rol=GASFITERO` sigue igual (ya incluye a los inactivos); solo devuelve los campos nuevos. **No hace falta un endpoint nuevo.**
- `DELETE` no cambia; la web no lo usa.

### B5. Login y sesión
- `app/routers/auth.py` `/login`: si la **contraseña es correcta** pero el estado no es `ACTIVO`, responder **403** con un mensaje claro (`"Tu cuenta está en ausencia hasta el dd/mm."` / `"Tu cuenta fue dada de baja."`). Con contraseña incorrecta, seguir respondiendo el 401 genérico (para no revelar qué cuentas existen).
- `app/core/security.py` `get_current_user`: **hoy no comprueba `activo`**. Añadir esa comprobación (401 si `activo` es false).
  *Por qué:* sin esto, a quien se marca ausente le sigue funcionando su token actual hasta que caduque.

### B5b. Edición de personal: dos fallos de `PATCH /usuarios/{id}` detectados al probar la web
1. **No se puede vaciar el DNI ni el celular.** El router usa `if payload.dni is not None:`, así que no hay forma de dejarlo en `NULL` (la web omite los campos vacíos porque `""` no pasa el patrón). Hay que distinguir "no enviado" de "enviado como `null`" con `payload.model_fields_set` (`if "dni" in payload.model_fields_set: usuario.dni = payload.dni`), y lo mismo para `celular`.
2. **Un DNI o celular duplicado devuelve 500.** Ambas columnas son `unique` y `crear_usuario` / `actualizar_usuario` no capturan `IntegrityError` (tampoco `app/core/exception_handlers.py`). Hay que comprobarlo antes del commit (o capturar el `IntegrityError`) y responder **409** `"El DNI 12345678 ya está registrado."` / `"El celular ... ya está registrado."`.
   *Por qué:* hoy el supervisor solo ve "Error del backend (HTTP 500)" y no sabe qué corregir.

### B6. Tests (`tests/test_estados_personal.py`)
- Login de un ausente → 403; un token existente deja de funcionar tras cambiar el estado → 401.
- 409 si la persona está en una cuadrilla activa; al reincorporar se limpian el motivo y la fecha.
- Crear con cargo chofer → 422; la migración rellena `estado` desde `activo` correctamente.

### Contrato que ya espera la web
```http
GET   /api/v1/usuarios?rol=GASFITERO
  → [{ id, codigo_empleado, nombre, dni, celular, rol, cargo, area,
       activo, estado, motivo_ausencia, fecha_retorno, created_at }]

POST  /api/v1/usuarios
  { codigo_empleado, nombre, dni?, celular?, password (≥12),
    rol: "GASFITERO", cargo: "GASFITERO", area: "MANTENIMIENTO" }

PATCH /api/v1/usuarios/{id}
  { nombre?, dni?, celular?, password? }                         // editar
  { estado: "AUSENTE", motivo_ausencia?, fecha_retorno? }        // ausencia
  { estado: "ACTIVO" } | { estado: "RETIRADO" }                  // reincorporar / retirar
```
> Mientras no exista `estado`, la web envía también `activo` (true/false) para que retirar y reincorporar funcionen ya. "Marcar ausente" queda deshabilitado hasta que el backend devuelva `estado`.

**Despliegue en Render:** primero `alembic upgrade head` y después el código.

---

## Parte C — Fase 2: código residual de choferes (por eliminar)

> Hacerlo **después** de aplicar la migración de la Parte A y **coordinado con la app móvil** (ver C.6): si el backend deja de enviar `chofer`, la app podría fallar al deserializar.

### C.1 Modelos y enums
| Ubicación | Qué quitar |
|---|---|
| `app/models/usuario.py:28` | `CargoUsuario.CHOFER_CAMIONETA` |
| `app/models/cuadrilla.py:33` | `RolEnCuadrilla.CHOFER_CAMIONETA` |
| Postgres | Quitar `CHOFER_CAMIONETA` de `cargo_usuario` y `CHOFER`/`CHOFER_CAMIONETA` de `rol_cuadrilla` (migración que recrea el tipo; postgres no permite `DROP VALUE`). Antes, comprobar que ninguna fila use esos valores, **incluidas las cuadrillas inactivas**. |
| Catálogos (sembrados en `d7e8f9a0b1c2_catalogos_operativos.py:105,110`) | Desactivar o borrar las filas `FUNCION_CUADRILLA/CHOFER` y `CARGO_USUARIO/CHOFER_CAMIONETA` |

### C.2 Cuadrillas — `app/routers/cuadrillas.py` y `app/schemas/cuadrilla.py`
| Ubicación | Qué hace hoy |
|---|---|
| `schemas/cuadrilla.py:8` | `chofer_id: Optional[int]` en la petición de creación |
| `schemas/cuadrilla.py:17` | Incluye `chofer_id` en la validación de integrantes distintos |
| `schemas/cuadrilla.py:61` | `chofer: Optional[PersonaCuadrilla]` en la respuesta |
| `routers/cuadrillas.py:35` | Entrada `CHOFER_CAMIONETA: False` en el mapa de roles |
| `routers/cuadrillas.py:44, 63-64, 72` | `build_detalle` separa al chofer en su propio campo |
| `routers/cuadrillas.py:119` | Cuenta `chofer_id` entre los integrantes |
| `routers/cuadrillas.py:150-153` | **Asigna `cargo = CHOFER_CAMIONETA` al usuario** al ponerlo de chofer |
| `routers/cuadrillas.py:182-186` | Crea la pertenencia con rol `CHOFER_CAMIONETA` |
| `routers/cuadrillas.py:238` | Validación específica del rol chofer al asignar |
| `routers/cuadrillas.py:286` | Cuenta `chofer_id` en la actualización |

### C.3 Supervisor — `app/routers/supervisor.py` y `app/schemas/supervisor.py`
| Ubicación | Qué hace hoy |
|---|---|
| `routers/supervisor.py:35` | Orden de la lista con chofer en la posición 2 |
| `routers/supervisor.py:60-62` | `es_chofer` y `funcion_codigo = "CHOFER"` |
| `routers/supervisor.py:80-81` | `puede_ser_gasfitero = not es_chofer`, `puede_ser_chofer` |
| `routers/supervisor.py:143` | `tecnicos-disponibles` considera ocupados a los choferes |
| `schemas/supervisor.py:21` | Campo `puede_ser_chofer` en `TecnicoResponse` |

### C.4 Órdenes de servicio
| Ubicación | Qué hacer |
|---|---|
| `app/services/orden_servicio_snapshot.py:19, 36-37` | Dejar de generar `snapshot["chofer"]` para las OS nuevas |
| `app/schemas/orden_servicio.py:73` | Mantener `chofer: Optional[...] = None` **como solo lectura** para las OS archivadas que lo tengan, o eliminarlo si se acepta perder ese dato histórico en la respuesta |

### C.5 Tests
- `tests/test_cuadrillas_mantenimiento.py:58-80`: `test_chofer_sin_cuadrilla_conserva_su_unica_funcion` y las aserciones de `puede_ser_chofer`.
- `tests/test_orden_servicio_snapshot.py:51`: `"chofer": None` en el snapshot esperado.

### C.6 App móvil (`Hydra-App-Mobile`, Flutter): coordinar
Usan `chofer`:
- `lib/data/models/cuadrilla_dto.dart` (y los generados `.freezed.dart` / `.g.dart`)
- `lib/data/models/gasfitero_dto.dart` (y sus generados)
- `lib/domain/models/cuadrilla.dart`
- `lib/data/repositories/os_repository.dart`, `lib/data/repositories/supervisor_repository.dart`
- `lib/data/services/supervisor_api_service.dart`

**Orden recomendado:** que la app trate `chofer` / `puede_ser_chofer` como opcionales (publicar esa versión) → el backend deja de enviarlos → limpieza final en ambos lados.

### Fuera de alcance (ya no aplica)
Las migraciones antiguas que mencionan `CHOFER`/`OPERADOR` (`a6b7c8d9e0f1`, `b2c3d4e5f6a7`, `b5c6d7e8f9a0`, `c3d4e5f6a7b8`, `e0f1a2b3c4d5`) son historial de Alembic: **no se editan**.
