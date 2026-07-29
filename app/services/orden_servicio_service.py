import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orden_servicio import OrdenServicio, numero_orden_sequence
from app.models.reclamo import Reclamo
from app.models.cuadrilla import Cuadrilla, CuadrillaPersonal
from app.models.usuario import Usuario, RolUsuario
from app.models.auditoria import AuditoriaEvento
from app.services.catalogo_service import especialidad_para_formato

logger = logging.getLogger("hydra.services.os")

class OrdenServicioService:
    ESTADOS_OS_ACTIVA = {"ASIGNADO", "EN_PROCESO"}

    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear_desde_reclamo(
        self,
        *,
        reclamo_id: int,
        cuadrilla_id: int,
        supervisor_id: int | None,
        fecha_programacion: datetime | None,
        actor: Usuario,
    ) -> OrdenServicio:

        reclamo = await self._validar_reclamo_sin_os_activa(reclamo_id)

        await self._validar_cuadrilla_compatible(cuadrilla_id, reclamo.formato)

        numero_orden = await self._generar_numero_orden()

        ot = OrdenServicio(
            numero_orden=numero_orden,
            reclamo_id=reclamo_id,
            supervisor_id=supervisor_id or actor.id,
            cuadrilla_id=cuadrilla_id,

            fecha_programacion=fecha_programacion,
            estado_orden="ASIGNADO",
        )
        self._db.add(ot)

        estado_anterior_reclamo = reclamo.estado
        reclamo.estado = "ASIGNADO"
        self._db.add(reclamo)

        # Hacemos flush para que la base de datos asigne el ID a la O.S. (ot.id)
        await self._db.flush()

        auditoria = AuditoriaEvento(
            usuario_id=actor.id,
            usuario_nombre=actor.nombre,
            rol=actor.rol.value if actor.rol else None,
            accion="OS_CREADA",
            entidad="orden_servicio",
            entidad_id=ot.id,
            detalles={
                "numero_orden": numero_orden,
                "reclamo_id": reclamo_id,
                "cuadrilla_id": cuadrilla_id,
                "supervisor_id": supervisor_id or actor.id,
                "reclamo_estado_anterior": estado_anterior_reclamo,
                "reclamo_estado_nuevo": "ASIGNADO",
            },
        )
        self._db.add(auditoria)

        await self._db.flush()
        await self._db.refresh(ot)

        result = await self._db.execute(
            select(OrdenServicio)
            .options(
                selectinload(OrdenServicio.reclamo),
                selectinload(OrdenServicio.cuadrilla)
                    .selectinload(Cuadrilla.personal)
                    .selectinload(CuadrillaPersonal.usuario),
                selectinload(OrdenServicio.supervisor),
            )
            .where(OrdenServicio.id == ot.id)
        )
        ot_cargado = result.scalars().first()

        logger.info(
            "os.created numero_orden=%s reclamo_id=%d actor_id=%d",
            numero_orden,
            reclamo_id,
            actor.id,
        )
        return ot_cargado

    async def _generar_numero_orden(self) -> str:
        result = await self._db.execute(
            select(numero_orden_sequence.next_value())
        )
        correlativo = result.scalar_one()

        return f"{correlativo:07d}"

    async def _validar_reclamo_sin_os_activa(self, reclamo_id: int) -> Reclamo:
        result = await self._db.execute(
            select(Reclamo).where(Reclamo.id == reclamo_id)
        )
        reclamo = result.scalars().first()
        if not reclamo:
            raise ValueError("Reclamo no encontrado.")

        result_ot = await self._db.execute(
            select(OrdenServicio).where(
                OrdenServicio.reclamo_id == reclamo_id,
                OrdenServicio.estado_orden.in_(self.ESTADOS_OS_ACTIVA),
            )
        )
        if result_ot.scalars().first():
            raise ValueError("El reclamo ya tiene una O.S. activa.")

        return reclamo

    async def _validar_cuadrilla_compatible(
        self,
        cuadrilla_id: int,
        formato_reclamo: str | None,
    ) -> None:
        result = await self._db.execute(
            select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
        )
        cuadrilla = result.scalars().first()
        if not cuadrilla:
            raise ValueError("Cuadrilla no encontrada.")

        especialidad_requerida = await especialidad_para_formato(
            self._db, formato_reclamo
        )
        if especialidad_requerida is None:
            raise ValueError(
                "El formato del reclamo no tiene una especialidad configurada."
            )

        especialidad_cuadrilla = (cuadrilla.especialidad or "").strip()
        if especialidad_cuadrilla.casefold() != especialidad_requerida.casefold():
            raise ValueError(
                f"Los reclamos con formato {formato_reclamo} solo pueden "
                f"asignarse a cuadrillas de {especialidad_requerida}."
            )


