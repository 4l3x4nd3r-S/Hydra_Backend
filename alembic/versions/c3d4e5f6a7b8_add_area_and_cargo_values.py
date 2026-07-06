"""add area and more cargo values to usuarios

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-03 00:00:00.000000

- Crea enum area_usuario {DISTRIBUCION, MANTENIMIENTO}
- Agrega columna area a usuarios (nullable)
- Amplia enum cargo_usuario con GASFITERO, CHOFER_CAMIONETA, OPERADOR_RETROEXCAVADORA
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE area_usuario AS ENUM ('DISTRIBUCION', 'MANTENIMIENTO')")
    op.add_column(
        'usuarios',
        sa.Column('area', sa.Enum('DISTRIBUCION', 'MANTENIMIENTO', name='area_usuario'), nullable=True),
    )

    op.execute("COMMIT")
    op.execute("ALTER TYPE cargo_usuario ADD VALUE IF NOT EXISTS 'GASFITERO'")
    op.execute("ALTER TYPE cargo_usuario ADD VALUE IF NOT EXISTS 'CHOFER_CAMIONETA'")
    op.execute("ALTER TYPE cargo_usuario ADD VALUE IF NOT EXISTS 'OPERADOR_RETROEXCAVADORA'")


def downgrade() -> None:
    op.drop_column('usuarios', 'area')
    op.execute("DROP TYPE IF EXISTS area_usuario")
