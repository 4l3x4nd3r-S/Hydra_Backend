"""Ampliar tipos de problema para Formato 1.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-15 17:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "reclamos",
        "tipo_problema",
        existing_type=sa.String(length=50),
        type_=sa.String(length=120),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "reclamos",
        "tipo_problema",
        existing_type=sa.String(length=120),
        type_=sa.String(length=50),
        existing_nullable=True,
    )

