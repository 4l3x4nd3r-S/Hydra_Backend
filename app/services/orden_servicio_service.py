import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orden_servicio import OrdenServicio
from app.models.reclamo import Reclamo
from app.models.cuadrilla import Cuadrilla, CuadrillaPersonal
from app.models.usuario import Usuario
from app.models.auditoria import AuditoriaEvento

logger = logging.getLogger("hydra.services.os")


class OrdenServicioService:
    ESTADOS_OS_ACTIVA = {"ASIGNADO", "EN_PROCESO"}

    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear_desde_reclamo(
        self,
        *,
        reclamo_id: int,
        cuadrilla_id: int | None,
        supervisor_id: int | None,
        fecha_programacion: datetime | None,
        actor: Usuario,
    ) -> OrdenServicio:
        reclamo = await self._validar_reclamo_sin_os_activa(reclamo_id)

        if cuadrilla_id is not None:
            await self._validar_cuadrilla_existe(cuadrilla_id)

        numero_orden = await self._generar_numero_orden()

        ot = OrdenServicio(
            numero_orden=numero_orden,
            reclamo_id=reclamo_id,
            supervisor_id=supervisor_id or actor.id,
            cuadrilla_id=cuadrilla_id,
            sector_id=None,
            fecha_programacion=fecha_programacion,
            estado_orden="ASIGNADO",
        )
        self._db.add(ot)

        estado_anterior_reclamo = reclamo.estado
        reclamo.estado = "ASIGNADO"
        self._db.add(reclamo)

        auditoria = AuditoriaEvento(
            usuario_id=actor.id,
            usuario_nombre=actor.nombre,
            rol=actor.rol.value if actor.rol else None,
            accion="OS_CREADA",
            entidad="orden_servicio",
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
        hoy = date.today()
        fecha_str = hoy.strftime("%Y%m%d")

        result = await self._db.execute(
            text(
                """
                INSERT INTO os_secuencia (fecha, contador)
                VALUES (:fecha, 1)
                ON CONFLICT (fecha)
                DO UPDATE SET contador = os_secuencia.contador + 1
                RETURNING contador
                """
            ),
            {"fecha": hoy},
        )
        contador = result.scalar_one()

        return f"OS-{fecha_str}-{contador:04d}"

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

    async def _validar_cuadrilla_existe(self, cuadrilla_id: int) -> None:
        result = await self._db.execute(
            select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
        )
        if not result.scalars().first():
            raise ValueError("Cuadrilla no encontrada.")
