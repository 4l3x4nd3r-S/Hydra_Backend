"""add alertas table

Revision ID: b2e3f4a5c6d7
Revises: 672d6f71abc2
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2e3f4a5c6d7'
down_revision: Union[str, None] = '672d6f71abc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'alertas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sensor_id', sa.String(length=50), nullable=True),
        sa.Column('sector_id', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('nivel', sa.String(length=10), nullable=False),
        sa.Column('estado', sa.String(length=15), nullable=False, server_default='PENDIENTE'),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('presion_detectada_mca', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('ot_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('atendida_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ot_id'], ['ordenes_trabajo.id']),
        sa.ForeignKeyConstraint(['sector_id'], ['sectores.id']),
        sa.ForeignKeyConstraint(['sensor_id'], ['sensores.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alertas_id'), 'alertas', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_alertas_id'), table_name='alertas')
    op.drop_table('alertas')
