"""Renombrar Desagüe a Alcantarillado en todos los datos operativos.

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-20 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _a_alcantarillado(columna: str) -> str:
    return (
        f"replace(replace(replace(replace(replace(replace({columna}, "
        "'DESAGÜE', 'ALCANTARILLADO'), 'DESAGUE', 'ALCANTARILLADO'), "
        "'Desagüe', 'Alcantarillado'), 'Desague', 'Alcantarillado'), "
        "'desagüe', 'alcantarillado'), 'desague', 'alcantarillado')"
    )


def _a_desague(columna: str) -> str:
    return (
        f"replace(replace(replace({columna}, "
        "'ALCANTARILLADO', 'DESAGÜE'), "
        "'Alcantarillado', 'Desagüe'), "
        "'alcantarillado', 'desagüe')"
    )


def upgrade() -> None:
    op.execute(
        "ALTER TABLE cuadrillas "
        "DROP CONSTRAINT IF EXISTS ck_cuadrillas_especialidad_valida"
    )
    op.execute(
        "ALTER TABLE cuadrillas "
        "DROP CONSTRAINT IF EXISTS ck_cuadrillas_especialidad"
    )
    op.execute(
        "UPDATE cuadrillas SET especialidad = 'Alcantarillado' "
        "WHERE UPPER(especialidad) IN "
        "('DESAGÜE', 'DESAGUE', 'DESAGÜES', 'DESAGUES', 'ALCANTARILLADO')"
    )
    op.create_check_constraint(
        "ck_cuadrillas_especialidad",
        "cuadrillas",
        "especialidad IS NULL OR especialidad IN ('Agua', 'Alcantarillado')",
    )

    op.execute(
        f"UPDATE reclamos SET tipo_problema = {_a_alcantarillado('tipo_problema')} "
        "WHERE tipo_problema ILIKE '%desagüe%' OR tipo_problema ILIKE '%desague%'"
    )
    op.execute(
        f"UPDATE reclamos SET descripcion = {_a_alcantarillado('descripcion')} "
        "WHERE descripcion ILIKE '%desagüe%' OR descripcion ILIKE '%desague%'"
    )
    op.execute(
        "UPDATE ordenes_servicio SET cuadrilla_snapshot = "
        f"({_a_alcantarillado('cuadrilla_snapshot::text')})::jsonb "
        "WHERE lower(cuadrilla_snapshot::text) LIKE '%desagüe%' "
        "OR lower(cuadrilla_snapshot::text) LIKE '%desague%'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE cuadrillas "
        "DROP CONSTRAINT IF EXISTS ck_cuadrillas_especialidad_valida"
    )
    op.execute(
        "ALTER TABLE cuadrillas "
        "DROP CONSTRAINT IF EXISTS ck_cuadrillas_especialidad"
    )
    op.execute(
        "UPDATE cuadrillas SET especialidad = 'Desagüe' "
        "WHERE especialidad = 'Alcantarillado'"
    )
    op.create_check_constraint(
        "ck_cuadrillas_especialidad",
        "cuadrillas",
        "especialidad IS NULL OR especialidad IN ('Agua', 'Desagüe')",
    )
    op.execute(
        f"UPDATE reclamos SET tipo_problema = {_a_desague('tipo_problema')} "
        "WHERE tipo_problema ILIKE '%alcantarillado%'"
    )
    op.execute(
        f"UPDATE reclamos SET descripcion = {_a_desague('descripcion')} "
        "WHERE descripcion ILIKE '%alcantarillado%'"
    )
    op.execute(
        "UPDATE ordenes_servicio SET cuadrilla_snapshot = "
        f"({_a_desague('cuadrilla_snapshot::text')})::jsonb "
        "WHERE lower(cuadrilla_snapshot::text) LIKE '%alcantarillado%'"
    )
