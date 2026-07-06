"""normalizar especialidad cuadrilla

Revision ID: a1b2c3d4e5f6
Revises: 002b7688eca3
Create Date: 2026-07-03 00:00:00.000000

Limpia valores no canónicos de la columna `cuadrillas.especialidad`,
mapea variantes (Fugas -> Agua, Desague -> Desagüe) y agrega un CHECK
constraint para impedir valores fuera de {Agua, Desagüe}.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '002b7688eca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "UPDATE cuadrillas "
            "SET especialidad = 'Agua' "
            "WHERE LOWER(COALESCE(especialidad, '')) LIKE '%fuga%'"
        )
    )

    bind.execute(
        sa.text(
            "UPDATE cuadrillas "
            "SET especialidad = 'Agua' "
            "WHERE especialidad IS NULL OR TRIM(especialidad) = ''"
        )
    )

    bind.execute(
        sa.text(
            "UPDATE cuadrillas "
            "SET especialidad = 'Desagüe' "
            "WHERE UPPER(especialidad) IN ('DESAGUE', 'DESAGUES', 'ALCANTARILLADO')"
        )
    )

    op.create_check_constraint(
        'ck_cuadrillas_especialidad',
        'cuadrillas',
        "especialidad IS NULL OR especialidad IN ('Agua', 'Desagüe')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_cuadrillas_especialidad', 'cuadrillas', type_='check')
