"""Restringir personal a Mantenimiento.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-14 19:00:00.000000

Elimina las asignaciones y usuarios del área Distribución y reduce el enum
area_usuario al único valor manejado actualmente por la aplicación.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    usuarios_distribucion = (
        "SELECT id FROM usuarios WHERE area::text = 'DISTRIBUCION'"
    )
    op.execute(
        f"DELETE FROM cuadrillas_personal WHERE usuario_id IN ({usuarios_distribucion})"
    )
    op.execute(
        f"UPDATE ordenes_servicio SET responsable_id = NULL "
        f"WHERE responsable_id IN ({usuarios_distribucion})"
    )
    op.execute(
        f"UPDATE ordenes_servicio SET supervisor_id = NULL "
        f"WHERE supervisor_id IN ({usuarios_distribucion})"
    )
    op.execute(
        f"UPDATE reclamos SET usuario_id = NULL "
        f"WHERE usuario_id IN ({usuarios_distribucion})"
    )
    op.execute("DELETE FROM usuarios WHERE area::text = 'DISTRIBUCION'")

    op.execute("ALTER TYPE area_usuario RENAME TO area_usuario_old")
    op.execute("CREATE TYPE area_usuario AS ENUM ('MANTENIMIENTO')")
    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN area TYPE area_usuario "
        "USING area::text::area_usuario"
    )
    op.execute("DROP TYPE area_usuario_old")


def downgrade() -> None:
    op.execute("ALTER TYPE area_usuario RENAME TO area_usuario_old")
    op.execute(
        "CREATE TYPE area_usuario AS ENUM ('DISTRIBUCION', 'MANTENIMIENTO')"
    )
    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN area TYPE area_usuario "
        "USING area::text::area_usuario"
    )
    op.execute("DROP TYPE area_usuario_old")

