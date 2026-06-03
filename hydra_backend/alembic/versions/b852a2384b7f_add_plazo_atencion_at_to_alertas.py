"""add plazo_atencion_at to alertas

Revision ID: b852a2384b7f
Revises: b2e3f4a5c6d7
Create Date: 2026-06-03 12:35:25.059067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


revision: str = 'b852a2384b7f'
down_revision: Union[str, None] = 'b2e3f4a5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alertas', sa.Column('plazo_atencion_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('alertas', 'plazo_atencion_at')
