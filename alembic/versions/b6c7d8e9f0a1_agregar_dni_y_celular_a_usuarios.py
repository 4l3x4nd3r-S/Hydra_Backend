"""Agregar DNI y celular a usuarios.

Revision ID: b6c7d8e9f0a1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-20 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("dni", sa.String(length=8), nullable=True))
    op.add_column(
        "usuarios", sa.Column("celular", sa.String(length=9), nullable=True)
    )

    op.create_unique_constraint("uq_usuarios_dni", "usuarios", ["dni"])
    op.create_unique_constraint("uq_usuarios_celular", "usuarios", ["celular"])
    op.create_check_constraint(
        "ck_usuarios_dni_formato",
        "usuarios",
        "dni IS NULL OR dni ~ '^[0-9]{8}$'",
    )
    op.create_check_constraint(
        "ck_usuarios_celular_formato",
        "usuarios",
        "celular IS NULL OR celular ~ '^9[0-9]{8}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_usuarios_celular_formato", "usuarios", type_="check")
    op.drop_constraint("ck_usuarios_dni_formato", "usuarios", type_="check")
    op.drop_constraint("uq_usuarios_celular", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_dni", "usuarios", type_="unique")
    op.drop_column("usuarios", "celular")
    op.drop_column("usuarios", "dni")
