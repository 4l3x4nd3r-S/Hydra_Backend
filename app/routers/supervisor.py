from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario, RolUsuario, AreaUsuario, CargoUsuario
from app.models.cuadrilla import (
    Cuadrilla,
    CuadrillaPersonal,
    RolEnCuadrilla,
)
from app.models.elemento_red import ElementoRed
from app.models.orden_servicio import OrdenServicio
from app.routers.cuadrillas import build_detalle
from app.services.orden_servicio_snapshot import cuadrilla_para_respuesta
from app.schemas.supervisor import TecnicoResponse, CrearOrdenServicioRequest
from app.schemas.orden_servicio import OrdenServicioResponse
from app.services.catalogo_service import (
    GRUPO_AREA_USUARIO,
    GRUPO_CARGO_USUARIO,
    GRUPO_FUNCION_CUADRILLA,
    mapa_etiquetas,
)

router = APIRouter(prefix="/supervisor", tags=["Supervisor"])

ROLES_SUPERVISORES = {RolUsuario.SUPERVISOR}

ORDEN_ROL_CUADRILLA = {
    RolEnCuadrilla.LIDER: 0,
    RolEnCuadrilla.APOYO: 1,
    RolEnCuadrilla.CHOFER: 2,
}


async def require_supervisor(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ROLES_SUPERVISORES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a supervisores.",
        )
    return current_user


def _tecnico_response(
    usuario: Usuario,
    funciones: dict[str, str],
    areas: dict[str, str],
    cargos: dict[str, str],
) -> TecnicoResponse:
    pertenencia = next(
        (item for item in usuario.cuadrillas if item.cuadrilla is not None and item.cuadrilla.activo),
        None,
    )
    rol = pertenencia.rol_en_cuadrilla if pertenencia is not None else None
    cuadrilla = pertenencia.cuadrilla if pertenencia is not None else None
    es_chofer = usuario.cargo == CargoUsuario.CHOFER_CAMIONETA
    funcion_codigo = rol.value if rol is not None else (
        "CHOFER" if es_chofer else "GASFITERO"
    )
    funcion_visible = funciones.get(funcion_codigo, funcion_codigo)
    cargo_codigo = usuario.cargo.value if usuario.cargo else None
    area_codigo = usuario.area.value if usuario.area else None
    return TecnicoResponse(
        id=usuario.id,
        codigo_empleado=usuario.codigo_empleado,
        nombre=usuario.nombre,
        dni=usuario.dni,
        celular=usuario.celular,
        cargo=cargo_codigo,
        cargo_visible=cargos.get(cargo_codigo, cargo_codigo) if cargo_codigo else None,
        area=area_codigo,
        area_visible=areas.get(area_codigo, area_codigo) if area_codigo else None,
        rol_en_cuadrilla=rol.value if rol else None,
        funcion_visible=funcion_visible,
        es_principal=rol == RolEnCuadrilla.LIDER,
        puede_ser_gasfitero=not es_chofer,
        puede_ser_chofer=es_chofer,
        cuadrilla_id=cuadrilla.id if cuadrilla else None,
        codigo_cuadrilla=cuadrilla.codigo_grupo if cuadrilla else None,
    )


def _orden_tecnico(tecnico: TecnicoResponse) -> tuple:
    rol = (
        RolEnCuadrilla(tecnico.rol_en_cuadrilla)
        if tecnico.rol_en_cuadrilla
        else None
    )
    return (
        tecnico.codigo_cuadrilla is None,
        tecnico.codigo_cuadrilla or "",
        ORDEN_ROL_CUADRILLA.get(rol, 4),
        tecnico.nombre.casefold(),
    )


