"""Eliminar la figura de chofer de los datos operativos.

Revision ID: 6c91240d80e1
Revises: 39940296b568
Create Date: 2026-11-18 00:00:00.000000

Esta migración NO elimina los valores de los enums (eso corresponde a una fase
posterior, coordinada con la app móvil). Solo normaliza los datos:

- ``usuarios.cargo``: ``CHOFER_CAMIONETA`` -> ``GASFITERO``.
- En las cuadrillas **activas**, la pertenencia con rol de chofer pasa a
  ``GASFITERO_APOYO``. Las cuadrillas inactivas y los ``cuadrilla_snapshot``
  de las OS archivadas se conservan como histórico.

Además deja el enum ``rol_cuadrilla`` alineado con el modelo Python. Algunas
bases fueron corregidas a mano y conservan los valores nuevos
(``GASFITERO_PRINCIPAL``/``GASFITERO_APOYO``/``CHOFER_CAMIONETA``), mientras que
otras, reconstruidas desde las migraciones, tienen los valores antiguos
(``LIDER``/``APOYO``/``CHOFER``). Los renombrados son idempotentes.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "6c91240d80e1"
down_revision: Union[str, None] = "39940296b568"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _renombrar_valor_enum(enum: str, viejo: str, nuevo: str) -> None:
    """Renombra un valor de enum solo si existe el viejo y falta el nuevo."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum}' AND e.enumlabel = '{viejo}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum}' AND e.enumlabel = '{nuevo}'
            ) THEN
                EXECUTE 'ALTER TYPE {enum} RENAME VALUE ''{viejo}'' TO ''{nuevo}''';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    # A.1: alinear el enum con los valores que espera el modelo Python.
    _renombrar_valor_enum("rol_cuadrilla", "LIDER", "GASFITERO_PRINCIPAL")
    _renombrar_valor_enum("rol_cuadrilla", "APOYO", "GASFITERO_APOYO")
    _renombrar_valor_enum("rol_cuadrilla", "CHOFER", "CHOFER_CAMIONETA")

    # Ningún usuario debe conservar el cargo de chofer.
    op.execute(
        "UPDATE usuarios SET cargo = 'GASFITERO' "
        "WHERE cargo::text = 'CHOFER_CAMIONETA'"
    )

    # En cuadrillas activas el chofer pasa a ser un gasfitero de apoyo.
    op.execute(
        """
        UPDATE cuadrillas_personal AS cp
        SET rol_en_cuadrilla = 'GASFITERO_APOYO'
        FROM cuadrillas AS c
        WHERE cp.cuadrilla_id = c.id
          AND c.activo IS TRUE
          AND cp.rol_en_cuadrilla::text = 'CHOFER_CAMIONETA'
        """
    )


def downgrade() -> None:
    # Migración de datos: no es posible saber qué filas eran chofer antes.
    # Los renombrados de enum tampoco se revierten para no romper las filas
    # que ya usan los valores nuevos.
    return None
