"""add_activo_to_cuadrilla

Revision ID: ea775f1f8a37
Revises: d7e8f9a0b1c2
Create Date: 2026-07-21 12:14:04.615889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


revision: str = 'ea775f1f8a37'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cuadrillas', sa.Column('activo', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    op.drop_column('cuadrillas', 'activo')