@router.get("/tecnicos", response_model=list[TecnicoResponse], summary="Listar personal disponible")
async def list_tecnicos(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Usuario)
        .options(
            selectinload(Usuario.cuadrillas).selectinload(
                CuadrillaPersonal.cuadrilla
            )
        )
        .where(
            Usuario.rol == RolUsuario.GASFITERO,
            Usuario.activo == True,
            Usuario.area == AreaUsuario.MANTENIMIENTO,
        )
    )
    query = query.order_by(Usuario.nombre)
    result = await db.execute(query)
    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    areas = await mapa_etiquetas(db, GRUPO_AREA_USUARIO)
    cargos = await mapa_etiquetas(db, GRUPO_CARGO_USUARIO)
    tecnicos = [
        _tecnico_response(usuario, funciones, areas, cargos)
        for usuario in result.scalars().all()
    ]
    return sorted(tecnicos, key=_orden_tecnico)


@router.get("/tecnicos-disponibles", response_model=list[TecnicoResponse], summary="Listar personal NO asignado a ninguna cuadrilla")
async def list_tecnicos_disponibles(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    ocupados_subq = (
        select(CuadrillaPersonal.usuario_id)
        .join(Cuadrilla)
        .where(
            CuadrillaPersonal.rol_en_cuadrilla.in_([
                RolEnCuadrilla.LIDER,
                RolEnCuadrilla.APOYO,
                RolEnCuadrilla.CHOFER,
            ]),
            Cuadrilla.activo == True
        )
    )
    query = (
        select(Usuario)
        .options(
            selectinload(Usuario.cuadrillas).selectinload(
                CuadrillaPersonal.cuadrilla
            )
        )
        .where(
            Usuario.rol == RolUsuario.GASFITERO,
            Usuario.activo == True,
            Usuario.area == AreaUsuario.MANTENIMIENTO,
            Usuario.id.notin_(ocupados_subq),
        )
    )
    query = query.order_by(Usuario.nombre)
    result = await db.execute(query)
    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    areas = await mapa_etiquetas(db, GRUPO_AREA_USUARIO)
    cargos = await mapa_etiquetas(db, GRUPO_CARGO_USUARIO)
    return [
        _tecnico_response(usuario, funciones, areas, cargos)
        for usuario in result.scalars().all()
    ]


@router.get("/cuadrillas", summary="Listar todas las cuadrillas con sus integrantes")
async def list_cuadrillas_full(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cuadrilla)
        .where(Cuadrilla.activo == True)
        .options(selectinload(Cuadrilla.personal).selectinload(CuadrillaPersonal.usuario))
        .order_by(Cuadrilla.codigo_grupo)
    )
    cuadrillas = result.scalars().all()
    funciones = await mapa_etiquetas(db, GRUPO_FUNCION_CUADRILLA)
    return [build_detalle(c, funciones).model_dump() for c in cuadrillas]


@router.get("/elementos-red", summary="Listar todos los elementos de red")
async def list_elementos(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ElementoRed).order_by(ElementoRed.codigo_plano))
    elementos = result.scalars().all()
    return [
        {
            "id": e.id,
            "codigo_plano": e.codigo_plano,
            "tipo": e.tipo,
            "latitud": e.latitud,
            "longitud": e.longitud,
            "sector_id": e.sector_id,
            "estado_operativo": e.estado_operativo,
            "estado_valvula": e.estado_valvula,
            "fecha_modificacion": e.fecha_modificacion.isoformat() if e.fecha_modificacion else None,
        }
        for e in elementos
    ]


