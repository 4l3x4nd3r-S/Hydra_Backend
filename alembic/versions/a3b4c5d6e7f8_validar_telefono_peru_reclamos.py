"""validar telefono peru en reclamos

Revision ID: a3b4c5d6e7f8
Revises: f3c4d5e6a7b8
Create Date: 2026-07-16 00:00:00.000000

Exige que todo telefono nuevo o actualizado tenga exactamente 9 digitos
ASCII y empiece con 9. La restriccion se agrega como NOT VALID para no
alterar ni bloquear el despliegue por datos historicos; PostgreSQL si la
aplica a todas las inserciones y actualizaciones posteriores.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f3c4d5e6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reclamos "
        "ADD CONSTRAINT ck_reclamos_telefono_peru "
        "CHECK (telefono IS NULL OR telefono ~ '^9[0-9]{8}$') "
        "NOT VALID"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reclamos_telefono_peru",
        "reclamos",
        type_="check",
    )
