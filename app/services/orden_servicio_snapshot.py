from typing import Any

from app.models.cuadrilla import Cuadrilla, RolEnCuadrilla
from app.models.orden_servicio import OrdenServicio


ESTADOS_OS_ARCHIVADA = {"COMPLETADO", "ARCHIVADO"}


def construir_snapshot_cuadrilla(cuadrilla: Cuadrilla | None) -> dict[str, Any] | None:
    if cuadrilla is None:
        return None

    snapshot: dict[str, Any] = {
        "id": cuadrilla.id,
        "codigo_grupo": cuadrilla.codigo_grupo,
        "especialidad": cuadrilla.especialidad,
        "lider": None,
        "apoyos": [],
        "chofer": None,
        "operador": None,
    }

    for integrante in cuadrilla.personal:
        usuario = integrante.usuario
        rol = integrante.rol_en_cuadrilla
        persona = {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "codigo_empleado": usuario.codigo_empleado,
            "rol_en_cuadrilla": rol.value if rol else "",
        }

        if rol == RolEnCuadrilla.LIDER:
            snapshot["lider"] = persona
        elif rol == RolEnCuadrilla.APOYO:
            snapshot["apoyos"].append(persona)
        elif rol == RolEnCuadrilla.CHOFER:
            snapshot["chofer"] = persona
        elif rol == RolEnCuadrilla.OPERADOR:
            snapshot["operador"] = persona

    return snapshot


def cuadrilla_para_respuesta(orden: OrdenServicio) -> dict[str, Any] | None:
    estado = (orden.estado_orden or "").upper()
    if estado in ESTADOS_OS_ARCHIVADA and orden.cuadrilla_snapshot is not None:
        return orden.cuadrilla_snapshot
    return construir_snapshot_cuadrilla(orden.cuadrilla)
