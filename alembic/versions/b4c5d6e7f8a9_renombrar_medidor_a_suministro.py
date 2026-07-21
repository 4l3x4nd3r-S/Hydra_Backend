"""Renombrar número de medidor a número de suministro.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_reclamos_numero_medidor_7_digitos",
        "reclamos",
        type_="check",
    )
    op.alter_column(
        "reclamos",
        "numero_medidor",
        new_column_name="numero_suministro",
    )
    op.create_check_constraint(
        "ck_reclamos_numero_suministro_7_digitos",
        "reclamos",
        "numero_suministro IS NULL OR "
        "(numero_suministro ~ '^[0-9]{7}$' "
        "AND numero_suministro <> '0000000')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reclamos_numero_suministro_7_digitos",
        "reclamos",
        type_="check",
    )
    op.alter_column(
        "reclamos",
        "numero_suministro",
        new_column_name="numero_medidor",
    )
    op.create_check_constraint(
        "ck_reclamos_numero_medidor_7_digitos",
        "reclamos",
        "numero_medidor IS NULL OR "
        "(numero_medidor ~ '^[0-9]{7}$' AND numero_medidor <> '0000000')",
    )
