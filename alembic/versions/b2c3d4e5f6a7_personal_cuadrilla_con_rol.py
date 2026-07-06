"""personal_cuadrilla_con_rol

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-03 00:00:00.000000

- Crea enum cargo_usuario para la tabla usuarios
- Crea enum rol_cuadrilla para la tabla de personal
- Agrega columna cargo a usuarios (nullable)
- Renombra cuadrillas_gasfiteros -> cuadrillas_personal
- Agrega columna rol_en_cuadrilla con default 'APOYO'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE cargo_usuario AS ENUM ('GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', 'CHOFER', 'OPERADOR_MAQUINARIA')")
    op.execute("CREATE TYPE rol_cuadrilla AS ENUM ('LIDER', 'APOYO', 'CHOFER', 'OPERADOR')")

    op.add_column('usuarios', sa.Column('cargo', sa.Enum('GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', 'CHOFER', 'OPERADOR_MAQUINARIA', name='cargo_usuario'), nullable=True))

    op.rename_table('cuadrillas_gasfiteros', 'cuadrillas_personal')

    op.add_column('cuadrillas_personal', sa.Column(
        'rol_en_cuadrilla',
        sa.Enum('LIDER', 'APOYO', 'CHOFER', 'OPERADOR', name='rol_cuadrilla'),
        nullable=False,
        server_default='APOYO',
    ))


def downgrade() -> None:
    op.drop_column('cuadrillas_personal', 'rol_en_cuadrilla')
    op.rename_table('cuadrillas_personal', 'cuadrillas_gasfiteros')
    op.drop_column('usuarios', 'cargo')
    op.execute("DROP TYPE IF EXISTS cargo_usuario")
    op.execute("DROP TYPE IF EXISTS rol_cuadrilla")
