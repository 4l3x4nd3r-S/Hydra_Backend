"""Cleanup cargo_usuario enum to 5 values

Revision ID: a6b7c8d9e0f1
Revises: f8a9b0c1d2e3
Create Date: 2026-07-12 01:00:00.000000

- Elimina CHOFER y OPERADOR_MAQUINARIA del enum cargo_usuario
- Mapea datos existentes: CHOFER -> CHOFER_CAMIONETA, OPERADOR_MAQUINARIA -> OPERADOR_RETROEXCAVADORA
- Enum final: GASFITERO, GASFITERO_PRINCIPAL, GASFITERO_APOYO, CHOFER_CAMIONETA, OPERADOR_RETROEXCAVADORA
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE usuarios SET cargo = 'CHOFER_CAMIONETA' WHERE cargo = 'CHOFER'")
    op.execute("UPDATE usuarios SET cargo = 'OPERADOR_RETROEXCAVADORA' WHERE cargo = 'OPERADOR_MAQUINARIA'")
    op.execute("UPDATE usuarios SET cargo = NULL WHERE cargo NOT IN ('GASFITERO', 'GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', 'CHOFER_CAMIONETA', 'OPERADOR_RETROEXCAVADORA')")

    op.execute("ALTER TYPE cargo_usuario RENAME TO cargo_usuario_old")
    op.execute("CREATE TYPE cargo_usuario AS ENUM ('GASFITERO', 'GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', 'CHOFER_CAMIONETA', 'OPERADOR_RETROEXCAVADORA')")
    op.execute("ALTER TABLE usuarios ALTER COLUMN cargo TYPE cargo_usuario USING cargo::text::cargo_usuario")
    op.execute("DROP TYPE cargo_usuario_old")


def downgrade() -> None:
    op.execute("ALTER TYPE cargo_usuario RENAME TO cargo_usuario_old")
    op.execute("CREATE TYPE cargo_usuario AS ENUM ('GASFITERO', 'GASFITERO_PRINCIPAL', 'GASFITERO_APOYO', 'CHOFER', 'OPERADOR_MAQUINARIA', 'CHOFER_CAMIONETA', 'OPERADOR_RETROEXCAVADORA')")
    op.execute("ALTER TABLE usuarios ALTER COLUMN cargo TYPE cargo_usuario USING cargo::text::cargo_usuario")
    op.execute("DROP TYPE cargo_usuario_old")
