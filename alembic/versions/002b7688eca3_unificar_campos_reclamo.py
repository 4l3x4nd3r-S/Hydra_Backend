"""unificar_campos_reclamo

Revision ID: 002b7688eca3
Revises: c76ece5b8293
Create Date: 2026-07-02 02:38:48.883578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002b7688eca3'
down_revision: Union[str, None] = 'c76ece5b8293'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE reclamos SET codigo_solicitud = codigo_ticket_cisco "
        "WHERE codigo_solicitud IS NULL AND codigo_ticket_cisco IS NOT NULL"
    )
    op.drop_column('reclamos', 'codigo_ticket_cisco')


def downgrade() -> None:
    op.add_column(
        'reclamos',
        sa.Column('codigo_ticket_cisco', sa.String(50), nullable=True),
    )