@router.get("/ordenes-servicio", response_model=list[OrdenServicioResponse], summary="Listar todas las órdenes de servicio")
async def list_ordenes_servicio(
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrdenServicio)
        .options(
            selectinload(OrdenServicio.supervisor),
            selectinload(OrdenServicio.cuadrilla)
                .selectinload(Cuadrilla.personal)
                .selectinload(CuadrillaPersonal.usuario),
            selectinload(OrdenServicio.responsable),
            selectinload(OrdenServicio.reclamo),
        )
        .order_by(OrdenServicio.created_at.desc())
    )
    ordenes = result.scalars().all()
    
    def _build_os_response(o: OrdenServicio) -> dict:
        cuadrilla_data = cuadrilla_para_respuesta(o)
            
        reclamo_data = None
        if o.reclamo:
            reclamo_data = {
                "id": o.reclamo.id,
                "formato": o.reclamo.formato,
                "codigo_solicitud": o.reclamo.codigo_solicitud,
                "canal_entrada": o.reclamo.canal_entrada,
                "tipo_problema": o.reclamo.tipo_problema,
                "estado": o.reclamo.estado,
                "descripcion": o.reclamo.descripcion,
                "nombre_solicitante": o.reclamo.nombre_solicitante,
                "direccion": o.reclamo.direccion,
                "numero_suministro": o.reclamo.numero_suministro,
                "telefono": o.reclamo.telefono,
                "email": o.reclamo.email,
                "fecha_registro": o.reclamo.fecha_registro,
            }

        responsable_data = None
        if o.responsable:
            responsable_data = {
                "id": o.responsable.id,
                "nombre": o.responsable.nombre,
                "codigo_empleado": o.responsable.codigo_empleado,
                "cargo": o.responsable.cargo.value if o.responsable.cargo else None,
            }
            
        return {
            "id": o.id,
            "numero_orden": o.numero_orden,
            "reclamo_id": o.reclamo_id,
            "supervisor_id": o.supervisor_id,
            "cuadrilla_id": o.cuadrilla_id,
            "responsable_id": o.responsable_id,
            "sector_id": o.sector_id,
            "fecha_programacion": o.fecha_programacion,
            "fecha_ejecucion_inicio": o.fecha_ejecucion_inicio,
            "fecha_ejecucion_fin": o.fecha_ejecucion_fin,
            "estado_orden": o.estado_orden,
            "insumos_utilizados": o.insumos_utilizados,
            "observaciones_gasfitero": o.observaciones_gasfitero,
            "ruta_carpeta_evidencias": o.ruta_carpeta_evidencias,
            "created_at": o.created_at,
            "trabajo_ejecutado": getattr(o, "trabajo_ejecutado", None),
            "problemas": getattr(o, "problemas", None),
            "soluciones": getattr(o, "soluciones", None),
            "comentarios_instrucciones": getattr(o, "comentarios_instrucciones", None),
            "latitud": getattr(o, "latitud", None),
            "longitud": getattr(o, "longitud", None),
            "fotos_problema_urls": getattr(o, "fotos_problema_urls", None) or [],
            "fotos_solucion_urls": getattr(o, "fotos_solucion_urls", None) or [],
            "reclamo": reclamo_data,
            "cuadrilla": cuadrilla_data,
            "responsable": responsable_data,
        }
        
    return [_build_os_response(o) for o in ordenes]


@router.post(
    "/ordenes-servicio",
    response_model=OrdenServicioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear y asignar orden de servicio",
)
async def crear_orden_servicio(
    payload: CrearOrdenServicioRequest,
    current_user: Usuario = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
):
    from app.services.orden_servicio_service import OrdenServicioService

    try:
        service = OrdenServicioService(db)
        if payload.fecha_programacion is not None:
            if isinstance(payload.fecha_programacion, str):
                fecha = datetime.fromisoformat(payload.fecha_programacion.replace("Z", "+00:00"))
            else:
                fecha = payload.fecha_programacion
            fecha = fecha.replace(tzinfo=None)
        else:
            fecha = None
        ot = await service.crear_desde_reclamo(
            reclamo_id=payload.reclamo_id,
            cuadrilla_id=payload.cuadrilla_id,
            responsable_id=payload.responsable_id,
            supervisor_id=payload.supervisor_id,
            fecha_programacion=fecha,
            actor=current_user,
        )
        await db.commit()
        
        ot.fotos_problema_urls = getattr(ot, "fotos_problema_urls", None) or []
        ot.fotos_solucion_urls = getattr(ot, "fotos_solucion_urls", None) or []
        return ot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
