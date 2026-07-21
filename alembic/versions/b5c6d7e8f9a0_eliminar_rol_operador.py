"""Eliminar el rol operador y convertirlo a chofer.

Revision ID: b5c6d7e8f9a0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-19 00:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE cuadrillas_personal "
        "SET rol_en_cuadrilla = 'CHOFER' "
        "WHERE rol_en_cuadrilla::text = 'OPERADOR'"
    )
    op.execute(
        "UPDATE usuarios "
        "SET cargo = 'CHOFER_CAMIONETA' "
        "WHERE cargo::text = 'OPERADOR_RETROEXCAVADORA'"
    )
    op.execute(
        """
        UPDATE ordenes_servicio
        SET cuadrilla_snapshot =
            (cuadrilla_snapshot - 'operador') ||
            jsonb_build_object(
                'chofer',
                COALESCE(
                    cuadrilla_snapshot -> 'chofer',
                    cuadrilla_snapshot -> 'operador'
                )
            )
        WHERE cuadrilla_snapshot IS NOT NULL
          AND cuadrilla_snapshot ? 'operador'
        """
    )

    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla TYPE text "
        "USING rol_en_cuadrilla::text"
    )
    op.execute("DROP TYPE rol_cuadrilla")
    op.execute("CREATE TYPE rol_cuadrilla AS ENUM ('LIDER', 'APOYO', 'CHOFER')")
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla TYPE rol_cuadrilla "
        "USING rol_en_cuadrilla::rol_cuadrilla"
    )
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla "
        "SET DEFAULT 'APOYO'::rol_cuadrilla"
    )

    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN cargo TYPE text USING cargo::text"
    )
    op.execute("DROP TYPE cargo_usuario")
    op.execute(
        "CREATE TYPE cargo_usuario AS ENUM ("
        "'GASFITERO', 'GASFITERO_PRINCIPAL', "
        "'GASFITERO_APOYO', 'CHOFER_CAMIONETA')"
    )
    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN cargo TYPE cargo_usuario "
        "USING cargo::cargo_usuario"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla TYPE text "
        "USING rol_en_cuadrilla::text"
    )
    op.execute("DROP TYPE rol_cuadrilla")
    op.execute(
        "CREATE TYPE rol_cuadrilla AS ENUM "
        "('LIDER', 'APOYO', 'CHOFER', 'OPERADOR')"
    )
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla TYPE rol_cuadrilla "
        "USING rol_en_cuadrilla::rol_cuadrilla"
    )
    op.execute(
        "ALTER TABLE cuadrillas_personal "
        "ALTER COLUMN rol_en_cuadrilla "
        "SET DEFAULT 'APOYO'::rol_cuadrilla"
    )

    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN cargo TYPE text USING cargo::text"
    )
    op.execute("DROP TYPE cargo_usuario")
    op.execute(
        "CREATE TYPE cargo_usuario AS ENUM ("
        "'GASFITERO', 'GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', "
        "'CHOFER_CAMIONETA', 'OPERADOR_RETROEXCAVADORA')"
    )
    op.execute(
        "ALTER TABLE usuarios ALTER COLUMN cargo TYPE cargo_usuario "
        "USING cargo::cargo_usuario"
    )
