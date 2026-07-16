"""Add responsable_id to ordenes_servicio

Revision ID: f8a9b0c1d2e3
Revises: e825fc93240e
Create Date: 2026-07-12 00:00:00.000000

- Agrega columna responsable_id (FK a usuarios.id, nullable) a ordenes_servicio
- Permite asignar una OS a un gasfitero individual (sin cuadrilla)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = '44eca831ba6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ordenes_servicio', sa.Column(
        'responsable_id',
        sa.Integer(),
        sa.ForeignKey('usuarios.id', name='fk_ordenes_servicio_responsable_id_usuarios'),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_constraint(
        'fk_ordenes_servicio_responsable_id_usuarios',
        'ordenes_servicio',
        type_='foreignkey',
    )
    op.drop_column('ordenes_servicio', 'responsable_id')
